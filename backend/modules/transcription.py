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
from modules.model_registry import get_transcription_model, get_transcription_metadata

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

def transcribe_audio(audio_path, job_id, language=None):
    """Transcribe an audio file using the configured model"""
    try:
        logger.info(f"Transcribing audio for job {job_id} with language={language}")
        
        # Get audio duration
        from pydub import AudioSegment
        audio = AudioSegment.from_file(audio_path)
        duration_seconds = len(audio) / 1000.0
        logger.info(f"Audio duration: {duration_seconds:.2f} seconds")
        
        # Get the transcription model with debug logs
        logger.info("Attempting to retrieve model from registry")
        model = get_transcription_model()
        
        # Debug logging about the model
        if model is not None:
            logger.info(f"Retrieved model from registry. Model ID: {id(model)}")
        else:
            logger.error("Model retrieval returned None")
            
        metadata = get_transcription_metadata()
        logger.info(f"Model metadata from registry: {metadata}")
        
        if model is None:
            errorMsg = "No Whisper model loaded. Please configure and load a model first."
            logger.error(errorMsg)
            active_jobs[job_id]["status"] = "error"
            active_jobs[job_id]["error"] = errorMsg
            raise Exception(errorMsg)
        
        # Process based on model type
        model_type = metadata.get('type')
        logger.info(f"Processing with model type: {model_type}")
        
        if model_type == "whisper":
            logger.info("Using standard Whisper model for transcription")
            
            # Transcribe with Whisper
            transcript_options = {}
            if language:
                transcript_options["language"] = language
                
            logger.info(f"Starting Whisper transcription with options: {transcript_options}")
            result = model.transcribe(audio_path, **transcript_options)
            logger.info("Whisper transcription completed successfully")
            
            # Process result...
            # ...existing code...
            
        elif model_type == "faster-whisper":
            logger.info("Using Faster-Whisper model for transcription")
            
            # Set language if specified
            language_option = language if language else None
            logger.info(f"Using language option: {language_option}")
            
            # Transcribe with Faster-Whisper
            logger.info("Starting Faster-Whisper transcription")
            segments, info = model.transcribe(audio_path, language=language_option)
            logger.info(f"Faster-Whisper transcription completed. Info: {info}")
            
            # Process segments...
            # ...existing code...
            
        else:
            errorMsg = f"Unknown model type: {model_type}"
            logger.error(errorMsg)
            active_jobs[job_id]["status"] = "error"
            active_jobs[job_id]["error"] = errorMsg
            raise Exception(errorMsg)
        
        # ...existing code...
        
    except Exception as e:
        logger.error(f"Error transcribing audio: {str(e)}")
        logger.exception(e)  # Log full traceback
        active_jobs[job_id]["status"] = "error"
        active_jobs[job_id]["error"] = str(e)
        raise

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

# Import our new debug module
from modules.debug import trace_function, debug_logger

@trace_function  # Add tracing to this function
def process_video(youtube_url, job_id, language=None):
    """Process a YouTube video: download audio, transcribe, then generate notes"""
    from config import active_jobs, transcription_logs
    
    try:
        # Update job status to downloading
        active_jobs[job_id]["status"] = "downloading"
        transcription_logs[job_id] = []
        
        debug_logger.info(f"Starting job {job_id} - Downloading video: {youtube_url}")
        
        # Download audio function implementation with error handling
        audio_path = download_youtube_audio(youtube_url, job_id)
        
        if not audio_path or not os.path.exists(audio_path):
            debug_logger.error(f"Failed to download audio for job {job_id}")
            active_jobs[job_id]["status"] = "error"
            active_jobs[job_id]["error"] = "Failed to download audio"
            return
            
        debug_logger.info(f"Audio downloaded for job {job_id} to {audio_path}")
        
        # Update job status to transcribing
        active_jobs[job_id]["status"] = "transcribing"
        
        # Transcribe audio function implementation
        debug_logger.info(f"Starting transcription for job {job_id} with language={language}")
        
        transcript_result = transcribe_audio(audio_path, job_id, language)
        
        if not transcript_result:
            debug_logger.error(f"Failed to transcribe audio for job {job_id}")
            active_jobs[job_id]["status"] = "error"
            active_jobs[job_id]["error"] = "Failed to transcribe audio"
            return
            
        debug_logger.info(f"Transcription complete for job {job_id}")
        
        # Update job status to generating notes
        active_jobs[job_id]["status"] = "generating_notes"
        
        # Generate notes function implementation
        debug_logger.info(f"Generating notes for job {job_id}")
        try:
            from modules.summarization import generate_notes
            notes = generate_notes(job_id)
            debug_logger.info(f"Notes generated for job {job_id}")
        except Exception as e:
            debug_logger.error(f"Error generating notes for job {job_id}: {str(e)}")
            debug_logger.exception(e)
            # Continue even if notes generation fails
        
        # Update job status to complete
        active_jobs[job_id]["status"] = "complete"
        debug_logger.info(f"Job {job_id} completed successfully")
        
    except Exception as e:
        debug_logger.error(f"Error processing video for job {job_id}: {str(e)}")
        debug_logger.exception(e)
        active_jobs[job_id]["status"] = "error"
        active_jobs[job_id]["error"] = str(e)
