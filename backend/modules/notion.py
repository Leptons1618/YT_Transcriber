import os
from notion_client import Client
from config import logger

def sanitize_text(text):
    """Sanitize text to handle Unicode characters safely
    
    Args:
        text: Text that might contain Unicode characters
        
    Returns:
        str: Sanitized text
    """
    if not text:
        return text
        
    try:
        # Try to encode and then decode to catch any encoding issues
        return text.encode('utf-8', errors='ignore').decode('utf-8')
    except Exception as e:
        logger.warning(f"Error sanitizing text: {str(e)}")
        # Fall back to ASCII if all else fails
        return text.encode('ascii', errors='ignore').decode('ascii')

def sanitize_error_message(error_message):
    """Sanitize error messages for safe logging
    
    Args:
        error_message: Error message that might contain Unicode characters
        
    Returns:
        str: Sanitized error message
    """
    try:
        # Convert the error message to a simple ASCII string
        return str(error_message).encode('ascii', errors='replace').decode('ascii')
    except Exception:
        # Ultimate fallback
        return "Error message contained unprocessable characters"

def chunk_text(text, max_length=2000):
    """Split text into chunks that respect Notion's character limits
    
    Args:
        text: The text to split
        max_length: Maximum length per chunk (Notion limit is 2000)
        
    Returns:
        list: List of text chunks
    """
    if not text:
        return []
    
    # If text is already within limits, return it as a single chunk
    if len(text) <= max_length:
        return [text]
    
    chunks = []
    # Try to split at sentence boundaries first
    sentences = text.split('. ')
    current_chunk = ""
    
    for sentence in sentences:
        # Add period back if it was removed during splitting
        sentence_with_period = sentence + ('' if sentence.endswith('.') else '.')
        
        # Check if adding this sentence would exceed the limit
        if len(current_chunk) + len(sentence_with_period) + 1 > max_length:
            # If current chunk is not empty, add it to chunks
            if current_chunk:
                chunks.append(current_chunk.strip())
            
            # If the sentence itself is too long, split it by characters
            if len(sentence_with_period) > max_length:
                # Split the long sentence into smaller chunks
                start = 0
                while start < len(sentence_with_period):
                    # Find a good breaking point (space) near the max length
                    end = min(start + max_length, len(sentence_with_period))
                    if end < len(sentence_with_period):
                        # Try to find a space to break at
                        while end > start and sentence_with_period[end] != ' ':
                            end -= 1
                        # If no space found, just break at max_length
                        if end == start:
                            end = min(start + max_length, len(sentence_with_period))
                    
                    chunks.append(sentence_with_period[start:end].strip())
                    start = end
            else:
                current_chunk = sentence_with_period
        else:
            # Add space if current_chunk is not empty
            if current_chunk:
                current_chunk += " "
            current_chunk += sentence_with_period
    
    # Add the last chunk if not empty
    if current_chunk:
        chunks.append(current_chunk.strip())
    
    return chunks

def create_text_blocks(text, block_type="paragraph"):
    """Create Notion blocks from text, respecting character limits
    
    Args:
        text: Text content to convert to Notion blocks
        block_type: Type of Notion block ('paragraph' or 'bulleted_list_item')
        
    Returns:
        list: List of Notion block objects
    """
    if not text:
        return []
    
    # Split text into chunks that respect Notion's character limits
    chunks = chunk_text(sanitize_text(text))
    
    # Create blocks for each chunk
    blocks = []
    for chunk in chunks:
        blocks.append({
            "object": "block",
            "type": block_type,
            block_type: {
                "rich_text": [{"type": "text", "text": {"content": chunk}}]
            }
        })
    
    return blocks

