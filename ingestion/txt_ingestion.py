"""
Text File Ingestion Module

This module provides functionality to ingest plain text files into the Chroma database.
"""

import os
import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from adapters.chroma_adapter import ChromaClient
from ingestion.llm_chunking import llm_chunk_text
from ingestion.simple_chunking import simple_chunk_text
from ingestion.hybrid_chunking import hybrid_chunk_text
from ingestion.pdf_extractor import extract_sections_from_text

logger = logging.getLogger(__name__)


def read_text_file(file_path: str) -> Dict[str, any]:
    """Read a text file and return its content with metadata."""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Text file not found: {file_path}")
    
    file_name = Path(file_path).stem
    file_size = os.path.getsize(file_path)
    
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            text = file.read()
        
        return {
            "file_name": file_name,
            "file_path": file_path,
            "file_size": file_size,
            "page_count": 1,  # Text files don't have pages
            "text": text,
            "extraction_method": "text"
        }
    except Exception as e:
        logger.error(f"Failed to read text file {file_path}: {e}")
        raise


def ingest_text_file(file_path: str, doc_type: str = None, jurisdiction: str = None, lang: str = "en") -> Dict:
    """Ingest a text file into Chroma."""
    try:
        # Read text file
        text_data = read_text_file(file_path)
        
        # Extract sections
        sections = extract_sections_from_text(text_data["text"])
        
        logger.info(f"Extracted {len(sections)} sections from {text_data['file_name']}")
        
        # Ingest each section as a separate document
        ingested_docs = []
        total_chunks = 0
        
        for section in sections:
            doc_id = f"{text_data['file_name']}_{section['order']}"
            
            doc_data = {
                "doc_id": doc_id,
                "title": f"{text_data['file_name']} - {section['heading']}",
                "body": section["text"],
                "doc_type": doc_type or "document",
                "jurisdiction": jurisdiction or "global",
                "lang": lang,
                "section": section["heading"],
            }
            
            result = ingest_document(doc_data)
            if "error" not in result:
                ingested_docs.append(result)
                total_chunks += len(result.get("chunks", []))
            else:
                logger.error(f"Failed to ingest section {section['heading']}: {result['error']}")
        
        return {
            "file_name": text_data["file_name"],
            "file_path": file_path,
            "sections_processed": len(sections),
            "documents_ingested": len(ingested_docs),
            "total_chunks": total_chunks,
            "status": "success"
        }
        
    except Exception as e:
        logger.error(f"Failed to ingest text file {file_path}: {e}")
        return {"error": str(e)}


