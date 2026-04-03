import os
import json
import datetime
import shutil
import tempfile
import smtplib
import re
import base64
from collections import defaultdict
from contextlib import asynccontextmanager
from email.message import EmailMessage

from fastapi import (
    FastAPI,
    HTTPException,
    UploadFile,
    File,
    Depends,
    Form,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm

from sqlmodel import SQLModel, Session, create_engine, select, or_

from passlib.context import CryptContext
from jose import JWTError, jwt
from dotenv import load_dotenv

from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch
import whisper

from pydantic import BaseModel, EmailStr

from apscheduler.schedulers.background import BackgroundScheduler

from models import User, JournalEntry
from constants.emotions import EMOTION_LABELS as _FALLBACK_LABELS, NEGATIVE_EMOTIONS
from services.report_generator import generate_csv_report, generate_excel_report
from services.suggestion_engine import generate_dynamic_suggestions

# FIX: Import the analytics service instead of duplicating logic inline
from services.emotion_analytics import get_emotion_timeline, get_emotion_counts

from google_calendar_oauth import create_calendar_event

load_dotenv()

# ==================================================
# CONFIG
# ==================================================

SECRET_KEY                  = os.getenv("SECRET_KEY")
# FIX: Don't silently fall back to a weak default — fail fast at startup
# if the secret key is missing from .env
if not SECRET_KEY:
    raise RuntimeError("SECRET_KEY is not set in .env. Refusing to start.")

ALGORITHM                   = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./journal.db")

_raw_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000")
ALLOWED_ORIGINS = [o.strip() for o in _raw_origins.split(",")]

engine        = create_engine(DATABASE_URL)
pwd_context   = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
scheduler     = BackgroundScheduler()

# AI MODEL — load threshold from model_meta.json

MODEL_PATH = os.getenv("MODEL_PATH", "praveen-1403/mindjounal-emotion-v2")
from huggingface_hub import login

hf_token = os.getenv("HF_TOKEN")
if hf_token:
    login(token=hf_token)

_meta_path = os.path.join(MODEL_PATH, "model_meta.json")
if os.path.exists(_meta_path):
    with open(_meta_path) as _f:
        _meta = json.load(_f)
    EMOTION_THRESHOLD = _meta["best_threshold"]
    EMOTION_LABELS    = _meta["label_names"]
    print(f"[Model] Loaded meta: threshold={EMOTION_THRESHOLD}, labels={len(EMOTION_LABELS)}")
else:
    # Graceful fallback for v1 model (no meta file)
    EMOTION_THRESHOLD = 0.35
    EMOTION_LABELS    = _FALLBACK_LABELS
    print("[Model] model_meta.json not found — using fallback threshold=0.35")

VALID_EMOTIONS = set(EMOTION_LABELS)

tokenizer     = AutoTokenizer.from_pretrained(MODEL_PATH)
emotion_model = AutoModelForSequenceClassification.from_pretrained(MODEL_PATH)
emotion_model.eval()

whisper_model = whisper.load_model("tiny")

# DB INIT + CORRUPTED ROW CLEANUP

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)


def cleanup_corrupted_entries():
    """Remove rows where emotion_primary has no valid emotion label."""
    with Session(engine) as session:
        entries = session.exec(select(JournalEntry)).all()
        removed = 0
        for entry in entries:
            labels = [e.strip() for e in entry.emotion_primary.split(",")]
            if not any(lbl in VALID_EMOTIONS for lbl in labels):
                session.delete(entry)
                removed += 1
        if removed:
            session.commit()
            print(f"[Startup] Removed {removed} corrupted entries.")
        else:
            print("[Startup] Database clean.")

# EMAIL UTILITY

def send_email(to_address: str, subject: str, body: str):
    sender   = os.getenv("EMAIL_ADDRESS")
    password = os.getenv("EMAIL_APP_PASSWORD")

    if not sender or not password:
        print("[Email] Credentials not set — skipping.")
        return

    msg = EmailMessage()
    msg.set_content(body)
    msg["Subject"] = subject
    msg["From"]    = sender
    msg["To"]      = to_address

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(sender, password)
            server.send_message(msg)
            print(f"[Email] Sent to {to_address}")
    except Exception as e:
        print(f"[Email] Failed: {e}")


