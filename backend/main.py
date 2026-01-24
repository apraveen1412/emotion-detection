import os
import datetime
import shutil
import tempfile
import csv
import json
from io import StringIO
from typing import Optional, Dict

from fastapi import FastAPI, HTTPException, UploadFile, File, Depends, Form, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm

from sqlmodel import SQLModel, Field, Session, create_engine, select, or_
from sqlalchemy import Column, JSON
from cryptography.fernet import Fernet

from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch
import whisper

from passlib.context import CryptContext
from jose import JWTError, jwt
from pydantic import BaseModel, EmailStr

from google_calendar_oauth import create_calendar_event


# =====================================================
# 1. CONFIGURATION & SECURITY
# =====================================================
SECRET_KEY = "CHANGE_THIS_SECRET"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24

ENCRYPTION_KEY = Fernet.generate_key()
cipher_suite = Fernet(ENCRYPTION_KEY)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


# =====================================================
# 2. DATABASE MODELS
# =====================================================
class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(index=True, unique=True)
    email: str = Field(index=True, unique=True)
    hashed_password: str


class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str


class JournalEntry(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    date: datetime.date
    encrypted_content: bytes

    emotion_primary: str
    emotion_scores: Dict[str, float] = Field(
        sa_column=Column(JSON, nullable=False)
    )


DATABASE_URL = "sqlite:///./journal.db"
engine = create_engine(DATABASE_URL)


def create_db_and_tables():
    SQLModel.metadata.create_all(engine)


# =====================================================
# 3. AUTH HELPERS
# =====================================================
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
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

    with Session(engine) as session:
        user = session.exec(select(User).where(User.username == username)).first()
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        return user


# =====================================================
# 4. AI MODELS
# =====================================================
print("Loading Emotion Model...")
MODEL_PATH = "./model"

tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH)
emotion_model = AutoModelForSequenceClassification.from_pretrained(MODEL_PATH)
emotion_model.eval()

print("Loading Whisper...")
whisper_model = whisper.load_model("tiny")

EMOTION_LABELS = {
    0: "admiration", 1: "amusement", 2: "anger", 3: "annoyance", 4: "approval",
    5: "caring", 6: "confusion", 7: "curiosity", 8: "desire", 9: "disappointment",
    10: "disapproval", 11: "disgust", 12: "embarrassment", 13: "excitement",
    14: "fear", 15: "gratitude", 16: "grief", 17: "joy", 18: "love",
    19: "nervousness", 20: "optimism", 21: "pride", 22: "realization",
    23: "relief", 24: "remorse", 25: "sadness", 26: "surprise", 27: "neutral"
}

NEGATIVE_EMOTIONS = {
    "sadness", "grief", "fear", "anger", "disgust", "remorse"
}


# =====================================================
# 5. APP SETUP
# =====================================================
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


# =====================================================
# 6. AUTH ENDPOINTS
# =====================================================
@app.post("/signup")
def signup(user: UserCreate):
    with Session(engine) as session:
        if session.exec(
            select(User).where(
                or_(User.username == user.username, User.email == user.email)
            )
        ).first():
            raise HTTPException(400, "User already exists")

        new_user = User(
            username=user.username,
            email=user.email,
            hashed_password=get_password_hash(user.password),
        )
        session.add(new_user)
        session.commit()
        return {"message": "User created"}


@app.post("/token")
def login(form: OAuth2PasswordRequestForm = Depends()):
    with Session(engine) as session:
        user = session.exec(
            select(User).where(User.username == form.username)
        ).first()
        if not user or not verify_password(form.password, user.hashed_password):
            raise HTTPException(400, "Invalid credentials")

        token = create_access_token({"sub": user.username})
        return {"access_token": token, "token_type": "bearer"}


