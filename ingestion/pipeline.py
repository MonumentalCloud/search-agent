import time
import uuid
import logging
from datetime import datetime
from typing import Dict, List, Optional
from pathlib import Path

from adapters.weaviate_adapter import WeaviateClient
from ingestion.pdf_extractor import extract_text_from_pdf, detect_document_type, detect_jurisdiction, extract_sections_from_text
from ingestion.llm_chunking import llm_chunk_text
from ingestion.hybrid_chunking import hybrid_chunk_text
from ingestion.docx_ingestion import ingest_docx, ingest_docx_directory

logger = logging.getLogger(__name__)


def _simple_chunk(body: str, max_chars: int = 1200, overlap: int = 150) -> List[str]:
    """Simple text chunking with overlap - DEPRECATED, use improved_chunk_text instead."""
    chunks: List[str] = []
    start = 0
    while start < len(body):
        end = min(len(body), start + max_chars)
        chunks.append(body[start:end])
        if end == len(body):
            break
        start = max(0, end - overlap)
    return chunks


def _extract_entities(text: str) -> List[str]:
    """Simple entity extraction - placeholder for now."""
    # TODO: Implement proper NER or dictionary-based extraction
    # For now, return empty list
    return []


def _llm_chunk_document(body: str, doc_metadata: Dict) -> List[Dict[str, any]]:
    """Use LLM-based chunking for intelligent semantic understanding."""
    try:
        # Use LLM-based chunking for Korean legal documents
        chunks = llm_chunk_text(body, max_tokens=400)
        
        # Add metadata to each chunk
        for chunk in chunks:
            chunk.update(doc_metadata)
        
        return chunks
        
    except Exception as e:
        logger.warning(f"LLM chunking failed, falling back to simple chunking: {e}")
        # Fallback to simple chunking
        simple_chunks = _simple_chunk(body)
        return [{"body": chunk, "entities": [], "token_count": len(chunk) // 4} for chunk in simple_chunks]


def _generate_spacing_variants(text: str) -> List[str]:
    """Generate Korean spacing variants."""
    variants = [text]
    # Simple spacing variants for Korean
    if " " in text:
        variants.append(text.replace(" ", ""))
    return variants


def ingest_document(doc: Dict, trace_id: str | None = None) -> Dict:
    """Ingest a document into Weaviate with proper schema."""
    # Require minimal fields
    title = (doc.get("title") or "").strip()
    body = (doc.get("body") or "").strip()
    if not title or not body:
        raise ValueError("title and body are required for ingestion")

    doc_id = doc.get("doc_id") or str(uuid.uuid4())
    
    with WeaviateClient() as client:
        # Check if Weaviate is available
        if not client._connected:
            logger.warning("Weaviate not connected, processing document without persistence")
            # Still process the document to return chunk IDs
            text_chunks = _simple_chunk(body)
            chunk_ids = [f"{doc_id}:{i}" for i in range(len(text_chunks))]
            return {
                "doc_id": doc_id,
                "chunks": chunk_ids,
                "status": "processed_offline",
                "message": "Weaviate not available, document processed but not persisted"
            }
        
        # Ensure schema exists
        if not client.ensure_schema():
            logger.error("Failed to ensure Weaviate schema")
            return {"error": "Schema creation failed"}

        # Prepare document
        document = {
            "doc_id": doc_id,
            "title": title,
            "doc_type": doc.get("doc_type", "document"),
            "jurisdiction": doc.get("jurisdiction"),
            "lang": doc.get("lang", "en"),
            "valid_from": doc.get("valid_from", datetime.now().isoformat()),
            "valid_to": doc.get("valid_to"),
            "entities": _extract_entities(title + " " + body),
        }

        # Use LLM-based chunking system
        doc_metadata = {
            "doc_id": doc_id,
            "section": doc.get("section", "main"),
            "valid_from": document["valid_from"],
            "valid_to": document["valid_to"],
            "lang": doc.get("lang", "en")
        }
        
        llm_chunks = _llm_chunk_document(body, doc_metadata)
        chunk_objects = []
        
        for i, chunk_data in enumerate(llm_chunks):
            chunk_id = f"{doc_id}:{i}"
            chunk_text = chunk_data["body"]
            entities = chunk_data.get("entities", [])
            
            # Add spacing variants for Korean entities
            if doc.get("lang") == "ko":
                for entity in entities[:]:  # Copy list to avoid modification during iteration
                    variants = _generate_spacing_variants(entity)
                    entities.extend(variants)
            
            chunk_obj = {
                "chunk_id": chunk_id,
                "doc_id": doc_id,
                "section": doc.get("section", "main"),
                "body": chunk_text,
                "entities": entities,
                "valid_from": document["valid_from"],
                "valid_to": document["valid_to"],
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
                "token_count": chunk_data.get("token_count", 0),
                "char_count": chunk_data.get("char_count", len(chunk_text)),
            }
            chunk_objects.append(chunk_obj)

        # Upsert to Weaviate
        try:
            # Upsert document
            success = client.batch_upsert_documents([document])
            if not success:
                raise Exception("Failed to upsert document")
            
            # Upsert chunks (without vectors for now)
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


def ingest_pdf_file(file_path: str, doc_type: str = None, jurisdiction: str = None, lang: str = "ko") -> Dict:
    """Ingest a PDF file into Weaviate."""
    try:
        # Extract text from PDF
        pdf_data = extract_text_from_pdf(file_path)
        
        # Auto-detect document type and jurisdiction if not provided
        if not doc_type:
            doc_type = detect_document_type(pdf_data["file_name"])
        if not jurisdiction:
            jurisdiction = detect_jurisdiction(pdf_data["file_name"])
        
        # Extract sections
        sections = extract_sections_from_text(pdf_data["text"])
        
        logger.info(f"Extracted {len(sections)} sections from {pdf_data['file_name']}")
        
        # Ingest each section as a separate document
        ingested_docs = []
        total_chunks = 0
        
        for section in sections:
            doc_id = f"{pdf_data['file_name']}_{section['order']}"
            
            doc_data = {
                "doc_id": doc_id,
                "title": f"{pdf_data['file_name']} - {section['heading']}",
                "body": section["text"],
                "doc_type": doc_type,
                "jurisdiction": jurisdiction,
                "lang": lang,
                "section": section["heading"],
                "valid_from": datetime.now().isoformat(),
            }
            
            result = ingest_document(doc_data)
            if "error" not in result:
                ingested_docs.append(result)
                total_chunks += len(result.get("chunks", []))
            else:
                logger.error(f"Failed to ingest section {section['heading']}: {result['error']}")
        
        return {
            "file_name": pdf_data["file_name"],
            "file_path": file_path,
            "page_count": pdf_data["page_count"],
            "sections_processed": len(sections),
            "documents_ingested": len(ingested_docs),
            "total_chunks": total_chunks,
            "status": "success"
        }
        
    except Exception as e:
        logger.error(f"Failed to ingest PDF {file_path}: {e}")
        return {"error": str(e)}


def ingest_pdf_directory(directory_path: str, doc_type: str = None, jurisdiction: str = None, lang: str = "ko", file_pattern: str = "*.pdf") -> Dict:
    """Ingest all PDF files from a directory.
    
    Args:
        directory_path: Path to directory containing PDF files
        doc_type: Document type (optional)
        jurisdiction: Jurisdiction code (optional)
        lang: Language code (default: "ko")
        file_pattern: Glob pattern to match files (default: "*.pdf")
    """
    directory = Path(directory_path)
    if not directory.exists():
        return {"error": f"Directory not found: {directory_path}"}
    
    pdf_files = list(directory.glob(file_pattern))
    if not pdf_files:
        return {"error": f"No files matching '{file_pattern}' found in {directory_path}"}
    
    results = []
    total_docs = 0
    total_chunks = 0
    
    for pdf_file in pdf_files:
        logger.info(f"Processing PDF: {pdf_file.name}")
        
        result = ingest_pdf_file(
            str(pdf_file), 
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
        "files_processed": len(pdf_files),
        "total_documents": total_docs,
        "total_chunks": total_chunks,
        "results": results,
        "status": "success"
    }


def rebuild_facet_vectors(facet: str = None) -> Dict:
    """Rebuild facet-value vectors from corpus."""
    with WeaviateClient() as client:
        if not client._connected:
            return {"error": "Not connected to Weaviate"}
        
        try:
            # Get all unique values for the facet
            if facet:
                facets_to_process = [facet]
            else:
                facets_to_process = ["doc_type", "section", "jurisdiction", "lang"]
            
            total_updated = 0
            
            for facet_name in facets_to_process:
                # Get unique values for this facet
                values = client.aggregate_group_by(facet_name)
                
                for value, count in values.items():
                    if count > 0:  # Only process values that exist
                        # TODO: Build vector from value + aliases + sample sentences
                        # For now, create a placeholder vector
                        vector = [0.1] * 384  # Placeholder vector
                        aliases = _generate_spacing_variants(value) if facet_name in ["section", "doc_type"] else []
                        
                        success = client.upsert_facet_value_vector(facet_name, value, vector, aliases)
                        if success:
                            total_updated += 1
            
            return {"updated_count": total_updated, "status": "success"}
            
        except Exception as e:
            logger.error(f"Failed to rebuild facet vectors: {e}")
            return {"error": str(e)}