def send_automated_reports(range_type: str):
    with Session(engine) as session:
        users = session.exec(select(User)).all()
    for user in users:
        try:
            content, start, end = generate_csv_report(user.id, range_type, engine)
            body = (
                f"Dear {user.username},\n\n"
                f"Your {range_type} emotional report from {start} to {end} "
                "has been generated.\n"
                "Please log into MindJournal to view your personalised insights."
            )
            send_email(
                user.email,
                f"MindJournal: Your {range_type.capitalize()} Report",
                body,
            )
        except Exception as e:
            print(f"[Scheduler] Report failed for {user.email}: {e}")

# AUTH HELPERS

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def create_access_token(data: dict) -> str:
    expire = datetime.datetime.utcnow() + datetime.timedelta(
        minutes=ACCESS_TOKEN_EXPIRE_MINUTES
    )
    data.update({"exp": expire})
    return jwt.encode(data, SECRET_KEY, algorithm=ALGORITHM)

async def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    try:
        payload  = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if not username:
            raise JWTError()
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

    with Session(engine) as session:
        user = session.exec(
            select(User).where(User.username == username)
        ).first()
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        return user

# LIFESPAN

@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    cleanup_corrupted_entries()

    scheduler.add_job(send_automated_reports, "cron", day_of_week="sun", hour=9,
                      args=["weekly"],  id="weekly_report",  replace_existing=True)
    scheduler.add_job(send_automated_reports, "cron", day=1, hour=9,
                      args=["monthly"], id="monthly_report", replace_existing=True)
    scheduler.add_job(send_automated_reports, "cron", month=1, day=1, hour=9,
                      args=["yearly"],  id="yearly_report",  replace_existing=True)
    scheduler.start()
    print("[Scheduler] Report jobs registered.")

    yield

    scheduler.shutdown()
    print("[Scheduler] Shut down.")

# FASTAPI APP

app = FastAPI(lifespan=lifespan)

# FIX: CORS origins loaded from .env instead of hardcoded localhost
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)

# AUTH ENDPOINTS

class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str

@app.post("/signup")
def signup(user: UserCreate):
    if not user.username.strip():
        raise HTTPException(400, "Username cannot be empty.")
    if len(user.password) < 6:
        raise HTTPException(400, "Password must be at least 6 characters.")

    with Session(engine) as session:
        if session.exec(
            select(User).where(
                or_(User.username == user.username, User.email == user.email)
            )
        ).first():
            raise HTTPException(400, "User already exists")
        session.add(User(
            username=user.username,
            email=user.email,
            hashed_password=get_password_hash(user.password),
        ))
        session.commit()
    return {"message": "User created"}

@app.post("/token")
def login(form: OAuth2PasswordRequestForm = Depends()):
    with Session(engine) as session:
        user = session.exec(
            select(User).where(
                or_(User.username == form.username, User.email == form.username)
            )
        ).first()
        if not user or not verify_password(form.password, user.hashed_password):
            raise HTTPException(400, "Invalid credentials")
        return {
            "access_token": create_access_token({"sub": user.username}),
            "token_type": "bearer",
        }

# Forgot password 

class ForgotPasswordRequest(BaseModel):
    identifier: str

class ForgotPasswordReset(BaseModel):
    identifier: str
    answer: str
    new_password: str

@app.post("/forgot-password/question")
def get_security_question(req: ForgotPasswordRequest):
    with Session(engine) as session:
        user = session.exec(
            select(User).where(
                or_(User.username == req.identifier, User.email == req.identifier)
            )
        ).first()
        # FIX: Use a generic error message to prevent username enumeration attacks
        if not user or not user.security_question:
            raise HTTPException(400, "No account with a security question found for that identifier.")
        return {"question": user.security_question}

