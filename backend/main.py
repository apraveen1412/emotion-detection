import os
import datetime
import shutil
import tempfile
import smtplib
import re
from collections import defaultdict
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

from cryptography.fernet import Fernet
from passlib.context import CryptContext
from jose import JWTError, jwt
from dotenv import load_dotenv

from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch
import whisper

from pydantic import BaseModel, EmailStr
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from models import User, JournalEntry
from constants.emotions import EMOTION_LABELS, NEGATIVE_EMOTIONS
from services.report_generator import generate_csv_report
from services.suggestion_engine import generate_dynamic_suggestions
from google_calendar_oauth import create_calendar_event

load_dotenv()

# ==================================================
# CONFIG
# ==================================================

SECRET_KEY = os.getenv("SECRET_KEY", "CHANGE_THIS_SECRET")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24

DATABASE_URL = "sqlite:///./journal.db"

EMOTION_THRESHOLD = 0.35          
NEGATIVE_STREAK_TRIGGER = 3       

engine = create_engine(DATABASE_URL)

cipher_suite = Fernet(Fernet.generate_key())
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

scheduler = AsyncIOScheduler()

# ==================================================
# DB INIT
# ==================================================

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)

# ==================================================
# EMAIL UTILITY
# ==================================================

def send_email(to_address, subject, body):
    sender = os.getenv("EMAIL_ADDRESS")
    password = os.getenv("EMAIL_APP_PASSWORD")

    msg = EmailMessage()
    msg.set_content(body)
    msg['Subject'] = subject
    msg['From'] = sender
    msg['To'] = to_address

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(sender, password)
            server.send_message(msg)
            print(f"✅ Email sent successfully to {to_address}")
    except Exception as e:
        print(f"❌ Failed to send email: {e}")

def send_automated_reports(range_type):
    with Session(engine) as session:
        users = session.exec(select(User)).all()
        for user in users:
            content, start, end = generate_csv_report(user.id, range_type, engine)
            body = (
                f"Dear {user.username},\n\n"
                f"Your {range_type} emotional report from {start} to {end} has been generated.\n"
                f"Overall, your emotional history has been reviewed by the AI. Please log into "
                f"MindJournal to download your detailed CSV data and view personalized insights."
            )
            send_email(user.email, f"MindJournal: Your {range_type.capitalize()} Report", body)

# ==================================================
# AUTH HELPERS
# ==================================================
def verify_password(plain, hashed):
    return pwd_context.verify(plain, hashed)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict):
    expire = datetime.datetime.utcnow() + datetime.timedelta(
        minutes=ACCESS_TOKEN_EXPIRE_MINUTES
    )
    data.update({"exp": expire})
    return jwt.encode(data, SECRET_KEY, algorithm=ALGORITHM)

async def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
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

# ==================================================
# AI MODELS
# ==================================================

MODEL_PATH = "./model"

tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH)
emotion_model = AutoModelForSequenceClassification.from_pretrained(MODEL_PATH)
emotion_model.eval()

whisper_model = whisper.load_model("tiny")

# ==================================================
# FASTAPI APP & SCHEDULER START
# ==================================================

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)

@app.on_event("startup")
def startup():
    create_db_and_tables()
    scheduler.start()
    
    scheduler.add_job(send_automated_reports, 'cron', day_of_week='sun', hour=9, args=['weekly'])
    scheduler.add_job(send_automated_reports, 'cron', day=1, hour=9, args=['monthly'])
    scheduler.add_job(send_automated_reports, 'cron', month=1, day=1, hour=9, args=['yearly'])

# ==================================================
# AUTH ENDPOINTS
# ==================================================
class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str

@app.post("/signup")
def signup(user: UserCreate):
    with Session(engine) as session:
        if session.exec(
            select(User).where(
                or_(User.username == user.username, User.email == user.email)
            )
        ).first():
            raise HTTPException(400, "User already exists")

        session.add(
            User(
                username=user.username,
                email=user.email,
                hashed_password=get_password_hash(user.password),
            )
        )
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

        token = create_access_token({"sub": user.username})
        return {"access_token": token, "token_type": "bearer"}

# ==================================================
# PROFILE ENDPOINTS
# ==================================================
class ProfileUpdate(BaseModel):
    default_morning_time: str
    default_evening_time: str

@app.get("/profile")
def get_profile(user: User = Depends(get_current_user)):
    return {
        "username": user.username,
        "default_morning_time": user.default_morning_time,
        "default_evening_time": user.default_evening_time
    }

@app.put("/profile")
def update_profile(profile: ProfileUpdate, user: User = Depends(get_current_user)):
    with Session(engine) as session:
        db_user = session.get(User, user.id)
        db_user.default_morning_time = profile.default_morning_time
        db_user.default_evening_time = profile.default_evening_time
        session.add(db_user)
        session.commit()
    return {"message": "Profile updated"}

# ==================================================
# CORE ANALYSIS (Multi-Emotion Sentence Chunking)
# ==================================================

