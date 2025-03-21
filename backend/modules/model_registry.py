"""
Model Registry - A singleton to store models across processes and threads
"""
import logging

logger = logging.getLogger(__name__)

# Add global variable declaration at the top of the file
transcription_model = None
transcription_metadata = {}

class ModelRegistry:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ModelRegistry, cls).__new__(cls)
            cls._instance._models = {
                'transcription_model': None,
                'summarizer_model': None,
                'metadata': {
                    'type': None,
                    'size': None
                }
            }
        return cls._instance
    
    def store_model(self, model, model_type, model_size):
        """Store transcription model with metadata"""
        logger.info(f"Storing {model_type}/{model_size} model in registry")
        self._models['transcription_model'] = model
        self._models['metadata']['type'] = model_type
        self._models['metadata']['size'] = model_size
        logger.info(f"Model stored successfully: {model_type}/{model_size}")
        # Debug print to verify model is stored
        logger.info(f"Model object ID: {id(model)}")
        return model
    
    def get_model(self):
        """Get the stored transcription model"""
        model = self._models['transcription_model']
        if model:
            logger.info(f"Retrieved model from registry: {self._models['metadata']['type']}/{self._models['metadata']['size']}")
            logger.info(f"Model object ID: {id(model)}")
        else:
            logger.warning("No model found in registry")
        return model
    
    def get_metadata(self):
        """Get metadata about the model"""
        return self._models['metadata']
    
    def store_summarizer(self, model):
        """Store summarizer model"""
        logger.info(f"Storing summarizer model in registry")
        self._models['summarizer_model'] = model
        logger.info(f"Summarizer model stored successfully")
        return model
    
    def get_summarizer(self):
        """Get the stored summarizer model"""
        return self._models['summarizer_model']

# Create a global instance
registry = ModelRegistry()

# Export functions that use the singleton
def store_transcription_model(model, metadata):
    """Store a transcription model in the registry"""
    global transcription_model, transcription_metadata
    transcription_model = model
    transcription_metadata = metadata
    logger.info(f"Model stored successfully: {metadata.get('type')}/{metadata.get('size')}")
    logger.info(f"Model object ID: {id(model)}")

def get_transcription_model():
    """Get the currently loaded transcription model"""
    global transcription_model
    return transcription_model

def get_transcription_metadata():
    """Get metadata for the currently loaded transcription model"""
    global transcription_metadata
    return transcription_metadata

def store_summarizer_model(model):
    return registry.store_summarizer(model)

# Add these aliases for backward compatibility
store_summarization_model = store_summarizer_model  # Alias for backward compatibility
load_summarizer = store_summarizer_model  # Another alias that might be used

def get_summarizer_model():
    return registry.get_summarizer()

# Add this alias to fix the new import error
get_summarization_model = get_summarizer_model  # Alias for backward compatibility

def get_model_status():
    """Get the status of all registered models"""
    model = registry.get_model()
    summarizer = registry.get_summarizer()
    metadata = registry.get_metadata()
    
    return {
        "transcription_loaded": model is not None,
        "transcription_type": metadata.get("type"),
        "transcription_size": metadata.get("size"),
        "summarization_loaded": summarizer is not None
    }
