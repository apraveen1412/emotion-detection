import datetime
from typing import Optional, Dict
from sqlmodel import SQLModel, Field
from sqlalchemy import Column, JSON

class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(index=True, unique=True)
    email: str = Field(index=True, unique=True)
    hashed_password: str
    
    # New Profile Preferences (Defaults to 6 AM and 5 PM)
    default_morning_time: str = Field(default="06:00")
    default_evening_time: str = Field(default="17:00")


class JournalEntry(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    date: datetime.date

    input_sentence: str
    encrypted_content: bytes

    emotion_primary: str
    emotion_scores: Dict[str, float] = Field(
        sa_column=Column(JSON, nullable=False)
    )