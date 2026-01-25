# backend/constants/emotions.py
# GoEmotions emotion taxonomy (28 labels)

EMOTION_LABELS = [
    "admiration",
    "amusement",
    "anger",
    "annoyance",
    "approval",
    "caring",
    "confusion",
    "curiosity",
    "desire",
    "disappointment",
    "disapproval",
    "disgust",
    "embarrassment",
    "excitement",
    "fear",
    "gratitude",
    "grief",
    "joy",
    "love",
    "nervousness",
    "optimism",
    "pride",
    "realization",
    "relief",
    "remorse",
    "sadness",
    "surprise",
    "neutral",
]

# -------------------------------------------------
# Expanded negative emotion set (for triggers & logic)
# -------------------------------------------------
NEGATIVE_EMOTIONS = {
    # Core negative emotions
    "sadness",
    "grief",
    "fear",
    "anger",
    "disgust",
    "remorse",

    # Secondary / contextual negatives (IMPORTANT)
    "disappointment",
    "embarrassment",
    "nervousness",
    "annoyance",
    "disapproval",
}