def export_to_notion(content, notion_token=None, parent_page_id=None):
    """Export transcript and notes to Notion by creating a new page
    
    Args:
        content: Dictionary containing transcript, summary, and other metadata
        notion_token: Notion API token
        parent_page_id: ID of the parent Notion page
        
    Returns:
        dict: Result of operation with success status and page URL
    """
    try:
        # Get API key either from parameter or environment variable
        notion_token = notion_token or os.getenv('NOTION_API_KEY')
        
        # Get parent page ID either from parameter or environment variable
        parent_page_id = parent_page_id or os.getenv('NOTION_PARENT_PAGE_ID')
        
        if not notion_token or not parent_page_id or not content:
            return {
                'success': False,
                'error': 'Missing required parameters. Please provide Notion token and page ID or set them in environment variables.'
            }
        
        # Initialize Notion client
        notion = Client(auth=notion_token)
        
        try:
            # Create a new page with the transcript title
            page_title = sanitize_text(content.get('title', 'YouTube Video Transcript'))
            
            # Create a new page in the parent database/page
            new_page = notion.pages.create(
                parent={"page_id": parent_page_id},
                properties={
                    "title": {
                        "title": [
                            {
                                "text": {
                                    "content": page_title
                                }
                            }
                        ]
                    }
                }
            )
            
            # Get the ID of the newly created page
            new_page_id = new_page["id"]
            
            # Format content for Notion blocks
            blocks = []
            
            # Add metadata (URL, channel)
            blocks.append({
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [
                        {"type": "text", "text": {"content": "Channel: "}},
                        {"type": "text", "text": {"content": sanitize_text(content['channel'])}, "annotations": {"bold": True}}
                    ]
                }
            })
            
            if content.get('url'):
                blocks.append({
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [
                            {"type": "text", "text": {"content": "URL: "}},
                            {"type": "text", "text": {"content": sanitize_text(content['url'])}, "annotations": {"underline": True}, "href": sanitize_text(content['url'])}
                        ]
                    }
                })
            
            # Add divider
            blocks.append({"object": "block", "type": "divider", "divider": {}})
            
            # Add summary section if available
            if content.get('summary'):
                blocks.append({
                    "object": "block",
                    "type": "heading_2",
                    "heading_2": {
                        "rich_text": [{"type": "text", "text": {"content": "Summary"}}]
                    }
                })
                
                # Add summary chunks as separate paragraph blocks
                summary_blocks = create_text_blocks(content['summary'], "paragraph")
                blocks.extend(summary_blocks)
                
                # Add divider
                blocks.append({"object": "block", "type": "divider", "divider": {}})
            
            # Add key points if available
            if content.get('keyPoints') and len(content['keyPoints']) > 0:
                blocks.append({
                    "object": "block",
                    "type": "heading_2",
                    "heading_2": {
                        "rich_text": [{"type": "text", "text": {"content": "Key Points"}}]
                    }
                })
                
                # Add bullet list for key points
                for point in content['keyPoints']:
                    # Check if point needs to be split (unlikely, but possible)
                    point_blocks = create_text_blocks(point, "bulleted_list_item")
                    blocks.extend(point_blocks)
                
                # Add divider
                blocks.append({"object": "block", "type": "divider", "divider": {}})
            
            # Add transcript if available
            if content.get('transcript') and len(content['transcript']) > 0:
                blocks.append({
                    "object": "block",
                    "type": "heading_2",
                    "heading_2": {
                        "rich_text": [{"type": "text", "text": {"content": "Transcript"}}]
                    }
                })
                
                # Add segments with timestamps
                for segment in content['transcript']:
                    # Format segment with timestamp
                    timestamp_text = f"[{segment['time']}] "
                    segment_text = segment['text']
                    
                    # Check if combined text exceeds the limit
                    if len(timestamp_text) + len(segment_text) > 2000:
                        # Split only the content part, keep timestamp intact
                        content_chunks = chunk_text(segment_text, 2000 - len(timestamp_text))
                        
                        for i, chunk in enumerate(content_chunks):
                            # Only add timestamp to the first chunk
                            if i == 0:
                                blocks.append({
                                    "object": "block",
                                    "type": "paragraph",
                                    "paragraph": {
                                        "rich_text": [
                                            {"type": "text", "text": {"content": timestamp_text}, "annotations": {"bold": True}},
                                            {"type": "text", "text": {"content": sanitize_text(chunk)}}
                                        ]
                                    }
                                })
                            else:
                                # Continuation chunks are indented
                                blocks.append({
                                    "object": "block",
                                    "type": "paragraph",
                                    "paragraph": {
                                        "rich_text": [
                                            {"type": "text", "text": {"content": "    " + sanitize_text(chunk)}}
                                        ]
                                    }
                                })
                    else:
                        # Standard case: timestamp + text fits in one block
                        blocks.append({
                            "object": "block",
                            "type": "paragraph",
                            "paragraph": {
                                "rich_text": [
                                    {"type": "text", "text": {"content": timestamp_text}, "annotations": {"bold": True}},
                                    {"type": "text", "text": {"content": sanitize_text(segment_text)}}
                                ]
                            }
                        })
            
            # Split blocks into chunks of 100 (Notion API limit)
            NOTION_BLOCK_LIMIT = 100
            block_chunks = [blocks[i:i + NOTION_BLOCK_LIMIT] for i in range(0, len(blocks), NOTION_BLOCK_LIMIT)]
            
            # Append blocks in batches
            for chunk in block_chunks:
                notion.blocks.children.append(
                    block_id=new_page_id,
                    children=chunk
                )
            
            # Get the URL of the newly created page to return to the user
            page_url = f"https://notion.so/{new_page_id.replace('-', '')}"
            
            logger.info(f"Successfully exported content to Notion page: {page_url}")
            return {
                'success': True, 
                'message': 'Successfully exported to Notion',
                'pageId': new_page_id,
                'pageUrl': page_url
            }
        
        except Exception as e:
            # Sanitize the error message to prevent Unicode encoding issues in logs
            safe_error_msg = sanitize_error_message(str(e))
            logger.error(f"Notion API error: {safe_error_msg}")
            return {'success': False, 'error': f'Notion API error: {safe_error_msg}'}
    
    except Exception as e:
        # Sanitize the error message to prevent Unicode encoding issues in logs
        safe_error_msg = sanitize_error_message(str(e))
        logger.error(f"Export to Notion error: {safe_error_msg}")
        return {'success': False, 'error': f'Server error: {safe_error_msg}'}