def analyze_and_store(text: str, date: str, user: User):
    # Split the long journal into individual sentences
    sentences = re.split(r'(?<=[.!?]) +', text.strip())
    if not sentences or not sentences[0]:
        sentences = [text]

    all_active_emotions = set()
    max_scores = defaultdict(float)

    # Analyze each sentence individually to catch every emotion shift
    for sentence in sentences:
        if not sentence.strip(): 
            continue
            
        inputs = tokenizer(sentence, return_tensors="pt", truncation=True, padding=True)

        with torch.no_grad():
            logits = emotion_model(**inputs).logits

        probs = torch.sigmoid(logits).squeeze().tolist()
        
        if isinstance(probs, float):
            probs = [probs]

        emotion_scores = {
            EMOTION_LABELS[i]: float(probs[i])
            for i in range(len(EMOTION_LABELS))
        }

        # Track any emotion that passes the threshold in ANY sentence
        for emo, score in emotion_scores.items():
            if score >= EMOTION_THRESHOLD:
                all_active_emotions.add(emo)
            if score > max_scores[emo]:
                max_scores[emo] = score

    active_emotions = list(all_active_emotions)

    if not active_emotions:
        best_emo = max(max_scores, key=max_scores.get)
        active_emotions = [best_emo]

    # Sort the detected emotions by their maximum intensity
    active_emotions.sort(key=lambda e: max_scores[e], reverse=True)

    requires_schedule = any(emo in NEGATIVE_EMOTIONS for emo in active_emotions)

    encrypted = cipher_suite.encrypt(text.encode())
    entry_date = datetime.datetime.strptime(date, "%Y-%m-%d").date()

    with Session(engine) as session:
        session.add(
            JournalEntry(
                user_id=user.id,
                date=entry_date,
                input_sentence=text,
                encrypted_content=encrypted,
                emotion_primary=",".join(active_emotions),
                emotion_scores=dict(max_scores), 
            )
        )
        session.commit()

        ninety_days_ago = entry_date - datetime.timedelta(days=90)
        history_3_months = session.exec(
            select(JournalEntry)
            .where(JournalEntry.user_id == user.id)
            .where(JournalEntry.date >= ninety_days_ago)
            .order_by(JournalEntry.date.desc())
        ).all()

    dominant, intensity, suggestion_dict = generate_dynamic_suggestions(
        active_emotions, history_3_months
    )

    return active_emotions, suggestion_dict, requires_schedule

# ==================================================
# ENDPOINTS
# ==================================================

@app.post("/analyze-text")
def analyze_text(
    text: str = Form(...),
    date: str = Form(...),
    user: User = Depends(get_current_user),
):
    emotions, suggestion_dict, requires_schedule = analyze_and_store(text, date, user)
    return {
        "emotions": emotions, 
        "suggestion": suggestion_dict, 
        "input_text": text,
        "requires_scheduling": requires_schedule
    }

@app.post("/analyze-audio")
def analyze_audio(
    file: UploadFile = File(...),
    date: str = Form(...),
    user: User = Depends(get_current_user),
):
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        shutil.copyfileobj(file.file, tmp)
        path = tmp.name

    text = whisper_model.transcribe(path)["text"]
    os.remove(path)

    emotions, suggestion_dict, requires_schedule = analyze_and_store(text, date, user)
    return {
        "emotions": emotions, 
        "suggestion": suggestion_dict, 
        "transcription": text, 
        "input_text": text,
        "requires_scheduling": requires_schedule
    }

# ==================================================
# SMART SCHEDULE ENDPOINT
# ==================================================
@app.post("/schedule-activity")
def schedule_activity(
    suggestion: str = Form(...),
    scheduled_time: str = Form(...), 
    user: User = Depends(get_current_user)
):
    now = datetime.datetime.now()

    if scheduled_time == "auto":
        m_hour, m_min = map(int, user.default_morning_time.split(":"))
        e_hour, e_min = map(int, user.default_evening_time.split(":"))
        
        candidates = [
            now.replace(hour=m_hour, minute=m_min, second=0, microsecond=0),
            now.replace(hour=e_hour, minute=e_min, second=0, microsecond=0),
            (now + datetime.timedelta(days=1)).replace(hour=m_hour, minute=m_min, second=0, microsecond=0)
        ]
        
        future_candidates = [c for c in candidates if c > now]
        dt = min(future_candidates)
    else:
        dt = datetime.datetime.fromisoformat(scheduled_time)
    
    create_calendar_event("MindJournal Scheduled Activity", "Please check your email for detailed suggestions.", dt)
    
    # Updated Email Body to remove "clinical" terminology
    email_body = (
        f"Dear {user.username},\n\n"
        f"This is a scheduled reminder to prioritize your emotional well-being today.\n\n"
        f"Your MindJournal entry triggered our analysis engine. To support your emotional stability, here are your personalized suggestions and actionable steps:\n\n"
        f"----------------------------------\n"
        f"{suggestion}\n"
        f"----------------------------------\n\n"
        f"Taking a few uninterrupted moments to engage in this practice can significantly aid in emotional regulation.\n\n"
        f"Warm regards,\n"
        f"The MindJournal AI"
    )
    
    scheduler.add_job(
        send_email,
        'date',
        run_date=dt,
        args=[user.email, "MindJournal: Scheduled Wellness Reminder", email_body]
    )
    
    formatted_time = dt.strftime("%I:%M %p on %b %d")
    return {"message": f"Activity scheduled for {formatted_time}"}

@app.get("/timeline")
def timeline(days: int = 90, user: User = Depends(get_current_user)):
    start = datetime.date.today() - datetime.timedelta(days=days)
    with Session(engine) as session:
        rows = session.exec(
            select(JournalEntry)
            .where(JournalEntry.user_id == user.id)
            .where(JournalEntry.date >= start)
            .order_by(JournalEntry.date)
        ).all()

    return [{"date": r.date.strftime("%Y-%m-%d"), "emotions": r.emotion_primary.split(",")} for r in rows]

@app.get("/report/csv")
def export_csv(range: str = "monthly", user: User = Depends(get_current_user)):
    content, start, end = generate_csv_report(user.id, range, engine)
    return {"filename": f"EmoJournal_{range}_{start}_to_{end}.csv", "content": content}