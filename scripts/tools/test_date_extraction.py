#!/usr/bin/env python3
"""
Test script for date extraction and storage in Chroma
"""

import os
import sys
import logging
from pathlib import Path

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

import json
import docx
from datetime import datetime
from ingestion.date_extractor import extract_dates_from_text
from adapters.chroma_adapter import ChromaClient
from ingestion.txt_ingestion import ingest_document

def extract_text_from_docx(file_path):
    """Extract text from a DOCX file."""
    try:
        doc = docx.Document(file_path)
        text = "\n\n".join([p.text for p in doc.paragraphs if p.text.strip()])
        return text
    except Exception as e:
        logger.error(f"Failed to extract text from {file_path}: {e}")
        return ""

def test_date_extraction_from_docx():
    """Test date extraction from DOCX files."""
    data_dir = Path(project_root) / "data"
    docx_files = list(data_dir.glob("*.docx"))
    
    if not docx_files:
        logger.error("No DOCX files found in data directory")
        return
    
    logger.info(f"Found {len(docx_files)} DOCX files")
    
    for file_path in docx_files:
        logger.info(f"\nProcessing {file_path.name}:")
        
        # Extract text
        text = extract_text_from_docx(file_path)
        if not text:
            logger.warning(f"Could not extract text from {file_path.name}")
            continue
        
        # Extract dates
        dates = extract_dates_from_text(text)
        
        logger.info(f"Extracted {len(dates)} dates:")
        for date_type, date_value in dates.items():
            logger.info(f"  {date_type}: {date_value}")
        
        # Test ingestion with dates
        doc_id = f"test_{file_path.stem}"
        doc_data = {
            "doc_id": doc_id,
            "title": f"Test - {file_path.name}",
            "body": text,
            "doc_type": "meeting",
            "jurisdiction": "KR",
            "lang": "ko",
            "section": "test",
        }
        
        result = ingest_document(doc_data)
        
        if "error" in result:
            logger.error(f"Failed to ingest document: {result['error']}")
        else:
            logger.info(f"Successfully ingested document with {len(result.get('chunks', []))} chunks")
            
            # Verify dates were stored correctly
            with ChromaClient() as client:
                if client._connected:
                    chunk_ids = result.get("chunks", [])
                    if chunk_ids:
                        # Get the first chunk
                        collection = client._client.get_collection(client.chunk_collection)
                        chunk_results = collection.get(ids=[chunk_ids[0]], include=["metadatas"])
                        
                        if chunk_results and chunk_results["metadatas"] and len(chunk_results["metadatas"]) > 0:
                            metadata = chunk_results["metadatas"][0]
                            
                            if "dates" in metadata and metadata["dates"]:
                                try:
                                    stored_dates = json.loads(metadata["dates"])
                                    logger.info("Stored dates in Chroma:")
                                    for date_type, date_value in stored_dates.items():
                                        logger.info(f"  {date_type}: {date_value}")
                                except json.JSONDecodeError:
                                    logger.warning("Failed to parse dates JSON")
                            else:
                                logger.warning("No dates found in chunk metadata")
                        else:
                            logger.warning("Could not retrieve chunk from Chroma")
                else:
                    logger.warning("Not connected to Chroma")

def test_date_search():
    """Test searching for documents by date."""
    logger.info("\nTesting date search:")
    
    with ChromaClient() as client:
        if not client._connected:
            logger.error("Not connected to Chroma")
            return
        
        # Get all chunks to analyze dates
        collection = client._client.get_collection(client.chunk_collection)
        results = collection.get(limit=100, include=["metadatas"])
        
        date_types = set()
        date_values = set()
        
        for metadata in results["metadatas"]:
            if "dates" in metadata and metadata["dates"]:
                try:
                    dates_dict = json.loads(metadata["dates"])
                    for date_type, date_value in dates_dict.items():
                        date_types.add(date_type)
                        date_values.add(date_value)
                except json.JSONDecodeError:
                    pass
        
        logger.info(f"Found date types: {date_types}")
        logger.info(f"Found date values: {date_values}")
        
        # Test searching for each date type
        for date_type in date_types:
            logger.info(f"\nSearching for chunks with date type '{date_type}':")
            
            # This is a simplified search - in a real implementation, you would use
            # a proper query with the dates field
            matching_chunks = []
            for metadata in results["metadatas"]:
                if "dates" in metadata and metadata["dates"]:
                    try:
                        dates_dict = json.loads(metadata["dates"])
                        if date_type in dates_dict:
                            matching_chunks.append({
                                "chunk_id": metadata.get("chunk_id", ""),
                                "doc_id": metadata.get("doc_id", ""),
                                "date_value": dates_dict[date_type]
                            })
                    except json.JSONDecodeError:
                        pass
            
            logger.info(f"Found {len(matching_chunks)} chunks with date type '{date_type}'")
            for i, chunk in enumerate(matching_chunks[:5]):  # Show first 5
                logger.info(f"  {i+1}. Chunk {chunk['chunk_id']} (Doc: {chunk['doc_id']}) - Value: {chunk['date_value']}")
            
            if len(matching_chunks) > 5:
                logger.info(f"  ... and {len(matching_chunks) - 5} more")

if __name__ == "__main__":
    logger.info("Starting date extraction and storage test")
    
    # Test date extraction from DOCX files
    test_date_extraction_from_docx()
    
    # Test date search
    test_date_search()
    
    logger.info("Date extraction and storage test completed")
