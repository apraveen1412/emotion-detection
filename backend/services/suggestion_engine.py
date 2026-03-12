import random
from collections import defaultdict
from constants.emotions import NEGATIVE_EMOTIONS

# Emotion clusters for targeted suggestions
ANXIETY_EMOTIONS = {"fear", "nervousness"}
DEPRESSIVE_EMOTIONS = {"sadness", "grief", "disappointment", "remorse"}
ANGER_EMOTIONS = {"anger", "annoyance", "disapproval", "disgust"}
STRESS_EMOTIONS = {"confusion", "embarrassment"}

def get_suggestion_tip(current_emotions):
    # 1. CHECK FOR MIXED EMOTIONS (Emotional Rollercoaster Day)
    has_pos = any(e not in NEGATIVE_EMOTIONS and e != "neutral" for e in current_emotions)
    has_neg = any(e in NEGATIVE_EMOTIONS for e in current_emotions)
    
    if has_pos and has_neg and len(current_emotions) >= 2:
        tips = [
            "Your day had distinct highs and lows. Practice 'Emotional Validation'—acknowledge that it is completely normal to hold conflicting feelings simultaneously.",
            "You experienced an emotional rollercoaster today. Do a 10-minute 'Wind Down' meditation to separate the stress of the day from your evening relaxation time.",
            "Today was complex. Try writing down the specific triggers for the negative shifts so you can anticipate them, while taking a moment to be grateful for the positive moments.",
            "Experiencing emotional whiplash can be exhausting. Engage in a low-stakes, comforting activity tonight—like watching a favorite anime or taking a hot bath—to let your nervous system reset.",
            "Your diary shows a mix of contrasting emotions. Step away from your screens and take a 15-minute quiet walk to let your brain process the complexities of today."
        ]
        return random.choice(tips)

    # 2. TARGET THE DOMINANT EMOTION
    primary_emotion = current_emotions[0] if current_emotions else "neutral"

    if primary_emotion in ANXIETY_EMOTIONS:
        tips = [
            "Practice the 5-4-3-2-1 grounding technique: identify 5 things you can see, 4 you can touch, 3 you can hear, 2 you can smell, and 1 you can taste.",
            "Do a 10-minute restorative yoga flow focusing on deep stretches and grounding poses like Child's Pose.",
            "Step outside for a short 15-minute walk to change your environment and reset your nervous system.",
            "Play an immersive space exploration or survival game for 20 minutes to completely shift your cognitive focus.",
            "Try a guided meditation focused on body scanning to release physical tension.",
            "Work on a low-stakes UI design task in Figma to engage your creative brain without any coding pressure.",
            "Take a cold shower or splash cold water on your face to trigger the mammalian dive reflex and rapidly lower anxiety.",
            "Do some light journaling about your day—getting chaotic thoughts out of your head and onto paper reduces their power.",
            "Listen to a podcast about recent space discoveries or science to redirect your thoughts toward something expansive and fascinating.",
            "Spend 15 minutes organizing your developer portfolio layout—focusing on structured, predictable tasks brings a sense of control."
        ]
    elif primary_emotion in DEPRESSIVE_EMOTIONS:
        tips = [
            "Engage in 'Behavioral Activation'—choose one small, achievable task (like organizing your desk or doing the dishes) to build momentum.",
            "Take a break and watch an episode of an adventurous, high-energy anime like One Piece to lift your spirits and find some inspiration.",
            "Go out for a quick coffee or tea at a local shop to be around others and physically change your scenery.",
            "Do 5 minutes of light cardio or stretching to get your blood flowing and artificially trigger endorphin release.",
            "Spend 15 minutes working on a creative hobby, like sketching out a YouTube thumbnail or planning a new video concept.",
            "Plan a short weekend getaway or day trip—perhaps looking up nearby nature spots or waterfalls to give yourself something to look forward to.",
            "Call or text a family member just to check in. Connecting with loved ones can provide a strong emotional anchor.",
            "Read a chapter of a manga you enjoy. Escaping into a well-crafted story can provide a necessary mental reset.",
            "Watch some high-quality cinematic B-roll footage online to spark your creative drive and visual inspiration.",
            "Cook a simple, nourishing meal. The step-by-step physical process of cooking is inherently grounding and rewarding."
        ]
    elif primary_emotion in ANGER_EMOTIONS:
        tips = [
            "Utilize physiological regulation: try 'Box Breathing' (inhale 4s, hold 4s, exhale 4s, hold 4s) to directly lower your heart rate.",
            "Channel the energy into a quick, high-intensity workout or a brisk jog around your neighborhood.",
            "Write down exactly what is frustrating you in a private note, then physically tear it up to symbolize releasing the anger.",
            "Distract your mind with a complex task, like debugging a piece of MERN stack code or optimizing a database query.",
            "Engage in a fast-paced or competitive video game to safely burn off excess adrenaline.",
            "Put on some high-energy music and spend 10 minutes doing an intensive chore, like cleaning your room or workspace.",
            "Do 20 push-ups or jumping jacks right now. Forcing sudden physical exertion breaks the cycle of angry rumination.",
            "Work on training or fine-tuning an AI model—channeling frustration into a highly logical, technical problem can be incredibly effective.",
            "Practice progressive muscle relaxation: tense every muscle in your body as hard as you can for 5 seconds, then completely release.",
            "Take a brisk 15-minute walk outside. The bilateral stimulation of walking helps the brain process intense, heated emotions."
        ]
    elif primary_emotion in STRESS_EMOTIONS:
        tips = [
            "Apply cognitive reframing: write down the stressful situation, identify the emotion, and challenge catastrophic thoughts with objective facts.",
            "Step away from your screen and do a quick 10-minute mindfulness meditation focusing strictly on the sensation of your breath.",
            "Play a resource management or strategy game to regain a sense of control and order in a low-stakes environment.",
            "Go outside and spend 10 minutes in nature, focusing on the sounds and sights completely away from digital devices.",
            "Do a 'brain dump'—write out every single pending task on your mind onto a piece of paper to clear your mental RAM.",
            "Break down a large, overwhelming project (like building a full-stack app) into micro-tasks. Do only the first one.",
            "Read up on a fascinating NLP concept or technical blog. Shifting from emotional stress to intellectual curiosity helps recalibrate the brain.",
            "Do a 15-minute digital declutter. Organize your desktop files or clear out your downloads folder to create a sense of visual order.",
            "Watch a quick tutorial on a new web framework. Learning something new shifts the brain from a state of overwhelm to a state of growth.",
            "Do a 5-minute stretching routine focusing specifically on your neck, shoulders, and upper back where stress physically accumulates."
        ]
    else:
        # POSITIVE / NEUTRAL EMOTIONS
        tips = [
            "Maintain this positive state by practicing 'Savoring'—take a moment to consciously reflect on what feels good right now.",
            "Channel this great energy into a passion project, like building out a new feature for your conversational AI app.",
            "Use this positive momentum to plan, script, or record a new creative video while your energy levels are high.",
            "Go out and celebrate this good day—treat yourself to a nice meal, a movie, or a fun outdoor activity.",
            "Share the good mood! Reach out to a friend or family member, or spend some quality time playing with a younger relative.",
            "Dive into learning a complex new topic you've been putting off, like advanced deep learning architectures.",
            "Start wireframing a new idea or side project you’ve been dreaming about while your mind is clear and optimistic.",
            "Go for a long, leisurely walk or drive just to enjoy the day and reflect on your recent wins.",
            "Take 10 minutes to update your resume or developer portfolio to reflect your latest skills and accomplishments.",
            "Spend some time engaging with your favorite fandoms, like reading manga theories or watching a favorite anime movie."
        ]
        
    return random.choice(tips)

