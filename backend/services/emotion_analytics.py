import datetime
from sqlmodel import Session, select
from models import JournalEntry   # adjust import if needed

def get_emotion_timeline(user_id, days, engine):
    start = datetime.date.today() - datetime.timedelta(days=days)

    with Session(engine) as session:
        rows = session.exec(
            select(JournalEntry)
            .where(JournalEntry.user_id == user_id)
            .where(JournalEntry.date >= start)
            .order_by(JournalEntry.date)
        ).all()

    return [
        {
            "date": r.date.isoformat(),
            "emotions": r.emotion_scores
        }
        for r in rows
    ]
