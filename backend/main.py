import os
import datetime
import shutil
import tempfile
from typing import List, Optional
from fastapi import FastAPI, HTTPException, UploadFile, File, Depends, Form, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlmodel import SQLModel, Field, Session, create_engine, select, or_
from cryptography.fernet import Fernet
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch
import whisper
from passlib.context import CryptContext
from jose import JWTError, jwt
from pydantic import BaseModel, EmailStr

# --- 1. CONFIGURATION & SECURITY ---
# In production, generate a random string for SECRET_KEY
SECRET_KEY = "YOUR_SUPER_SECRET_KEY_CHANGE_THIS" 
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 # 24 hours

# Generates a key for encrypting journal entries (AES-256)
ENCRYPTION_KEY = Fernet.generate_key() 
cipher_suite = Fernet(ENCRYPTION_KEY)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# --- 2. DATABASE MODELS ---
class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(index=True, unique=True)
    email: str = Field(index=True, unique=True) # Unique Email
    hashed_password: str

# Input Schema for Signup
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
    emotion_score: float

DATABASE_URL = "sqlite:///./journal.db"
engine = create_engine(DATABASE_URL)

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)

# --- 3. AUTHENTICATION HELPERS ---
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.datetime.utcnow() + datetime.timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
        
    with Session(engine) as session:
        statement = select(User).where(User.username == username)
        user = session.exec(statement).first()
        if user is None:
            raise credentials_exception
        return user

# --- 4. AI MODELS ---
print("Loading AI Models...")
MODEL_PATH = "./model" 
# Ensure your Drive files are in backend/model/
try:
    tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH)
    emotion_model = AutoModelForSequenceClassification.from_pretrained(MODEL_PATH)
    emotion_model.eval()
except OSError:
    print("WARNING: Model not found in ./model. Please download files from Drive.")

print("Loading Whisper...")
whisper_model = whisper.load_model("tiny") 

EMOTION_LABELS = {
    0: "admiration", 1: "amusement", 2: "anger", 3: "annoyance", 4: "approval",
    5: "caring", 6: "confusion", 7: "curiosity", 8: "desire", 9: "disappointment",
    10: "disapproval", 11: "disgust", 12: "embarrassment", 13: "excitement", 14: "fear",
    15: "gratitude", 16: "grief", 17: "joy", 18: "love", 19: "nervousness",
    20: "optimism", 21: "pride", 22: "realization", 23: "relief", 24: "remorse",
    25: "sadness", 26: "surprise", 27: "neutral"
}

# --- 5. APP SETUP ---
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def on_startup():
    create_db_and_tables()

# --- 6. AUTH ENDPOINTS ---

@app.post("/signup")
def signup(user_data: UserCreate):
    with Session(engine) as session:
        # Check if username OR email already exists
        statement = select(User).where(
            or_(User.username == user_data.username, User.email == user_data.email)
        )
        existing_user = session.exec(statement).first()
        
        if existing_user:
            if existing_user.username == user_data.username:
                raise HTTPException(status_code=400, detail="Username already taken")
            if existing_user.email == user_data.email:
                raise HTTPException(status_code=400, detail="Email already registered")
        
        # Create new user
        new_user = User(
            username=user_data.username, 
            email=user_data.email,
            hashed_password=get_password_hash(user_data.password)
        )
        session.add(new_user)
        session.commit()
        return {"message": "User created successfully"}

@app.post("/token")
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    with Session(engine) as session:
        # 1. Check if user exists
        user = session.exec(select(User).where(User.username == form_data.username)).first()
        if not user:
             # UPDATED: Specific error for missing user
             raise HTTPException(status_code=400, detail="User not found, please create a new account")
        
        # 2. Check password
        if not verify_password(form_data.password, user.hashed_password):
            raise HTTPException(status_code=400, detail="Incorrect password")
        
        access_token = create_access_token(data={"sub": user.username})
        return {"access_token": access_token, "token_type": "bearer"}

# --- 7. SECURE APP ENDPOINTS (Requires Login) ---

def process_entry_logic(text: str, date_str: str, user: User):
    # AI Inference
    inputs = tokenizer(text, return_tensors="pt", truncation=True, padding=True)
    with torch.no_grad():
        outputs = emotion_model(**inputs)
    
    probs = torch.sigmoid(outputs.logits).squeeze().tolist()
    max_idx = probs.index(max(probs))
    emotion = EMOTION_LABELS.get(max_idx, "neutral")
    score = max(probs)

    # Database Save (Linked to User ID)
    with Session(engine) as session:
        encrypted_text = cipher_suite.encrypt(text.encode())
        entry_date = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()

        new_entry = JournalEntry(
            user_id=user.id, 
            date=entry_date, 
            encrypted_content=encrypted_text, 
            emotion_primary=emotion, 
            emotion_score=score
        )
        session.add(new_entry)
        session.commit()

        # Fetch User Specific History
        history_query = select(JournalEntry).where(
            JournalEntry.user_id == user.id,
            JournalEntry.date >= entry_date - datetime.timedelta(days=90)
        )
        history_results = session.exec(history_query).all()
        
        # Scientific Insight Logic (CBT)
        insight = "Take a moment to breathe."
        if emotion in ["anger", "annoyance"]: insight = "Try the physiological sigh: 2 short inhales, 1 long exhale to reset autonomic nervous system."
        if emotion in ["joy", "excitement", "optimism"]: insight = "Savoring: Write down 3 specific sensory details about this feeling to strengthen neural pathways."
        if emotion in ["sadness", "grief", "disappointment"]: insight = "Behavioral Activation: Do one very small, functional task (like washing a cup) to break the inertia."
        if emotion in ["fear", "nervousness"]: insight = "Box Breathing: Inhale 4s, Hold 4s, Exhale 4s, Hold 4s to activate the parasympathetic system."

    return {
        "emotion": emotion,
        "score": round(score * 100, 2),
        "insight": insight,
        "history_count": len(history_results)
    }

@app.post("/analyze-text")
def analyze_text(
    text: str = Form(...), 
    date: str = Form(...), 
    current_user: User = Depends(get_current_user)
):
    return process_entry_logic(text, date, current_user)

@app.post("/analyze-audio")
def analyze_audio(
    file: UploadFile = File(...), 
    date: str = Form(...),
    current_user: User = Depends(get_current_user)
):
    filename = file.filename or "recording.webm"
    file_ext = os.path.splitext(filename)[1] or ".webm"

    # Secure temp file handling
    with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = tmp.name

    try:
        result = whisper_model.transcribe(tmp_path)
        transcribed_text = result.get("text", "").strip()
        if not transcribed_text:
            raise HTTPException(status_code=400, detail="Could not transcribe audio.")

        response = process_entry_logic(transcribed_text, date, current_user)
        response["is_audio"] = True
        response["transcription"] = transcribed_text
        return response

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        try:
            if os.path.exists(tmp_path): os.remove(tmp_path)
        except: pass

@app.get("/history")
def get_history(current_user: User = Depends(get_current_user)):
    with Session(engine) as session:
        # Only return data for the logged-in user
        query = select(JournalEntry).where(JournalEntry.user_id == current_user.id).order_by(JournalEntry.date)
        entries = session.exec(query).all()
        data = [{"date": e.date, "emotion": e.emotion_primary} for e in entries]
    return data

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)