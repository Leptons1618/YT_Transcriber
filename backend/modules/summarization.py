import re
from nltk.tokenize import sent_tokenize
from config import logger
import config  # Import the entire config module
from modules.utils import similar, get_model_path
import langdetect
import config
from transformers import MBartForConditionalGeneration, MBartTokenizer
from modules.models import load_summarizer

# Dictionary of language-specific markers for content analysis
LANGUAGE_MARKERS = {
    "en": {
        "important_phrases": [
            "important", "significant", "key", "critical", "crucial", "essential",
            "main point", "highlight", "takeaway", "conclusion", "in summary",
            "to summarize", "noteworthy", "remember", "notably", "specifically"
        ]
    },
    "hi": {
        "important_phrases": [
            "महत्वपूर्ण", "मुख्य", "प्रमुख", "आवश्यक", "अनिवार्य", "महत्वपूर्ण बिंदु",
            "मुख्य बिंदु", "निष्कर्ष", "सारांश", "संक्षेप में", "विशेष रूप से", "खास तौर पर"
        ]
    },
    "bn": {
        "important_phrases": [
            "গুরুত্বপূর্ণ", "মূল", "প্রধান", "অপরিহার্য", "প্রয়োজনীয়", 
            "মূল বিষয়", "সারসংক্ষেপ", "সংক্ষিপ্তসার", "বিশেষভাবে", "উল্লেখযোগ্য"
        ]
    }
}

# Global multilingual model cache
multilingual_summarizers = {}

# Update the model options for better Hindi and Bengali support
def load_multilingual_summarizer(language):
    """Load or retrieve language-specific summarization model"""
    if language not in multilingual_summarizers:
        logger.info(f"Loading multilingual summarizer for {language}")
        
        try:
            # Get model path for storing models
            model_path = get_model_path("summarizers")
            
            # Determine the best model for the language
            if language == 'hi':
                # IndicBART for Hindi
                model_name = "ai4bharat/IndicBART"
                tokenizer = MBartTokenizer.from_pretrained(model_name, cache_dir=model_path)
                model = MBartForConditionalGeneration.from_pretrained(model_name, cache_dir=model_path)
                tokenizer.src_lang = "hi_IN"
            elif language == 'bn':
                # MT5 for Bengali
                from transformers import MT5ForConditionalGeneration, MT5Tokenizer
                model_name = "google/mt5-base"
                tokenizer = MT5Tokenizer.from_pretrained(model_name, cache_dir=model_path)
                model = MT5ForConditionalGeneration.from_pretrained(model_name, cache_dir=model_path)
            else:
                # For other languages, use mBART-50
                model_name = "facebook/mbart-large-50-one-to-many-mmt"
                tokenizer = MBartTokenizer.from_pretrained(model_name, cache_dir=model_path)
                model = MBartForConditionalGeneration.from_pretrained(model_name, cache_dir=model_path)
                
                # Set source language code for mBART-50
                lang_code_map = {
                    'fr': 'fr_XX', 'de': 'de_DE', 'es': 'es_XX', 
                    'ru': 'ru_RU', 'zh': 'zh_CN', 'ja': 'ja_XX'
                }
                tokenizer.src_lang = lang_code_map.get(language, 'en_XX')
            
            multilingual_summarizers[language] = {
                'model': model,
                'tokenizer': tokenizer,
                'model_type': 'mt5' if 'mt5' in model_name else 'mbart'
            }
            logger.info(f"Successfully loaded {model_name} model for {language}")
            
        except Exception as e:
            logger.error(f"Failed to load multilingual model for {language}: {e}")
            return None
    
    return multilingual_summarizers.get(language)

def detect_language(text):
    """Detect language of the text"""
    try:
        return langdetect.detect(text)
    except:
        return "en"  # Default to English if detection fails

def extract_important_sentences(transcript, language="en"):
    """Extract important sentences directly from transcript with language support"""
    # Get language-specific markers or fall back to English
    language_data = LANGUAGE_MARKERS.get(language, LANGUAGE_MARKERS["en"])
    important_markers = language_data["important_phrases"]
    
    sentences = sent_tokenize(transcript)
    important_sentences = []
    
    for sentence in sentences:
        lower_sentence = sentence.lower()
        
        # Check if the sentence contains any important markers
        if any(marker in lower_sentence for marker in important_markers):
            important_sentences.append(sentence)
            
        # Also include sentences that are within a good information density range
        elif 100 <= len(sentence) <= 200 and len(sentence.split()) >= 10:
            important_sentences.append(sentence)
    
    # Limit to 5 sentences to avoid overwhelming the key points section
    return important_sentences[:5]

