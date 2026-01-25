import csv
import datetime
from io import StringIO

from sqlmodel import Session, select

from models import JournalEntry
from constants.emotions import NEGATIVE_EMOTIONS

# -------------------------------------------------
# Report range configuration
# -------------------------------------------------
RANGE_DAYS = {
    "weekly": 7,
    "monthly": 30,
    "yearly": 365
}

# -------------------------------------------------
# Generate modern CSV report (Excel-safe)
# -------------------------------------------------
def generate_csv_report(user_id, range_type, engine):
    days = RANGE_DAYS.get(range_type, 30)

    end_date = datetime.date.today()
    start_date = end_date - datetime.timedelta(days=days)

    with Session(engine) as session:
        entries = session.exec(
            select(JournalEntry)
            .where(JournalEntry.user_id == user_id)
            .where(JournalEntry.date >= start_date)
            .order_by(JournalEntry.date)
        ).all()

    output = StringIO()
    output.write("\ufeff")  # ✅ UTF-8 BOM for Excel compatibility

    writer = csv.writer(output)

    # -------------------------------------------------
    # Report heading
    # -------------------------------------------------
    writer.writerow([
        f"EmoJournal — {range_type.capitalize()} Emotion Report"
    ])
    writer.writerow([
        f"Date Range: {start_date} → {end_date}"
    ])
    writer.writerow([])  # spacing

    # -------------------------------------------------
    # Table header
    # -------------------------------------------------
    writer.writerow([
        "Date",
        "Input Sentence",
        "Emotion(s)",
        "Suggested Action"
    ])

    # -------------------------------------------------
    # Data rows
    # -------------------------------------------------
    for entry in entries:
        # Decode stored input text (safe fallback)
        try:
            input_sentence = entry.input_sentence
        except Exception:
            input_sentence = "[Encrypted Input]"

        emotion = entry.emotion_primary

        if emotion in NEGATIVE_EMOTIONS:
            suggested_action = (
                "Try grounding exercises, reflective journaling, "
                "or light physical activity"
            )
        else:
            suggested_action = (
                "Reinforce habits or situations that contributed "
                "to this positive emotional state"
            )

        # ✅ Excel-safe date (prevents #######)
        safe_date = f'="{entry.date.strftime("%Y-%m-%d")}"'

        writer.writerow([
            safe_date,
            input_sentence,
            emotion,
            suggested_action
        ])

    return output.getvalue(), start_date, end_date
