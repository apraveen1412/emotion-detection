import datetime
from typing import Optional, Dict
from sqlmodel import SQLModel, Field
from sqlalchemy import Column, JSON


class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(index=True, unique=True)
    email: str = Field(index=True, unique=True)
    hashed_password: str

    # Scheduling preferences
    default_morning_time: str = Field(default="06:00")
    default_evening_time: str = Field(default="17:00")

    # Security question for password reset
    # FIX: These fields were used in main.py but missing from the model definition,
    # which would cause AttributeError at runtime on /forgot-password/* endpoints.
    security_question: Optional[str] = Field(default=None)
    hashed_security_answer: Optional[str] = Field(default=None)


class JournalEntry(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    date: datetime.date

    # The plaintext sentence used for AI analysis
    input_sentence: str

    # FIX: encrypted_content had no default and was not nullable,
    # causing every INSERT (which never populated this field) to raise
    # a DB integrity error. Made Optional with a default of None.
    encrypted_content: Optional[bytes] = Field(default=None)

    emotion_primary: str
    emotion_scores: Dict[str, float] = Field(
        sa_column=Column(JSON, nullable=False)
    )