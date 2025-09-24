#!/usr/bin/env python3
"""
Debug script for testing LLM chunking
"""

import logging
import sys
import os
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Configure logging
logging.basicConfig(level=logging.DEBUG, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

from ingestion.llm_chunking import LLMChunker, llm_chunk_text
from ingestion.pdf_extractor import extract_sections_from_text

def main():
    # Read the test document
    with open('data/test_document_v2.txt', 'r') as f:
        text = f.read()
    
    print(f"Input text length: {len(text)} characters")
    
    # Extract sections
    print("\n=== SECTION EXTRACTION ===")
    sections = extract_sections_from_text(text)
    print(f"Found {len(sections)} sections:")
    for i, section in enumerate(sections):
        print(f"\n--- Section {i+1} ---")
        print(f"Heading: {section['heading']}")
        print(f"Text length: {len(section['text'])} characters")
        print(f"Text preview: {section['text'][:100]}...")
    
    # Test LLM chunking
    print("\n=== LLM CHUNKING ===")
    chunker = LLMChunker()
    chunks = chunker.chunk_text(text)
    
    print(f"Got {len(chunks)} chunks:")
    for i, chunk in enumerate(chunks):
        print(f"\n--- Chunk {i+1} ---")
        print(f"Type: {chunk.chunk_type}")
        print(f"Section title: {chunk.section_title}")
        print(f"Text length: {len(chunk.text)} characters")
        print(f"Text: {chunk.text[:200]}...")
        print(f"Entities: {chunk.entities}")
        if hasattr(chunk, 'relationships') and chunk.relationships:
            print(f"Relationships: {chunk.relationships}")
    
    # Test direct llm_chunk_text function
    print("\n=== DIRECT LLM_CHUNK_TEXT ===")
    result = llm_chunk_text(text)
    
    print(f"Got {len(result)} chunks:")
    for i, chunk in enumerate(result):
        print(f"\n--- Chunk {i+1} ---")
        print(f"Type: {chunk.get('chunk_type')}")
        print(f"Text length: {len(chunk.get('body', ''))} characters")
        print(f"Text: {chunk.get('body', '')[:200]}...")
        print(f"Entities: {chunk.get('entities', [])}")
        print(f"Relationships: {chunk.get('relationships', [])}")

if __name__ == "__main__":
    main()
