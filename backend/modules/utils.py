import os
import time
import logging
import nltk
import subprocess
from config import logger

def ensure_nltk_resources():
    """Download required NLTK resources if they're not already available"""
    try:
        nltk.data.find('tokenizers/punkt')
    except LookupError:
        nltk.download('punkt')
        logger.info("Downloaded NLTK resource: punkt")

    try:
        nltk.data.find('tokenizers/punkt_tab')
    except LookupError:
        nltk.download('punkt_tab')
        logger.info("Downloaded NLTK resource: punkt_tab")

def formatTime(seconds):
    """Format seconds into minutes:seconds format"""
    minutes = int(seconds / 60)
    secs = int(seconds % 60)
    return f"{minutes}:{secs:02d}"

def append_transcription_log(job_id, text, transcription_logs):
    """Append a log entry to the transcription logs for a job"""
    if job_id not in transcription_logs:
        transcription_logs[job_id] = []
    
    # Add timestamp to logs for UI only
    import datetime
    timestamp = datetime.datetime.now().strftime('%H:%M:%S')
    log_entry = f"{timestamp} - {text}"
    transcription_logs[job_id].append(log_entry)
    
    # Keep only the latest 100 logs to prevent memory bloat
    if len(transcription_logs[job_id]) > 100:
        transcription_logs[job_id] = transcription_logs[job_id][-100:]

def get_audio_duration(audio_path):
    """Get the duration of an audio file in seconds"""
    try:
        result = subprocess.run(
            ['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 
             'default=noprint_wrappers=1:nokey=1', audio_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT
        )
        audio_duration = float(result.stdout)
        logger.info(f"Audio duration: {audio_duration:.2f} seconds")
        return audio_duration
    except Exception as e:
        logger.warning(f"Couldn't determine audio duration: {str(e)}")
        return 0

def similar(str1, str2, threshold=0.7):
    """Check if two strings are similar using word-based comparison"""
    # First check: if lengths are very different, they're not similar
    if abs(len(str1) - len(str2)) / max(len(str1), len(str2)) > (1 - threshold):
        return False
    
    # Word-based comparison
    words1 = set(str1.lower().split())
    words2 = set(str2.lower().split())
    
    # Calculate Jaccard similarity
    intersection = len(words1.intersection(words2))
    union = len(words1.union(words2))
    
    if union == 0:  # Edge case
        return False
        
    similarity = intersection / union
    return similarity > threshold

def get_model_path(model_type):
    """Get the path for storing a specific model type"""
    from config import MODEL_DIR
    path = os.path.join(MODEL_DIR, model_type)
    os.makedirs(path, exist_ok=True)
    return path
