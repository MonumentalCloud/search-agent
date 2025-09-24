"""
Hybrid Chunking Module

This module provides a hybrid approach to document chunking that combines
rule-based chunking with LLM-based entity and date extraction.
"""

import re
import logging
from typing import List, Dict, Any, Optional

from ingestion.simple_chunking import simple_chunk_text
from ingestion.llm_chunking import LLMEntityExtractor
from ingestion.date_extractor import extract_dates_from_text

logger = logging.getLogger(__name__)

# Initialize extractors
entity_extractor = LLMEntityExtractor()

def hybrid_chunk_text(text: str, max_chars: int = 800) -> List[Dict[str, Any]]:
    """
    Hybrid chunking approach that combines rule-based chunking with LLM-based entity extraction.
    
    Args:
        text: Text to chunk
        max_chars: Maximum characters per chunk
        
    Returns:
        List of chunk objects with body, entities, dates, and other metadata
    """
    # Start with simple rule-based chunking
    simple_chunks = simple_chunk_text(text, max_chars=max_chars)
    
    # Enhanced chunks with entities and dates
    enhanced_chunks = []
    
    for chunk in simple_chunks:
        chunk_text = chunk["body"]
        
        # Skip empty chunks
        if not chunk_text or len(chunk_text.strip()) < 10:
            continue
        
        # Extract entities and relationships
        extraction_result = entity_extractor.extract_entities(chunk_text)
        entities = extraction_result.get("entities", [])
        relationships = extraction_result.get("relationships", [])
        
        # Extract dates
        dates = extract_dates_from_text(chunk_text)
        
        # Create enhanced chunk
        enhanced_chunk = {
            "body": chunk_text,
            "section_title": chunk.get("section_title", ""),
            "entities": entities,
            "relationships": relationships,
            "dates": dates,
            "token_count": len(chunk_text.split()),
            "char_count": len(chunk_text)
        }
        
        enhanced_chunks.append(enhanced_chunk)
    
    return enhanced_chunks