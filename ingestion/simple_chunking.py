"""
Simple and reliable text chunking module

This module provides straightforward, deterministic text chunking that preserves
sentence and paragraph boundaries.
"""

import re
import logging
from typing import List, Dict

logger = logging.getLogger(__name__)

def split_into_sentences(text: str) -> List[str]:
    """Split text into sentences, preserving paragraph structure."""
    # First split by paragraphs
    paragraphs = re.split(r'\n\s*\n', text)
    
    sentences = []
    for paragraph in paragraphs:
        # Skip empty paragraphs
        if not paragraph.strip():
            continue
            
        # Split paragraph into sentences
        paragraph_sentences = re.split(r'(?<=[.!?])\s+', paragraph.strip())
        
        # Add each sentence, making sure it ends with proper punctuation
        for sentence in paragraph_sentences:
            if sentence.strip():
                # Ensure sentence ends with punctuation
                if not sentence.strip()[-1] in '.!?':
                    sentence = sentence.strip() + '.'
                sentences.append(sentence.strip())
                
        # Add an empty string to mark paragraph boundary
        sentences.append('')
    
    # Remove any trailing empty strings
    while sentences and not sentences[-1]:
        sentences.pop()
        
    return sentences

def chunk_by_section(text: str, max_chars: int = 1000) -> List[Dict]:
    """
    Chunk text by sections, then by paragraphs and sentences.
    
    Args:
        text: The text to chunk
        max_chars: Maximum characters per chunk
        
    Returns:
        List of dictionaries with 'body' and 'section_title' keys
    """
    # First split by section headers
    section_pattern = r'(^|\n)(#+\s+.+)(\n|$)'
    sections = re.split(section_pattern, text)
    
    chunks = []
    current_section = "Document"
    current_chunk = ""
    
    for i, section in enumerate(sections):
        if not section.strip():
            continue
            
        # Check if this is a section header
        if re.match(r'^#+\s+.+$', section.strip()):
            # If we have content in the current chunk, save it
            if current_chunk.strip():
                chunks.append({
                    "body": current_chunk.strip(),
                    "section_title": current_section
                })
            
            # Update the current section title
            current_section = section.strip()
            current_chunk = ""
            continue
        
        # Process the section content
        sentences = split_into_sentences(section)
        
        # Build chunks from sentences, respecting max_chars
        for sentence in sentences:
            # Empty string marks paragraph boundary
            if not sentence:
                current_chunk += "\n\n"
                continue
                
            # If adding this sentence would exceed max_chars, start a new chunk
            if len(current_chunk) + len(sentence) + 1 > max_chars and current_chunk.strip():
                chunks.append({
                    "body": current_chunk.strip(),
                    "section_title": current_section
                })
                current_chunk = sentence + " "
            else:
                current_chunk += sentence + " "
    
    # Add the final chunk if it has content
    if current_chunk.strip():
        chunks.append({
            "body": current_chunk.strip(),
            "section_title": current_section
        })
    
    return chunks

def simple_chunk_text(text: str, max_chars: int = 1000) -> List[Dict]:
    """
    Simple text chunking that preserves sentence and paragraph boundaries.
    
    Args:
        text: The text to chunk
        max_chars: Maximum characters per chunk
        
    Returns:
        List of dictionaries with 'body' and 'section_title' keys
    """
    chunks = chunk_by_section(text, max_chars)
    
    # Log the chunks for debugging
    logger.debug(f"Created {len(chunks)} chunks using simple chunking")
    for i, chunk in enumerate(chunks):
        logger.debug(f"Chunk {i}: '{chunk['body'][:50]}...' ({len(chunk['body'])} chars)")
        
    return chunks
