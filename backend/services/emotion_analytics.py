import datetime
from sqlmodel import Session, select
from models import JournalEntry


def get_emotion_timeline(user_id: int, days: int, engine) -> list[dict]:
    """
    Returns a list of {date, emotions} dicts for the given user
    over the past `days` days, ordered ascending by date.

    FIX: This function was defined but never called — main.py had a
    duplicate inline implementation in the /timeline endpoint.
    main.py now imports and uses this function directly.
    """
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
            "date":     r.date.isoformat(),
            "emotions": r.emotion_primary.split(","),
        }
        for r in rows
    ]


def get_emotion_counts(user_id: int, days: int, valid_emotions: set, engine) -> dict:
    """
    Returns aggregated emotion frequency counts for the given user
    over the past `days` days.

    FIX: /emotion-counts in main.py had its own inline aggregation loop.
    Extracted here so analytics logic lives in one place.
    """
    from collections import defaultdict

    start = datetime.date.today() - datetime.timedelta(days=days)

    with Session(engine) as session:
        rows = session.exec(
            select(JournalEntry)
            .where(JournalEntry.user_id == user_id)
            .where(JournalEntry.date >= start)
        ).all()

    counts: dict = defaultdict(int)
    for row in rows:
        for emo in row.emotion_primary.split(","):
            emo = emo.strip()
            if emo in valid_emotions:
                counts[emo] += 1

    return {
        "emotion_counts": dict(counts),
        "total_entries":  len(rows),
        "period_days":    days,
    }