@app.post("/forgot-password/reset")
def reset_forgotten_password(req: ForgotPasswordReset):
    if len(req.new_password) < 6:
        raise HTTPException(400, "Password must be at least 6 characters.")
    with Session(engine) as session:
        user = session.exec(
            select(User).where(
                or_(User.username == req.identifier, User.email == req.identifier)
            )
        ).first()
        if not user or not user.hashed_security_answer:
            raise HTTPException(400, "Invalid request.")
        if not verify_password(req.answer.strip().lower(), user.hashed_security_answer):
            raise HTTPException(400, "Incorrect answer to security question.")
        user.hashed_password = get_password_hash(req.new_password)
        session.add(user)
        session.commit()
        return {"message": "Password successfully reset."}

# PROFILE ENDPOINTS

class ProfileUpdate(BaseModel):
    default_morning_time: str
    default_evening_time: str

class SecurityQuestionUpdate(BaseModel):
    question: str
    answer: str

class PasswordChange(BaseModel):
    current_password: str
    new_password: str

class PasswordVerify(BaseModel):
    password: str

class PasswordConfirm(BaseModel):
    password: str

@app.get("/profile")
def get_profile(user: User = Depends(get_current_user)):
    return {
        "username":              user.username,
        "email":                 user.email,
        "default_morning_time":  user.default_morning_time,
        "default_evening_time":  user.default_evening_time,
        "has_security_question": bool(user.security_question),
    }

def _validate_time(t: str, field: str):
    try:
        datetime.datetime.strptime(t, "%H:%M")
    except ValueError:
        raise HTTPException(400, f"Invalid format for {field} — use HH:MM.")

@app.put("/profile")
def update_profile(profile: ProfileUpdate, user: User = Depends(get_current_user)):
    _validate_time(profile.default_morning_time, "morning time")
    _validate_time(profile.default_evening_time, "evening time")
    with Session(engine) as session:
        db_user = session.get(User, user.id)
        db_user.default_morning_time = profile.default_morning_time
        db_user.default_evening_time = profile.default_evening_time
        session.add(db_user)
        session.commit()
    return {"message": "Profile updated"}

@app.put("/profile/security-question")
def update_security_question(
    sec: SecurityQuestionUpdate, user: User = Depends(get_current_user)
):
    if not sec.answer.strip():
        raise HTTPException(400, "Security answer cannot be empty.")
    with Session(engine) as session:
        db_user = session.get(User, user.id)
        db_user.security_question      = sec.question
        db_user.hashed_security_answer = get_password_hash(sec.answer.strip().lower())
        session.add(db_user)
        session.commit()
    return {"message": "Security question saved."}

@app.post("/profile/verify-password")
def verify_current_password(req: PasswordVerify, user: User = Depends(get_current_user)):
    if not verify_password(req.password, user.hashed_password):
        raise HTTPException(400, "Incorrect password.")
    return {"message": "Password verified."}

@app.put("/profile/password")
def change_password(pwd: PasswordChange, user: User = Depends(get_current_user)):
    if not verify_password(pwd.current_password, user.hashed_password):
        raise HTTPException(400, "Incorrect current password.")
    if len(pwd.new_password) < 6:
        raise HTTPException(400, "New password must be at least 6 characters.")
    with Session(engine) as session:
        db_user = session.get(User, user.id)
        db_user.hashed_password = get_password_hash(pwd.new_password)
        session.add(db_user)
        session.commit()
    return {"message": "Password updated successfully."}

@app.delete("/profile/account")
def delete_account(req: PasswordConfirm, user: User = Depends(get_current_user)):
    if not verify_password(req.password, user.hashed_password):
        raise HTTPException(400, "Incorrect password.")
    with Session(engine) as session:
        for j in session.exec(
            select(JournalEntry).where(JournalEntry.user_id == user.id)
        ).all():
            session.delete(j)
        session.delete(session.get(User, user.id))
        session.commit()
    return {"message": "Account completely deleted."}

