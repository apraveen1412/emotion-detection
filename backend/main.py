import os
import datetime
import shutil
import tempfile

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

from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch
import whisper

from pydantic import BaseModel, EmailStr

from models import User, JournalEntry
from constants.emotions import EMOTION_LABELS, NEGATIVE_EMOTIONS
from services.report_generator import generate_csv_report
from services.suggestion_engine import generate_dynamic_suggestions
from google_calendar_oauth import create_calendar_event

# ==================================================
# CONFIG
# ==================================================

SECRET_KEY = "CHANGE_THIS_SECRET"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24

DATABASE_URL = "sqlite:///./journal.db"

EMOTION_THRESHOLD = 0.35          # internal only
NEGATIVE_STREAK_TRIGGER = 3       # calendar trigger

engine = create_engine(DATABASE_URL)

cipher_suite = Fernet(Fernet.generate_key())
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# ==================================================
# DB INIT
# ==================================================

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)

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
# FASTAPI APP
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
                or_(
                    User.username == user.username,
                    User.email == user.email
                )
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
                or_(
                    User.username == form.username,
                    User.email == form.username
                )
            )
        ).first()

        if not user or not verify_password(
            form.password, user.hashed_password
        ):
            raise HTTPException(400, "Invalid credentials")

        token = create_access_token({"sub": user.username})
        return {"access_token": token, "token_type": "bearer"}

# ==================================================
# CORE ANALYSIS
# ==================================================

def analyze_and_store(text: str, date: str, user: User):
    inputs = tokenizer(text, return_tensors="pt", truncation=True, padding=True)

    with torch.no_grad():
        logits = emotion_model(**inputs).logits

    probs = torch.sigmoid(logits).squeeze().tolist()

    emotion_scores = {
        EMOTION_LABELS[i]: float(probs[i])
        for i in range(len(probs))
    }

    # Multi-label emotion selection (no scores exposed)
    active_emotions = [
        emo for emo, score in emotion_scores.items()
        if score >= EMOTION_THRESHOLD
    ]

    if not active_emotions:
        active_emotions = [max(emotion_scores, key=emotion_scores.get)]

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
                emotion_scores=emotion_scores,  # internal only
            )
        )
        session.commit()

        # Fetch recent history (latest first)
        recent_entries = session.exec(
            select(JournalEntry)
            .where(JournalEntry.user_id == user.id)
            .order_by(JournalEntry.date.desc())
            .limit(7)
        ).all()

    # --------------------------------------------------
    # Dynamic suggestions
    # --------------------------------------------------
    dominant, intensity, suggestions = generate_dynamic_suggestions(
        recent_entries
    )
    suggestion_text = " ".join(suggestions)

    # --------------------------------------------------
    # Google Calendar trigger (NEGATIVE STREAK)
    # --------------------------------------------------
    negative_streak = 0

    for entry in recent_entries:
        emotions = entry.emotion_primary.split(",")
        if any(e in NEGATIVE_EMOTIONS for e in emotions):
            negative_streak += 1
        else:
            break

    if negative_streak >= NEGATIVE_STREAK_TRIGGER:
        print("[Calendar] Negative emotion streak detected:", negative_streak)

        create_calendar_event(
            summary="EmoJournal Emotional Check-in",
            description=(
                f"A pattern of negative emotions was detected "
                f"over the last {negative_streak} entries.\n\n"
                f"{suggestion_text}"
            )
        )

    return active_emotions, suggestion_text

# ==================================================
# ANALYSIS ENDPOINTS
# ==================================================

@app.post("/analyze-text")
def analyze_text(
    text: str = Form(...),
    date: str = Form(...),
    user: User = Depends(get_current_user),
):
    emotions, suggestion = analyze_and_store(text, date, user)
    return {
        "emotions": emotions,
        "suggestion": suggestion,
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

    emotions, suggestion = analyze_and_store(text, date, user)
    return {
        "emotions": emotions,
        "suggestion": suggestion,
        "transcription": text,
    }

# ==================================================
# TIMELINE
# ==================================================

@app.get("/timeline")
def timeline(
    days: int = 30,
    user: User = Depends(get_current_user),
):
    start = datetime.date.today() - datetime.timedelta(days=days)

    with Session(engine) as session:
        rows = session.exec(
            select(JournalEntry)
            .where(JournalEntry.user_id == user.id)
            .where(JournalEntry.date >= start)
            .order_by(JournalEntry.date)
        ).all()

    return [
        {
            "date": r.date.strftime("%Y-%m-%d"),
            "emotions": r.emotion_primary.split(","),
        }
        for r in rows
    ]

# ==================================================
# CSV REPORT
# ==================================================

@app.get("/report/csv")
def export_csv(
    range: str = "monthly",
    user: User = Depends(get_current_user),
):
    content, start, end = generate_csv_report(
        user.id, range, engine
    )
    return {
        "filename": f"EmoJournal_{range}_{start}_to_{end}.csv",
        "content": content,
    }
