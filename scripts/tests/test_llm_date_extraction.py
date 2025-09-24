#!/usr/bin/env python3
"""
Test LLM-based date extraction on a single DOCX file
"""

import os
import sys
import logging
from pathlib import Path
import json

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from configs.load import setup_root_logger, get_default_llm
from ingestion.docx_ingestion_llm import extract_text_from_docx, extract_dates_with_llm

# Set up logging
logger = logging.getLogger(__name__)

def main():
    # Set up logging
    setup_root_logger()
    
    # Specify the file to test
    file_path = os.path.join(project_root, "data", "회의록_01_마케팅.docx")
    
    print(f"Testing LLM date extraction on: {file_path}")
    
    # Extract text from DOCX
    text = extract_text_from_docx(file_path)
    print(f"Extracted {len(text)} characters of text")
    
    # Print first 500 characters
    print("\nText sample:")
    print(text[:500])
    
    # Extract dates using LLM
    print("\nExtracting dates with LLM...")
    date_info = extract_dates_with_llm(text)
    
    # Print results
    print("\nExtracted date information:")
    print(json.dumps(date_info, indent=2, ensure_ascii=False))
    
    print("\nDone!")

if __name__ == "__main__":
    main()
