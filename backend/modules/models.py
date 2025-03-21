import torch
import whisper
import gc
import time
import os
import json
import traceback
from transformers import pipeline, AutoModelForSeq2SeqLM, AutoTokenizer
from config import logger, SUMMARIZER_MODELS, MODEL_DIR, CONFIG_FILE
import config
from modules.utils import get_model_path

# Set CUDA memory allocation configuration - update the existing setting
os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "max_split_size_mb:512"

def load_whisper_model(model_size="medium"):
    """Load the OpenAI Whisper model"""
    # Clear GPU memory before loading new model
    if config.transcription_model is not None:
        logger.info("Unloading previous Whisper model")
        del config.transcription_model
        gc.collect()
        torch.cuda.empty_cache()
        time.sleep(1)  # Allow GPU memory to release
    
    logger.info(f"Loading Whisper {model_size} model")
    model_path = get_model_path("whisper")
    
    # Load with optimized settings
    config.transcription_model = whisper.load_model(
        model_size, 
        download_root=model_path,
        device="cuda" if torch.cuda.is_available() else "cpu"
    )
    config.current_whisper_model_size = model_size
    logger.info(f"Completed loading Whisper {model_size} model")
    return True

def verify_faster_whisper_model(model_size="medium"):
    """Verify that a Faster-Whisper model can be loaded"""
    try:
        from faster_whisper import WhisperModel
        model_path = get_model_path("faster-whisper")
        logger.info(f"Verifying Faster-Whisper {model_size} model")
        
        # Just verify the model can be accessed
        _ = WhisperModel(
            model_size, 
            device="cuda", 
            compute_type="float16", 
            download_root=model_path,
            cpu_threads=4
        )
        logger.info(f"Verified Faster-Whisper {model_size} model")
        return True
    except Exception as e:
        logger.error(f"Error verifying Faster-Whisper model: {str(e)}")
        return False

def get_available_summarizers():
    """Return dict of available summarization models"""
    available = {
        # Standard models
        "bart-large-cnn": {
            "size": "large", 
            "description": "High quality English summarization model"
        },
        "facebook/bart-large-xsum": {
            "size": "large", 
            "description": "Extreme summarization model"
        },
        "google/pegasus-xsum": {
            "size": "large", 
            "description": "Abstractive summarization with high coherence"
        },
        # Add specialized Indic language models
        "ai4bharat/IndicBART": {
            "size": "large", 
            "description": "Specialized for Indian languages including Hindi",
            "languages": ["hi"]
        },
        "google/mt5-base": {
            "size": "base", 
            "description": "Optimized for Bengali summarization",
            "languages": ["bn"]
        },
        # Add mBART-large-50 model for multilingual support
        "facebook/mbart-large-50-one-to-many-mmt": {
            "size": "large", 
            "description": "Multilingual model that supports 50 languages",
            "languages": ["hi", "bn", "fr", "de", "es", "ru", "zh", "ja"]  # Add key languages it supports well
        }
    }
    return available

def load_summarizer(model_name=None):
    """Load the summarization model"""
    from config import summarizer
    import config
    from transformers import pipeline
    
    available_models = get_available_summarizers()
    
    # Use default if none specified
    if not model_name or model_name not in available_models:
        model_name = "facebook/bart-large-cnn"
    
    logger.info(f"Loading summarization model: {model_name}")
    
    try:
        # Define model path for saving downloaded models
        model_path = get_model_path("summarizers")
        
        # For specialized Indic language models, we don't load them here
        # They'll be loaded on-demand in the generate_notes function
        if (model_name in ["ai4bharat/IndicBART", "google/mt5-base"] or
            model_name == "facebook/mbart-large-50-one-to-many-mmt"):
            logger.info(f"Model {model_name} will be loaded on-demand when needed")
            config.summarizer = None  # Will use specialized loader
            config.summarizer_model = model_name
            config.summarizer_status = "loaded"
            # Store the model path for later use
            config.summarizer_path = model_path
            return True
        
        # Standard models using the pipeline with cache_dir to save models
        config.summarizer = pipeline(
            "summarization", 
            model=model_name, 
            device=0 if torch.cuda.is_available() else -1,
            model_kwargs={"cache_dir": model_path}
        )
        config.summarizer_model = model_name
        config.summarizer_status = "loaded"
        logger.info(f"Summarizer loaded successfully: {model_name}")
        return True
        
    except Exception as e:
        logger.error(f"Error loading summarizer model: {str(e)}")
        config.summarizer = None
        config.summarizer_status = "error"
        config.summarizer_model = None
        return False

def save_app_config(model_type="whisper", model_size="medium", summarizer_model=None, theme="light"):
    """Save application configuration to config file"""
    summarizer_model = summarizer_model or config.current_summarizer_model
    
    config_data = {
        "model_type": model_type,
        "model_size": model_size,
        "summarizer_model": summarizer_model,
        "theme": theme
    }
    
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config_data, f)
    
    logger.info(f"Configuration saved: {config_data}")
    return config_data

def load_app_config():
    """Load application configuration from config file"""
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            config_data = json.load(f)
    else:
        config_data = {
            "model_type": "whisper",
            "model_size": "medium",
            "theme": "light",
            "summarizer_model": "bart-large-cnn"
        }
    
    # Add model_status to indicate whether models are loaded
    config_data["model_status"] = "loaded" if config.transcription_model is not None else "no model loaded"
    config_data["summarizer_status"] = "loaded" if config.summarizer is not None else "no summarizer loaded"
    
    # Add available summarizer models to the config
    config_data["available_summarizers"] = SUMMARIZER_MODELS
    
    # Add current summarizer model
    config_data["summarizer_model"] = config.current_summarizer_model
    
    return config_data
