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
from modules.model_registry import (
    store_transcription_model, 
    get_transcription_model,
    get_transcription_metadata,
    store_summarizer_model, 
    get_summarizer_model
)

# Set CUDA memory allocation configuration - update the existing setting
os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "max_split_size_mb:512"

def set_transcription_model(model):
    """Store the transcription model globally"""
    global transcription_model
    transcription_model = model
    return model

def get_transcription_model():
    """Get the currently loaded transcription model"""
    global transcription_model
    return transcription_model

def set_summarizer(model):
    """Store the summarizer model globally"""
    return store_summarizer_model(model, 'transformer')

def get_summarizer():
    """Get the currently loaded summarizer model"""
    global summarizer
    return summarizer

def load_whisper_model(model_size="medium"):
    """Load a Whisper model of the specified size"""
    try:
        import whisper
        logger.info(f"Loading Whisper {model_size} model")
        model = whisper.load_model(model_size)
        
        # Store in registry with detailed logging
        logger.info(f"Storing Whisper {model_size} model in registry")
        store_transcription_model(model, 'whisper', model_size)
        
        # Test retrieving model using the registry's function
        test_model = get_transcription_model()
        if test_model is not None:
            logger.info(f"Model successfully verified in registry. ID: {id(test_model)}")
        else:
            logger.error("Failed to verify model in registry after storage")
        
        logger.info(f"Successfully loaded Whisper {model_size} model")
        return True, f"Loaded Whisper {model_size} model"
    except Exception as e:
        logger.error(f"Error loading Whisper model: {str(e)}")
        logger.exception(e)
        return False, f"Error loading Whisper model: {str(e)}"

def verify_faster_whisper_model(model_size="medium"):
    """Verify a Faster-Whisper model is available and prepare it for later use"""
    try:
        # Just verify that the model can be loaded
        from faster_whisper import WhisperModel
        
        # Setup model options
        compute_type = "float16" 
        if model_size in ["tiny", "base"]:
            compute_type = "int8"
        
        logger.info(f"Verifying Faster-Whisper {model_size} model")
        # Create the model
        model = WhisperModel(model_size, device="cuda", compute_type=compute_type)
        
        # Store in registry with detailed logging
        logger.info(f"Storing Faster-Whisper {model_size} model in registry")
        store_transcription_model(model, 'faster-whisper', model_size)
        
        # Verify model is retrievable
        test_model = get_transcription_model()
        if test_model is not None:
            logger.info(f"Model successfully verified in registry. ID: {id(test_model)}")
        else:
            logger.error("Failed to verify model in registry after storage")
        
        logger.info(f"Verified Faster-Whisper {model_size} model")
        return True, f"Verified Faster-Whisper {model_size} model"
    except Exception as e:
        logger.error(f"Error verifying Faster-Whisper model: {str(e)}")
        logger.exception(e)
        return False, f"Error verifying Faster-Whisper model: {str(e)}"

def get_available_summarizers():
    """Get available summarizer models"""
    return {
        'bart-large-cnn': {
            'name': 'facebook/bart-large-cnn',
            'size': '1.6GB',
            'description': 'High quality but requires more memory'
        },
        'bart-base-cnn': {
            'name': 'sshleifer/distilbart-cnn-6-6',
            'size': '680MB',
            'description': 'Good balance of quality and speed'
        },
        't5-small': {
            'name': 't5-small',
            'size': '300MB',
            'description': 'Fast but less detailed summaries'
        },
        'flan-t5-small': {
            'name': 'google/flan-t5-small',
            'size': '300MB',
            'description': 'Improved small model with instruction tuning'
        },
        'distilbart-xsum': {
            'name': 'sshleifer/distilbart-xsum-12-1',
            'size': '400MB',
            'description': 'Efficient model focused on extreme summarization'
        }
    }

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
