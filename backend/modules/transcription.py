import os
import time
import json
import threading
import yt_dlp
import torch
import whisper
from nltk.tokenize import sent_tokenize
from config import logger, active_jobs, transcription_logs, AUDIO_DIR, TRANSCRIPT_DIR, NOTES_DIR
from modules.utils import append_transcription_log, formatTime, get_audio_duration, get_model_path
from modules.summarization import generate_notes
import config

def download_youtube_audio(youtube_url, job_id):
    """Download audio from a YouTube video"""
    logger.info(f"Job {job_id}: Starting audio download using yt-dlp")
    output_template = os.path.join(AUDIO_DIR, f"{job_id}.%(ext)s")
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': output_template,
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
    }
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([youtube_url])
    logger.info(f"Job {job_id}: Audio downloaded successfully")
    return os.path.join(AUDIO_DIR, f"{job_id}.mp3")

def transcribe_audio(audio_path, model_type="whisper", model_size="medium", language=None):
    """Transcribe audio using the specified model and language"""
    global transcription_model, current_whisper_model_size
    logger.info(f"Transcribing audio with {model_type} model ({model_size}) from {audio_path}, language: {language or 'auto'}")
    
    if not os.path.exists(audio_path):
        logger.error(f"Audio file not found: {audio_path}")
        raise FileNotFoundError(f"Audio file not found: {audio_path}")
    
    # Extract job_id and log the start of transcription
    job_id = os.path.basename(audio_path).split('.')[0]
    append_transcription_log(job_id, "Transcription started...", transcription_logs)
    
    # Get audio duration for progress reporting
    audio_duration = get_audio_duration(audio_path)

    if model_type == "faster-whisper":
        from faster_whisper import WhisperModel
        model_path = get_model_path("faster-whisper")
        
        logger.info(f"Loading Faster-Whisper {model_size} model")
        try:
            faster_model = WhisperModel(
                model_size, 
                device="cuda", 
                compute_type="float16", 
                download_root=model_path,
                cpu_threads=4,
                num_workers=2
            )
            
            # Use efficient batched processing
            logger.info(f"Starting transcription for job {job_id}")
            segments = []
            segment_count = 0
            last_log_time = time.time()
            
            # Set language to None for auto-detection if it's empty
            language_param = None if not language else language
            
            # Process segments with optimization options and language
            for segment in faster_model.transcribe(
                audio_path,
                beam_size=5,
                language=language_param,  # Use modified language parameter
                task="transcribe",
                vad_filter=True,
                vad_parameters=dict(min_silence_duration_ms=500),
            )[0]:
                segment_count += 1
                segments.append(segment)
                
                # Format and log each segment but don't flood logs
                formatted_time = formatTime(segment.start)
                log_message = f"{formatted_time} - {segment.text}"
                append_transcription_log(job_id, log_message, transcription_logs)
                
                # Report progress every 10 seconds
                current_time = time.time()
                if (current_time - last_log_time) > 10:
                    progress = min(100, int((segment.end / audio_duration * 100) if audio_duration else 0))
                    logger.info(f"Job {job_id}: Transcription progress ~{progress}% ({segment_count} segments)")
                    last_log_time = current_time
            
            logger.info(f"Job {job_id}: Transcription complete with {segment_count} segments")
            
            # Create optimized output
            transcript = " ".join([s.text for s in segments])
            formatted_segments = [{"text": s.text, "start": s.start, "end": s.end} for s in segments]
            return transcript, formatted_segments
        
        except Exception as e:
            logger.error(f"Error in transcription: {str(e)}")
            raise
    
    else:
        # For OpenAI Whisper model
        if config.transcription_model is None:
            errorMsg = "No Whisper model loaded. Please configure and load a model first."
            logger.error(errorMsg)
            raise Exception(errorMsg)
        
        # Start transcription
        logger.info(f"Starting OpenAI Whisper transcription for job {job_id}")
        append_transcription_log(job_id, "Starting OpenAI Whisper transcription...", transcription_logs)
        
        try:
            # Use the already loaded model with optimized settings
            result = config.transcription_model.transcribe(
                audio_path,
                fp16=True,
                beam_size=5,
                best_of=5,
                language=language  # Add language parameter
            )
            
            # Log some segments for UI display without flooding logs
            total_segments = len(result["segments"])
            log_interval = max(1, total_segments // 20)  # log ~20 segments
            
            for i, segment in enumerate(result["segments"]):
                if i % log_interval == 0 or i == total_segments - 1:
                    formatted_time = formatTime(segment['start'])
                    log_message = f"{formatted_time} - {segment['text']}"
                    append_transcription_log(job_id, log_message, transcription_logs)
            
            logger.info(f"Job {job_id}: Whisper transcription complete with {total_segments} segments")
            return result["text"], result["segments"]
            
        except Exception as e:
            logger.error(f"Error in Whisper transcription: {str(e)}")
            raise

def process_video(youtube_url, job_id, language=None):
    """Main processing function for a video - downloads, transcribes and generates notes"""
    try:
        with threading.Lock():
            if job_id not in active_jobs:
                active_jobs[job_id] = {"url": youtube_url, "created_at": time.time()}
            active_jobs[job_id]["status"] = "downloading"
            if language:
                active_jobs[job_id]["language"] = language
        logger.info(f"Job {job_id}: Downloading audio...")
        
        audio_path = download_youtube_audio(youtube_url, job_id)
        
        with threading.Lock():
            active_jobs[job_id]["status"] = "transcribing"
            active_jobs[job_id]["audio_path"] = audio_path
        logger.info(f"Job {job_id}: Audio downloaded to {audio_path}. Transcribing...")
        
        # Retrieve configuration for model
        model_type = active_jobs[job_id].get("model_type", "whisper")
        model_size = active_jobs[job_id].get("model_size", "medium")
        language = active_jobs[job_id].get("language", None)
        
        # Transcribe audio based on selected model
        transcript, segments = transcribe_audio(audio_path, model_type, model_size, language)
        
        # Get video metadata BEFORE saving transcript
        ydl_opts = {
            'quiet': True,
            'no_warnings': True
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(youtube_url, download=False)
        
        # Save transcript including title, channel and language
        transcript_data = {
            "text": transcript,
            "segments": segments,
            "title": info.get('title', 'Unknown'),
            "channel": info.get('uploader', 'Unknown'),
            "youtube_url": youtube_url,
            "language": language
        }
        transcript_path = os.path.join(TRANSCRIPT_DIR, f"{job_id}.json")
        with open(transcript_path, 'w') as f:
            json.dump(transcript_data, f)
        logger.info(f"Job {job_id}: Transcript saved at {transcript_path}")
        
        with threading.Lock():
            active_jobs[job_id]["status"] = "generating_notes"
            active_jobs[job_id]["transcript_path"] = transcript_path
        
        # Generate and save notes with language support
        notes = generate_notes(transcript, language)
        notes["title"] = transcript_data["title"]
        notes_path = os.path.join(NOTES_DIR, f"{job_id}.json")
        with open(notes_path, 'w') as f:
            json.dump(notes, f)
        logger.info(f"Job {job_id}: Notes saved at {notes_path}")
        
        with threading.Lock():
            active_jobs[job_id]["status"] = "complete"
            active_jobs[job_id]["notes_path"] = notes_path
            active_jobs[job_id]["title"] = transcript_data["title"]
            active_jobs[job_id]["channel"] = transcript_data["channel"]
            active_jobs[job_id]["thumbnail"] = info.get('thumbnail', '')
        logger.info(f"Job {job_id}: Processing complete")
    
    except Exception as e:
        with threading.Lock():
            if job_id not in active_jobs:
                active_jobs[job_id] = {"url": youtube_url, "created_at": time.time()}
            active_jobs[job_id]["status"] = "error"
            active_jobs[job_id]["error"] = str(e)
        logger.error(f"Job {job_id}: Error occurred - {str(e)}", exc_info=True)