def ingest_document(doc: Dict, trace_id: str | None = None) -> Dict:
    """Ingest a document into Chroma with proper schema."""
    # Require minimal fields
    title = (doc.get("title") or "").strip()
    body = (doc.get("body") or "").strip()
    if not title or not body:
        raise ValueError("title and body are required for ingestion")

    doc_id = doc.get("doc_id") or str(uuid.uuid4())
    
    with ChromaClient() as client:
        # Check if Chroma is available
        if not client._connected:
            logger.warning("Chroma not connected, processing document without persistence")
            # Still process the document to return chunk IDs
            text_chunks = body.split('\n\n')  # Simple paragraph splitting
            chunk_ids = [f"{doc_id}:{i}" for i in range(len(text_chunks))]
            return {
                "doc_id": doc_id,
                "chunks": chunk_ids,
                "status": "processed_offline",
                "message": "Chroma not available, document processed but not persisted"
            }
        
        # Ensure schema exists
        if not client.ensure_schema():
            logger.error("Failed to ensure Chroma schema")
            return {"error": "Schema creation failed"}

        # Prepare document
        document = {
            "doc_id": doc_id,
            "title": title,
            "doc_type": doc.get("doc_type", "document"),
            "jurisdiction": doc.get("jurisdiction", "global"),
            "lang": doc.get("lang", "en"),
            "valid_from": doc.get("valid_from", datetime.now().isoformat()),
            "valid_to": doc.get("valid_to"),
            "entities": [],  # Will be populated from chunks
        }

        # Use LLM-based chunking system
        doc_metadata = {
            "doc_id": doc_id,
            "section": doc.get("section", "main"),
            "lang": doc.get("lang", "en")
        }
        
        # Use hybrid chunking that combines LLM intelligence with deterministic rules
        hybrid_chunks = hybrid_chunk_text(body, max_chars=800)
        chunk_objects = []
        
        # Log the chunks for debugging
        logger.debug(f"Hybrid chunking returned {len(hybrid_chunks)} chunks")
        for i, chunk in enumerate(hybrid_chunks):
            logger.debug(f"Chunk {i}: '{chunk['body'][:50]}...' ({len(chunk['body'])} chars)")
        
        for i, chunk_data in enumerate(hybrid_chunks):
            chunk_id = f"{doc_id}:{i}"
            chunk_text = chunk_data["body"]
            section_title = chunk_data.get("section_title", doc.get("section", "main"))
            
            # Skip empty or very short chunks
            if not chunk_text or len(chunk_text) < 10:
                logger.warning(f"Skipping empty or very short chunk: '{chunk_text}'")
                continue
            
            # Entities and relationships are already extracted by the hybrid chunker
            entities = chunk_data.get("entities", [])
            relationships = chunk_data.get("relationships", [])
            dates = chunk_data.get("dates", {})
            
            # Add all entities to document level
            document["entities"].extend(entities)
            
            chunk_obj = {
                "chunk_id": chunk_id,
                "doc_id": doc_id,
                "section": section_title,
                "body": chunk_text,
                "entities": entities,
                "relationships": relationships,
                "dates": dates,  # Store dates as a dictionary
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
                "token_count": chunk_data.get("token_count", len(chunk_text.split())),
                "char_count": chunk_data.get("char_count", len(chunk_text)),
            }
            chunk_objects.append(chunk_obj)

        # Upsert to Chroma
        try:
            # Upsert document
            success = client.batch_upsert_documents([document])
            if not success:
                raise Exception("Failed to upsert document")
            
            # Upsert chunks
            success = client.batch_upsert_chunks(chunk_objects)
            if not success:
                raise Exception("Failed to upsert chunks")
            
            logger.info(f"Successfully ingested document {doc_id} with {len(chunk_objects)} chunks")
            
            return {
                "doc_id": doc_id,
                "chunks": [chunk["chunk_id"] for chunk in chunk_objects],
                "status": "success"
            }
            
        except Exception as e:
            logger.error(f"Failed to ingest document {doc_id}: {e}")
            return {"error": str(e)}


def ingest_text_directory(directory_path: str, doc_type: str = None, jurisdiction: str = None, lang: str = "en", file_pattern: str = "*.txt") -> Dict:
    """Ingest all text files from a directory."""
    directory = Path(directory_path)
    if not directory.exists():
        return {"error": f"Directory not found: {directory_path}"}
    
    text_files = list(directory.glob(file_pattern))
    if not text_files:
        return {"error": f"No files matching '{file_pattern}' found in {directory_path}"}
    
    results = []
    total_docs = 0
    total_chunks = 0
    
    for text_file in text_files:
        logger.info(f"Processing text file: {text_file.name}")
        
        result = ingest_text_file(
            str(text_file), 
            doc_type=doc_type, 
            jurisdiction=jurisdiction, 
            lang=lang
        )
        
        results.append(result)
        
        if "error" not in result:
            total_docs += result.get("documents_ingested", 0)
            total_chunks += result.get("total_chunks", 0)
    
    return {
        "directory": directory_path,
        "files_processed": len(text_files),
        "documents_ingested": total_docs,
        "total_chunks": total_chunks,
        "results": results,
        "status": "success"
    }