def generate_dynamic_suggestions(current_emotions, history_entries):
    """
    Generates personalized suggestions based on today's emotions 
    and all available historical data.
    """
    suggestion_tip = get_suggestion_tip(current_emotions)
    
    formatted_current = ", ".join(current_emotions) if current_emotions else "neutral"
    
    suggestion_dict = {
        "observation": "",
        "insight": suggestion_tip,
        "action": ""
    }
    
    total_entries = len(history_entries)
    
    if total_entries <= 1:
        suggestion_dict["observation"] = f"Your entry today indicates feelings of {formatted_current}."
        suggestion_dict["action"] = "Continue tracking your daily journals to allow the AI to build a reliable longitudinal baseline for deeper insights."
        return current_emotions[0] if current_emotions else "neutral", 0.0, suggestion_dict

    # Aggregate historical baseline
    emotion_counts = defaultdict(float)
    negative_count = 0
    
    for entry in history_entries:
        emotions = entry.emotion_primary.split(",")
        for emo in emotions:
            emotion_counts[emo] += 1.0
            if emo in NEGATIVE_EMOTIONS:
                negative_count += 1

    dominant_history = max(emotion_counts, key=lambda e: emotion_counts[e])
    intensity = round(emotion_counts[dominant_history] / total_entries, 3)
    negative_ratio = negative_count / (total_entries * max(1, len(current_emotions)))
    timeframe = f"over your recorded history ({total_entries} entries)"
    
    has_neg = any(e in NEGATIVE_EMOTIONS for e in current_emotions)

    if has_neg:
        if negative_ratio > 0.5:
            suggestion_dict["observation"] = f"Today you experienced {formatted_current}. Your data shows a sustained pattern of elevated negative emotions (like {dominant_history}) {timeframe}."
            suggestion_dict["action"] = "Because this is a persistent trend, we strongly recommend scheduling the suggested activity below to help break this cycle."
        else:
            suggestion_dict["observation"] = f"Today you experienced {formatted_current}, but your historical baseline {timeframe} remains relatively stable."
            suggestion_dict["action"] = "This is a normal emotional variance. Take a short break and try the suggested activity to recalibrate."
    else:
        if negative_ratio > 0.5:
            suggestion_dict["observation"] = f"Today you experienced {formatted_current}! This is an excellent breakthrough compared to your recent baseline of {dominant_history} {timeframe}."
            suggestion_dict["action"] = "Take note of the events that led to today's positive shift. Engage in the suggested activity to keep the momentum going."
        else:
            suggestion_dict["observation"] = f"Today you experienced {formatted_current}, continuing your stable emotional trend {timeframe}."
            suggestion_dict["action"] = "Your emotional regulation is working well. Enjoy the suggested activity below to reinforce this excellent state."

    return dominant_history, intensity, suggestion_dict