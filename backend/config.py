import os
import logging
import datetime
import json

# Base paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKEND_DIR = os.path.join(BASE_DIR, "backend")

# Storage paths
AUDIO_DIR = os.path.join(BACKEND_DIR, 'downloads')
TRANSCRIPT_DIR = os.path.join(BACKEND_DIR, 'transcripts')
NOTES_DIR = os.path.join(BACKEND_DIR, 'notes')
MODEL_DIR = os.path.join(BACKEND_DIR, "models")
LOG_DIR = os.path.join(BACKEND_DIR, "logs")

# Ensure directories exist
for directory in [AUDIO_DIR, TRANSCRIPT_DIR, NOTES_DIR, MODEL_DIR, LOG_DIR]:
    os.makedirs(directory, exist_ok=True)

# Config file path
CONFIG_FILE = os.path.join(BACKEND_DIR, "config.json")

# Set CUDA memory allocation configuration
os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "max_split_size_mb:512"
# Also set this environment variable to avoid CUDA memory allocation issues
os.environ["TRANSFORMERS_OFFLINE"] = "0"  # Allow downloading if needed
os.environ["TOKENIZERS_PARALLELISM"] = "false"  # Avoid parallelism warnings

# Logging configuration
log_filename = os.path.join(LOG_DIR, f"session_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.log")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(log_filename)
    ]
)
logger = logging.getLogger(__name__)

# Dictionary to store real-time transcription logs
transcription_logs = {}

# Track jobs
active_jobs = {}

# Summarizer model definitions
SUMMARIZER_MODELS = {
    "bart-large-cnn": {"name": "facebook/bart-large-cnn", "size": "1.6GB", "description": "High quality but requires more memory"},
    "bart-base-cnn": {"name": "sshleifer/distilbart-cnn-6-6", "size": "680MB", "description": "Good balance of quality and speed"},
    "t5-small": {"name": "t5-small", "size": "300MB", "description": "Fast but less detailed summaries"},
    "flan-t5-small": {"name": "google/flan-t5-small", "size": "300MB", "description": "Improved small model with instruction tuning"},
    "distilbart-xsum": {"name": "sshleifer/distilbart-xsum-12-1", "size": "400MB", "description": "Efficient model focused on extreme summarization"}
}

# Global model variables
transcription_model = None
current_whisper_model_size = None
summarizer = None
current_summarizer_model = "bart-large-cnn"

# Set up paths for different model types
MODEL_DIR = os.path.join(os.path.dirname(__file__), 'models')
AUDIO_DIR = os.path.join(os.path.dirname(__file__), 'downloads')
TRANSCRIPT_DIR = os.path.join(os.path.dirname(__file__), 'transcripts')
NOTES_DIR = os.path.join(os.path.dirname(__file__), 'notes')
LOGS_DIR = os.path.join(os.path.dirname(__file__), 'logs')
CONFIG_FILE = os.path.join(os.path.dirname(__file__), 'config.json')

# Ensure directories exist
for dir_path in [MODEL_DIR, AUDIO_DIR, TRANSCRIPT_DIR, NOTES_DIR, LOGS_DIR]:
    os.makedirs(dir_path, exist_ok=True)
    
# Create summarizer models directory as well
os.makedirs(os.path.join(MODEL_DIR, 'summarizers'), exist_ok=True)

# Add path for storing summarizer model
summarizer_path = None

DEFAULT_CONFIG = {
    'model_type': 'faster-whisper',
    'model_size': 'tiny',
    'summarizer_model': 'bart-large-cnn',
    'theme': 'light',
    'available_summarizers': {
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
}

def load_config():
    """Load configuration from config.json"""
    config_path = os.path.join(os.path.dirname(__file__), 'config.json')
    
    if not os.path.exists(config_path):
        save_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG.copy()
    
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
            
        # Ensure all necessary keys are present
        for key, value in DEFAULT_CONFIG.items():
            if key not in config:
                config[key] = value
                
        return config
    except Exception as e:
        logging.error(f"Error loading config: {e}")
        return DEFAULT_CONFIG.copy()

def save_config(config):
    """Save configuration to config.json"""
    config_path = os.path.join(os.path.dirname(__file__), 'config.json')
    
    try:
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)
        logging.info("Configuration saved")
    except Exception as e:
        logging.error(f"Error saving config: {e}")

def set_summarizer(new_summarizer):
    """Set the global summarizer instance"""
    global summarizer
    summarizer = new_summarizer
    return summarizer

def get_transcription_model():
    """Get the currently loaded transcription model"""
    global transcription_model
    return transcription_model

def set_transcription_model(model):
    """Set the transcription model globally"""
    global transcription_model
    transcription_model = model

def get_summarizer():
    """Get the currently loaded summarizer model"""
    global summarizer
    return summarizer

def set_summarizer(model):
    """Set the summarizer model globally"""
    global summarizer
    summarizer = model