# CORE ANALYSIS

MAX_INPUT_CHARS = 2000

def analyze_and_store(text: str, date: str, user: User):
    if not text or not text.strip():
        raise HTTPException(400, "Journal text cannot be empty.")

    if len(text) > MAX_INPUT_CHARS:
        raise HTTPException(
            400,
            f"Input too long ({len(text)} chars). Maximum is {MAX_INPUT_CHARS} characters."
        )

    sentences = re.split(r"(?<=[.!?]) +", text.strip()) or [text]

    all_active_emotions: set = set()
    max_scores: dict         = defaultdict(float)

    for sentence in sentences:
        if not sentence.strip():
            continue

        inputs = tokenizer(sentence, return_tensors="pt", truncation=True, padding=True)
        with torch.no_grad():
            logits = emotion_model(**inputs).logits

        probs = torch.sigmoid(logits).squeeze().tolist()
        if isinstance(probs, float):
            probs = [probs]

        for i, score in enumerate(probs):
            emo = EMOTION_LABELS[i]
            if score >= EMOTION_THRESHOLD:
                all_active_emotions.add(emo)
            if score > max_scores[emo]:
                max_scores[emo] = float(score)

    active_emotions = list(all_active_emotions)
    if not active_emotions:
        active_emotions = [max(max_scores, key=max_scores.get)]

    active_emotions.sort(key=lambda e: max_scores[e], reverse=True)
    requires_schedule = any(emo in NEGATIVE_EMOTIONS for emo in active_emotions)

    try:
        entry_date = datetime.datetime.strptime(date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(400, "Invalid date format — use YYYY-MM-DD.")

    with Session(engine) as session:
        session.add(JournalEntry(
            user_id          = user.id,
            date             = entry_date,
            input_sentence   = text,
            encrypted_content= None,   # TODO: encrypt server-side before storing
            emotion_primary  = ",".join(active_emotions),
            emotion_scores   = dict(max_scores),
        ))
        session.commit()

        history_3_months = session.exec(
            select(JournalEntry)
            .where(JournalEntry.user_id == user.id)
            .where(JournalEntry.date >= entry_date - datetime.timedelta(days=90))
            .order_by(JournalEntry.date.desc())
        ).all()

    dominant, intensity, suggestion_dict = generate_dynamic_suggestions(
        active_emotions, history_3_months
    )
    return active_emotions, suggestion_dict, requires_schedule

# ANALYSIS ENDPOINTS

@app.post("/analyze-text")
def analyze_text(
    text: str  = Form(...),
    date: str  = Form(...),
    user: User = Depends(get_current_user),
):
    emotions, suggestion_dict, requires_schedule = analyze_and_store(text, date, user)
    return {
        "emotions":            emotions,
        "suggestion":          suggestion_dict,
        "input_text":          text,
        "requires_scheduling": requires_schedule,
    }

@app.post("/analyze-audio")
def analyze_audio(
    file: UploadFile = File(...),
    date: str        = Form(...),
    user: User       = Depends(get_current_user),
):
    allowed_audio_types = {
        "audio/webm", "audio/wav", "audio/mpeg",
        "audio/ogg", "audio/mp4", "audio/x-m4a"
    }
    if file.content_type and file.content_type not in allowed_audio_types:
        raise HTTPException(400, f"Unsupported audio type: {file.content_type}")

    with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as tmp:
        shutil.copyfileobj(file.file, tmp)
        path = tmp.name

    try:
        text = whisper_model.transcribe(path)["text"]
    finally:
        os.remove(path)

    if not text or not text.strip():
        raise HTTPException(422, "Could not transcribe audio — no speech detected.")

    emotions, suggestion_dict, requires_schedule = analyze_and_store(text, date, user)
    return {
        "emotions":            emotions,
        "suggestion":          suggestion_dict,
        "transcription":       text,
        "input_text":          text,
        "requires_scheduling": requires_schedule,
    }

# SCHEDULE ACTIVITY

@app.post("/schedule-activity")
def schedule_activity(
    suggestion:     str  = Form(...),
    scheduled_time: str  = Form(...),
    user:           User = Depends(get_current_user),
):
    now = datetime.datetime.now()

    if scheduled_time == "auto":
        try:
            m_hour, m_min = map(int, user.default_morning_time.split(":"))
            e_hour, e_min = map(int, user.default_evening_time.split(":"))
        except ValueError:
            raise HTTPException(500, "Stored scheduling preferences are malformed.")

        candidates = [
            now.replace(hour=m_hour, minute=m_min, second=0, microsecond=0),
            now.replace(hour=e_hour, minute=e_min, second=0, microsecond=0),
            (now + datetime.timedelta(days=1)).replace(
                hour=m_hour, minute=m_min, second=0, microsecond=0
            ),
        ]
        future_candidates = [c for c in candidates if c > now]
        if not future_candidates:
            raise HTTPException(400, "No valid future scheduling time found.")
        dt = min(future_candidates)
    else:
        try:
            dt = datetime.datetime.fromisoformat(scheduled_time)
        except ValueError:
            raise HTTPException(
                400,
                "Invalid scheduled_time — use ISO 8601 (YYYY-MM-DDTHH:MM) or 'auto'.",
            )

    if dt <= now:
        raise HTTPException(400, "Scheduled time must be in the future.")

    try:
        create_calendar_event(
            "MindJournal Scheduled Activity",
            "Please check your email for detailed suggestions.",
            dt,
        )
    except Exception as e:
        print(f"[Calendar] Event creation failed (non-fatal): {e}")

    email_body = (
        f"Dear {user.username},\n\n"
        "This is a scheduled reminder to prioritise your emotional well-being.\n\n"
        "Here are your personalised suggestions:\n\n"
        "----------------------------------\n"
        f"{suggestion}\n"
        "----------------------------------\n\n"
        "Warm regards,\nThe MindJournal AI"
    )

    scheduler.add_job(
        send_email, "date",
        run_date=dt,
        args=[user.email, "MindJournal: Scheduled Wellness Reminder", email_body],
        id=f"reminder_{user.id}_{int(dt.timestamp())}",
        replace_existing=True,
    )

    return {"message": f"Activity scheduled for {dt.strftime('%I:%M %p on %b %d')}"}

# TIMELINE

@app.get("/timeline")
def timeline(days: int = 90, user: User = Depends(get_current_user)):
    # FIX: Validate days parameter
    if days <= 0 or days > 3650:
        raise HTTPException(400, "days must be between 1 and 3650.")
    return get_emotion_timeline(user.id, days, engine)

# EMOTION COUNTS (bar chart)

@app.get("/emotion-counts")
def emotion_counts(days: int = 30, user: User = Depends(get_current_user)):
    if days <= 0 or days > 3650:
        raise HTTPException(400, "days must be between 1 and 3650.")
    return get_emotion_counts(user.id, days, VALID_EMOTIONS, engine)

# REPORT ENDPOINTS

VALID_RANGES = {"weekly", "monthly", "yearly"}

@app.get("/report/csv")
def export_csv(range: str = "monthly", user: User = Depends(get_current_user)):
    if range not in VALID_RANGES:
        raise HTTPException(400, f"Invalid range. Choose from: {', '.join(VALID_RANGES)}")
    content, start, end = generate_csv_report(user.id, range, engine)
    return {
        "filename": f"MindJournal_{range}_{start}_to_{end}.csv",
        "content":  content,
    }

@app.get("/report/excel")
def export_excel(range: str = "monthly", user: User = Depends(get_current_user)):
    if range not in VALID_RANGES:
        raise HTTPException(400, f"Invalid range. Choose from: {', '.join(VALID_RANGES)}")
    content_bytes, start, end = generate_excel_report(user.id, range, engine)
    return {
        "filename": f"MindJournal_{range}_{start}_to_{end}.xlsx",
        "content":  base64.b64encode(content_bytes).decode("utf-8"),
    }