def generate_notes(transcript, language=None):
    """Generate summary notes from transcript with language support"""
    logger.info(f"Generating notes from transcript in language: {language or 'auto-detect'}")
    
    # Detect language if not specified
    if not language:
        language = detect_language(transcript)
        logger.info(f"Detected language: {language}")
    
    # Always respect the user's explicitly chosen model
    if config.current_summarizer_model:
        logger.info(f"Using user-selected model: {config.current_summarizer_model}")
        
        # Load the specifically selected model
        if config.current_summarizer_model in ["ai4bharat/IndicBART", "google/mt5-base", "facebook/mbart-large-50-one-to-many-mmt"]:
            multilingual_model = load_multilingual_summarizer(language)
            if multilingual_model:
                # Log a notice if the selected model isn't ideal for the detected language
                if config.current_summarizer_model == "ai4bharat/IndicBART" and language != "hi":
                    logger.info(f"Note: IndicBART is optimized for Hindi but using it for {language} as requested")
                elif config.current_summarizer_model == "google/mt5-base" and language != "bn":
                    logger.info(f"Note: MT5 is optimized for Bengali but using it for {language} as requested")
                
                return generate_multilingual_notes(transcript, language, multilingual_model)
    
    # Previous conditional checks if no specific model was selected
    # Now only reached if user hasn't explicitly chosen a model or if loading that model failed
    
    # Check if we should use a specialized model based on language
    if language in ['hi', 'bn']:
        logger.info(f"No specific model selected, choosing appropriate model for {language}")
        multilingual_model = load_multilingual_summarizer(language)
        if multilingual_model:
            return generate_multilingual_notes(transcript, language, multilingual_model)
    
    # For English or other languages supported by the default summarizer
    logger.info("Generating notes from transcript")
    
    # Check if summarizer is available and properly initialized
    if config.summarizer is None:
        logger.warning("Summarizer not available, attempting to load default model")
        
        # Try to load a summarizer on demand if it's not available
        if not load_summarizer("t5-small"):  # Try to load a lightweight model
            logger.warning("Failed to load summarizer on demand, returning basic summary")
            return {
                "summary": transcript[:1000] + "...",
                "key_points": ["No key points could be generated. Summarizer model could not be loaded."],
                "original_transcript": transcript
            }
    
    try:
        # Verify the summarizer is callable before proceeding
        if not callable(config.summarizer):
            logger.error("Summarizer is not callable, reloading")
            if not load_summarizer():
                return {
                    "summary": transcript[:1000] + "...",
                    "key_points": ["No key points could be generated. Summarizer model is not functioning correctly."],
                    "original_transcript": transcript
                }
        
        # Optimize for performance by creating smarter chunks
        sentences = sent_tokenize(transcript)
        chunks = []
        current_chunk = ""
        
        # Create chunks of roughly 900-1000 characters for summarization
        for sentence in sentences:
            if len(current_chunk) + len(sentence) < 900:
                current_chunk += " " + sentence
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = sentence
        
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        # Skip very short chunks and process in batches for efficiency
        valid_chunks = [chunk for chunk in chunks if len(chunk) >= 50]
        
        # Log information for debugging
        logger.info(f"Processing {len(valid_chunks)} chunks for summarization")
        if len(valid_chunks) == 0:
            logger.warning("No valid chunks found for summarization")
            return {
                "summary": transcript[:1000] + "...",
                "key_points": ["Transcript too short for key point extraction."],
                "original_transcript": transcript
            }
        
        # Process in small batches to avoid OOM errors
        batch_size = 2
        batched_chunks = [valid_chunks[i:i+batch_size] for i in range(0, len(valid_chunks), batch_size)]
        
        # Log batching information
        logger.info(f"Created {len(batched_chunks)} batches of size {batch_size}")
        
        all_summaries = []
        successful_batches = 0
        
        # Use a try-except block for the entire batch processing to avoid partial failures
        try:
            # Double check the summarizer again - IMPORTANT: use config.summarizer instead of reimporting
            if not callable(config.summarizer):
                raise ValueError("Summarizer is not properly initialized")
                
            # Try to detect model type for optimized parameters
            model_type = "unknown"
            try:
                model_type = config.summarizer.model.config.model_type.lower()
                logger.info(f"Using summarization model type: {model_type}")
            except Exception as e:
                logger.warning(f"Could not determine model type: {str(e)}")
            
            # Prepare parameters based on model type
            if "t5" in model_type:
                params = {
                    "max_length": 150,
                    "min_length": 30,
                    "do_sample": False,
                    "truncation": True
                }
            else:  # bart, etc.
                params = {
                    "max_length": 150,
                    "min_length": 30,
                    "do_sample": True,
                    "temperature": 1.0,
                    "num_beams": 4,
                    "truncation": True
                }
                
            # Process all batches with a single parameter set
            for batch_idx, batch in enumerate(batched_chunks):
                try:
                    logger.info(f"Processing batch {batch_idx+1}/{len(batched_chunks)}")
                    summaries = config.summarizer(batch, **params)
                    all_summaries.extend([s['summary_text'] for s in summaries])
                    successful_batches += 1
                    logger.info(f"Successfully processed batch {batch_idx+1}")
                except Exception as batch_error:
                    logger.error(f"Error in batch summarization for batch {batch_idx+1}: {str(batch_error)}")
                    continue
                    
        except Exception as e:
            logger.error(f"Error during summarization: {str(e)}")
            # If we have no summaries at this point, try a fallback approach
            if len(all_summaries) == 0:
                try:
                    # Try once more with a direct approach on smaller chunks
                    logger.info("Attempting fallback summarization with single chunks")
                    for chunk in valid_chunks[:3]:  # Only try first few chunks
                        try:
                            result = config.summarizer(chunk, max_length=100, min_length=20, truncation=True)
                            all_summaries.append(result[0]['summary_text'])
                        except:
                            continue
                except:
                    pass
        
        if len(all_summaries) == 0:
            logger.error("No summaries were generated successfully")
            return {
                "summary": "Failed to generate a summary. Please try a different model or try again later.",
                "key_points": ["Failed to extract key points from the transcript."],
                "original_transcript": transcript
            }
        
        logger.info(f"Generated {len(all_summaries)} summaries from {successful_batches} batches")
        
        # Improved key point extraction with better sentence parsing
        key_points = []
        for summary in all_summaries:
            # First try to find sentences that look like bullet points or key facts
            important_patterns = [
                r'(?:^|\n)(?:\d+\.\s|\*\s|\-\s)(.+?)(?=$|\n)',  # Numbered/bulleted points
                r'(?:Key|Important|Main)(?:\s+point|\s+takeaway|\s+idea|\s+concept|\s+fact)(?:s)?(?:\s+include|\s+is|\s+are)?(?:\s*:)?\s+(.+?)(?:$|\n|\.)',  # "Key point is..." patterns
                r'(?:First|Second|Third|Fourth|Fifth|Finally|Lastly)(?:\s*,)?\s+(.+?)(?:$|\n|\.)'  # Ordinal markers
            ]
            
            for pattern in important_patterns:
                matches = re.finditer(pattern, summary, re.IGNORECASE | re.MULTILINE)
                for match in matches:
                    if match.group(1).strip():
                        point = match.group(1).strip()
                        # Ensure the point ends with proper punctuation
                        if not point.endswith(('.', '!', '?')):
                            point += '.'
                        key_points.append(point)
            
            # If we haven't found at least 2 points with patterns, use regular sentence tokenization
            if len(key_points) < 2:
                points = sent_tokenize(summary)
                # Filter for longer, more informative sentences
                for point in points:
                    point = point.strip()
                    word_count = len(point.split())
                    # Only include points that are reasonably long but not too long
                    if 5 <= word_count <= 25 and len(point) >= 50:
                        key_points.append(point)
        
        # Deduplicate points with lower similarity threshold
        unique_points = []
        for point in key_points:
            if not any(similar(point, existing, threshold=0.7) for existing in unique_points):
                unique_points.append(point)
        
        logger.info(f"Generated {len(unique_points)} unique key points")
        
        # If we still don't have enough key points, extract sentences from the transcript
        if len(unique_points) < 3:
            logger.info("Not enough key points extracted, falling back to direct transcript extraction")
            # Extract some sentences directly from transcript
            important_sentences = extract_important_sentences(transcript)
            for sentence in important_sentences:
                if not any(similar(sentence, existing, threshold=0.7) for existing in unique_points):
                    unique_points.append(sentence)
        
        # If we still have no key points, add a default message
        if len(unique_points) == 0:
            unique_points = ["No key points could be automatically extracted from this transcript."]
        
        notes = {
            "summary": " ".join(all_summaries),
            "key_points": unique_points[:10],  # Limit to top 10 points
            "original_transcript": transcript
        }
        logger.info(f"Notes generation complete: {len(notes['key_points'])} key points")
        return notes
        
    except Exception as e:
        logger.error(f"Error in note generation: {str(e)}", exc_info=True)
        # Fallback
        return {
            "summary": "Error generating summary: " + str(e)[:100] + "... Please try a different model.",
            "key_points": ["Could not generate key points due to an error."],
            "original_transcript": transcript
        }

