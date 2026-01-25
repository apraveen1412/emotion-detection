from collections import defaultdict
from constants.emotions import NEGATIVE_EMOTIONS

# -------------------------------------------------
# Dynamic, history-aware suggestion engine
# -------------------------------------------------

def generate_dynamic_suggestions(entries):
    """
    Generates context-aware suggestions based on recent
    emotional history.

    Returns:
        dominant_emotion (str)
        intensity (float)
        suggestions (List[str])
    """

    if not entries:
        return (
            "neutral",
            0.0,
            [
                "No recent emotional patterns detected.",
                "Continue journaling regularly to build emotional awareness."
            ]
        )

    # -------------------------------------------------
    # Aggregate emotion presence (NOT raw scores)
    # -------------------------------------------------
    emotion_counts = defaultdict(float)

    for entry in entries:
        emotions = entry.emotion_primary.split(",")
        for emo in emotions:
            emotion_counts[emo] += 1.0

    total_entries = len(entries)

    # -------------------------------------------------
    # Determine dominant emotion (frequency-based)
    # -------------------------------------------------
    dominant_emotion = max(
        emotion_counts,
        key=lambda e: emotion_counts[e]
    )

    intensity = round(
        emotion_counts[dominant_emotion] / total_entries,
        3
    )

    # -------------------------------------------------
    # Suggestion logic (pattern-based, not static)
    # -------------------------------------------------
    suggestions = []

    if dominant_emotion in NEGATIVE_EMOTIONS:
        suggestions.append(
            f"Repeated presence of {dominant_emotion} was detected "
            f"across recent journal entries."
        )

        if intensity >= 0.7:
            suggestions.append(
                "This emotion has been persistent. Structured routines, "
                "grounding exercises, or guided reflection may help."
            )
        elif intensity >= 0.4:
            suggestions.append(
                "Moderate emotional recurrence observed. Short breaks, "
                "physical activity, or expressive writing could be beneficial."
            )
        else:
            suggestions.append(
                "Occasional negative emotions are normal. Maintaining "
                "awareness and balance is recommended."
            )

    else:
        suggestions.append(
            f"A recurring positive emotional trend involving "
            f"{dominant_emotion} was observed."
        )

        if intensity >= 0.7:
            suggestions.append(
                "This positive state appears strong and consistent. "
                "Identifying contributing habits may help sustain it."
            )
        elif intensity >= 0.4:
            suggestions.append(
                "Positive emotions are appearing regularly. "
                "Reinforcing daily routines may enhance well-being."
            )
        else:
            suggestions.append(
                "Positive emotions appear intermittently. "
                "Reflecting on triggering moments may help strengthen them."
            )

    # -------------------------------------------------
    # Cross-emotion insight (secondary patterns)
    # -------------------------------------------------
    if len(emotion_counts) > 1:
        suggestions.append(
            "Multiple emotions were observed recently, indicating "
            "emotional complexity rather than a single dominant state."
        )

    return dominant_emotion, intensity, suggestions