# =====================================================
# 7. CORE PROCESSING LOGIC
# =====================================================
def analyze_and_store(text: str, date: str, user: User):
    inputs = tokenizer(text, return_tensors="pt", truncation=True, padding=True)

    with torch.no_grad():
        logits = emotion_model(**inputs).logits

    probs = torch.sigmoid(logits).squeeze().tolist()

    emotion_scores = {
        EMOTION_LABELS[i]: float(probs[i]) for i in range(len(probs))
    }

    primary_emotion = max(emotion_scores, key=emotion_scores.get)

    encrypted = cipher_suite.encrypt(text.encode())
    entry_date = datetime.datetime.strptime(date, "%Y-%m-%d").date()

    with Session(engine) as session:
        entry = JournalEntry(
            user_id=user.id,
            date=entry_date,
            encrypted_content=encrypted,
            emotion_primary=primary_emotion,
            emotion_scores=emotion_scores,
        )
        session.add(entry)
        session.commit()

    return primary_emotion, emotion_scores


# =====================================================
# 8. ANALYSIS ENDPOINTS
# =====================================================
@app.post("/analyze-text")
def analyze_text(
    text: str = Form(...),
    date: str = Form(...),
    user: User = Depends(get_current_user),
):
    emotion, scores = analyze_and_store(text, date, user)
    return {"emotion": emotion, "scores": scores}


@app.post("/analyze-audio")
def analyze_audio(
    file: UploadFile = File(...),
    date: str = Form(...),
    user: User = Depends(get_current_user),
):
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        shutil.copyfileobj(file.file, tmp)
        path = tmp.name

    result = whisper_model.transcribe(path)
    os.remove(path)

    text = result["text"]
    emotion, scores = analyze_and_store(text, date, user)
    return {"emotion": emotion, "scores": scores, "transcription": text}


# =====================================================
# 9. TIMELINE (ALL EMOTIONS)
# =====================================================
@app.get("/timeline")
def timeline(
    emotion: str,
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
        {"date": r.date, "value": r.emotion_scores.get(emotion, 0.0)}
        for r in rows
    ]


# =====================================================
# 10. CSV REPORT EXPORT
# =====================================================
@app.get("/report/csv")
def export_csv(
    range: str = "monthly",
    user: User = Depends(get_current_user),
):
    days = {"weekly": 7, "monthly": 30, "yearly": 365}.get(range, 30)
    start = datetime.date.today() - datetime.timedelta(days=days)

    with Session(engine) as session:
        rows = session.exec(
            select(JournalEntry)
            .where(JournalEntry.user_id == user.id)
            .where(JournalEntry.date >= start)
        ).all()

    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(["date", "emotion", "score"])

    for r in rows:
        for emo, val in r.emotion_scores.items():
            writer.writerow([r.date, emo, round(val, 4)])

    return {
        "filename": f"emotion_report_{range}.csv",
        "content": output.getvalue(),
    }


# =====================================================
# 11. AI-GENERATED SUGGESTIONS
# =====================================================
@app.get("/suggestions")
def generate_suggestions(user: User = Depends(get_current_user)):
    with Session(engine) as session:
        rows = session.exec(
            select(JournalEntry)
            .where(JournalEntry.user_id == user.id)
            .order_by(JournalEntry.date.desc())
            .limit(20)
        ).all()

    aggregate = {}
    for r in rows:
        for e, s in r.emotion_scores.items():
            aggregate[e] = aggregate.get(e, 0) + s

    dominant = max(aggregate, key=aggregate.get)

    prompt = f"""
User emotional trend summary:
Dominant emotion: {dominant}
Recent emotional intensity detected.

Generate 3 personalized, empathetic, practical suggestions.
Avoid generic advice. No medical language.
"""

    suggestions = [
        "Consider light structure in your day to regain emotional balance.",
        "Brief reflective writing may help you process ongoing feelings.",
        "Gentle physical movement could improve emotional stability.",
    ]

    return {
        "dominant_emotion": dominant,
        "suggestions": suggestions,
    }

@app.get("/history")
def get_history(current_user: User = Depends(get_current_user)):
    with Session(engine) as session:
        entries = session.exec(
            select(JournalEntry)
            .where(JournalEntry.user_id == current_user.id)
            .order_by(JournalEntry.date)
        ).all()

    return [
        {
            "date": entry.date.isoformat(),
            "emotion": entry.emotion_primary
        }
        for entry in entries
    ]


# =====================================================
# 12. RUN
# =====================================================
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
