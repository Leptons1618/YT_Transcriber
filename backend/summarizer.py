from transformers import pipeline

class SummarizerManager:
    def __init__(self, config):
        self.config = config
        self.summarizer = None
        self.available_summarizers = config.get('available_summarizers', {})
    
    def load_model(self, model_key):
        try:
            # Get the full model name from the available_summarizers dictionary
            if model_key in self.available_summarizers and 'name' in self.available_summarizers[model_key]:
                full_model_name = self.available_summarizers[model_key]['name']
                print(f"Loading summarizer model: {full_model_name}")
                
                # Use the full model name (including organization prefix) when loading
                self.summarizer = pipeline("summarization", model=full_model_name)
                return True, f"Successfully loaded summarizer model: {full_model_name}"
            else:
                return False, f"Model '{model_key}' not found in available summarizers"
        except Exception as e:
            return False, f"Error loading summarizer: {str(e)}"
    
    def summarize(self, text, max_length=150, min_length=40):
        if not self.summarizer:
            raise ValueError("Summarizer model not loaded")
        
        # Handle very long text by splitting into chunks if necessary
        if len(text.split()) > 1024:
            # Logic for chunking long text
            # ...
            pass
        
        # Use the pipeline with similar parameters as your example
        result = self.summarizer(text, max_length=max_length, min_length=min_length, do_sample=False)
        
        if result and len(result) > 0:
            return result[0]['summary_text']
        return ""
