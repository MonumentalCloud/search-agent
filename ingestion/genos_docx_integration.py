"""
Integration script for using DocxProcessor with GenOS format.
"""
import asyncio
import os
import json
from pathlib import Path
from typing import List, Dict, Any
import logging

from ingestion.docx_processor import DocxProcessor

logger = logging.getLogger(__name__)

async def process_docx_file(file_path: str, request, **kwargs) -> List[Dict[str, Any]]:
    """Process a DOCX file and return vectors in GenOS format."""
    processor = DocxProcessor()
    vectors = await processor(request, file_path, **kwargs)
    return vectors

async def process_docx_directory(directory: str, request, file_pattern: str = "*.docx", **kwargs) -> Dict[str, List[Dict[str, Any]]]:
    """Process all DOCX files in a directory and return vectors."""
    results = {}
    directory_path = Path(directory)
    
    # Find all DOCX files in the directory
    docx_files = list(directory_path.glob(file_pattern))
    logger.info(f"Found {len(docx_files)} DOCX files in {directory}")
    
    # Process each file
    for file_path in docx_files:
        logger.info(f"Processing {file_path}")
        try:
            vectors = await process_docx_file(str(file_path), request, **kwargs)
            results[str(file_path)] = vectors
            logger.info(f"Successfully processed {file_path} with {len(vectors)} vectors")
        except Exception as e:
            logger.error(f"Error processing {file_path}: {e}")
            results[str(file_path)] = []
    
    return results

async def save_vectors_to_json(vectors: Dict[str, List[Dict[str, Any]]], output_dir: str):
    """Save vectors to JSON files for later use or inspection."""
    os.makedirs(output_dir, exist_ok=True)
    
    for file_path, file_vectors in vectors.items():
        if not file_vectors:
            continue
            
        file_name = Path(file_path).stem
        output_path = os.path.join(output_dir, f"{file_name}_vectors.json")
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(file_vectors, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Saved vectors for {file_path} to {output_path}")

# Example of how this would be used in GenOS:
"""
# In your GenOS code:
from ingestion.docx_processor import DocxProcessor

# In your DocumentProcessor.__call__ method:
async def __call__(self, request: Request, file_path: str, **kwargs):
    # For DOCX files
    if file_path.lower().endswith('.docx'):
        docx_processor = DocxProcessor()
        vectors = await docx_processor(request, file_path, **kwargs)
        return vectors
    
    # For other file types, use existing code
    # ...
"""