def generate_multilingual_notes(transcript, language, model_data):
    """Generate notes for non-English languages using specialized models"""
    logger.info(f"Using specialized model for {language} summarization")
    
    try:
        model = model_data['model']
        tokenizer = model_data['tokenizer']
        model_type = model_data.get('model_type', 'mbart')
        
        # Process in chunks due to token limits
        chunks = []
        current_chunk = ""
        sentences = sent_tokenize(transcript)
        
        for sentence in sentences:
            if len(current_chunk) + len(sentence) < 900:
                current_chunk += " " + sentence
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = sentence
        
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        valid_chunks = [chunk for chunk in chunks if len(chunk) >= 50]
        
        if not valid_chunks:
            return {
                "summary": transcript[:1000] + "...",
                "key_points": ["Transcript too short for key point extraction."],
                "original_transcript": transcript,
                "language": language
            }
        
        all_summaries = []
        
        # Process differently based on model type
        for chunk in valid_chunks[:3]:  # Process just a few chunks to avoid overwhelming the model
            if model_type == 'mt5':
                # MT5 model processing
                prefix = "summarize: "
                inputs = tokenizer(prefix + chunk, return_tensors="pt", max_length=1024, truncation=True)
                
                summary_ids = model.generate(
                    inputs["input_ids"], 
                    max_length=150, 
                    min_length=40,
                    length_penalty=2.0,
                    num_beams=4,
                    early_stopping=True
                )
                
                summary = tokenizer.decode(summary_ids[0], skip_special_tokens=True)
            else:
                # mBART model processing
                inputs = tokenizer(chunk, return_tensors="pt", max_length=1024, truncation=True)
                
                summary_ids = model.generate(
                    inputs["input_ids"], 
                    max_length=150, 
                    min_length=30,
                    num_beams=4,
                    length_penalty=2.0,
                    early_stopping=True
                )
                
                summary = tokenizer.decode(summary_ids[0], skip_special_tokens=True)
            
            all_summaries.append(summary)
        
        # Extract key points using language-specific approach
        key_points = extract_important_sentences(transcript, language)
        
        # For Indic languages, we might need additional post-processing
        if language in ['hi', 'bn']:
            # Try to split summaries into more coherent points
            additional_points = []
            for summary in all_summaries:
                # For Hindi and Bengali, split on Devanagari purna viram and other markers
                splits = re.split(r'[।|॥]|\.\s+', summary)
                for split in splits:
                    if len(split.strip()) > 50:
                        additional_points.append(split.strip())
            
            # Add the additional points to key_points if they're not too similar
            for point in additional_points:
                if not any(similar(point, existing, threshold=0.7) for existing in key_points):
                    key_points.append(point)
        
        notes = {
            "summary": " ".join(all_summaries),
            "key_points": key_points[:10],
            "original_transcript": transcript,
            "language": language
        }
        
        return notes
        
    except Exception as e:
        logger.error(f"Error in multilingual note generation: {str(e)}", exc_info=True)
        return {
            "summary": transcript[:1000] + "...",
            "key_points": ["Could not generate key points due to an error."],
            "original_transcript": transcript,
            "language": language
        }
