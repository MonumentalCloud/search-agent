"""
Progress-Aware PDF Ingestion

This module provides ingestion with progress tracking and loading screens.
"""

import time
import logging
from typing import Dict, List, Optional, Callable
from pathlib import Path
from tqdm import tqdm
import sys

from ingestion.pipeline import ingest_pdf_file, ingest_document
from ingestion.pdf_extractor import extract_text_from_pdf, extract_sections_from_text

logger = logging.getLogger(__name__)


class ProgressTracker:
    """Track and display ingestion progress."""
    
    def __init__(self, total_files: int, show_progress: bool = True):
        self.total_files = total_files
        self.current_file = 0
        self.show_progress = show_progress
        self.pbar = None
        
        if show_progress:
            self.pbar = tqdm(
                total=total_files,
                desc="📄 Processing PDFs",
                unit="file",
                bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} files [{elapsed}<{remaining}]"
            )
    
    def update_file(self, filename: str, status: str = "processing"):
        """Update progress for current file."""
        self.current_file += 1
        
        if self.pbar:
            self.pbar.set_description(f"📄 {filename[:30]}...")
            self.pbar.set_postfix(status=status)
            self.pbar.update(1)
    
    def close(self):
        """Close progress bar."""
        if self.pbar:
            self.pbar.close()


def ingest_pdf_with_progress(
    file_path: str, 
    doc_type: str = None, 
    jurisdiction: str = None, 
    lang: str = "ko",
    progress_callback: Optional[Callable] = None
) -> Dict:
    """Ingest a PDF file with progress tracking."""
    try:
        filename = Path(file_path).name
        
        if progress_callback:
            progress_callback(f"📖 Extracting text from {filename}...")
        
        # Extract text from PDF
        pdf_data = extract_text_from_pdf(file_path)
        
        if progress_callback:
            progress_callback(f"📑 Extracted {pdf_data['page_count']} pages from {filename}")
        
        # Auto-detect document type and jurisdiction if not provided
        if not doc_type:
            from ingestion.pdf_extractor import detect_document_type
            doc_type = detect_document_type(pdf_data["file_name"])
        if not jurisdiction:
            from ingestion.pdf_extractor import detect_jurisdiction
            jurisdiction = detect_jurisdiction(pdf_data["file_name"])
        
        if progress_callback:
            progress_callback(f"🔍 Analyzing document structure...")
        
        # Extract sections
        sections = extract_sections_from_text(pdf_data["text"])
        
        if progress_callback:
            progress_callback(f"📋 Found {len(sections)} sections, processing with LLM...")
        
        # Ingest each section as a separate document
        ingested_docs = []
        total_chunks = 0
        
        for i, section in enumerate(sections):
            if progress_callback:
                progress_callback(f"🧠 LLM processing section {i+1}/{len(sections)}: {section['heading'][:30]}...")
            
            doc_id = f"{pdf_data['file_name']}_{section['order']}"
            
            doc_data = {
                "doc_id": doc_id,
                "title": f"{pdf_data['file_name']} - {section['heading']}",
                "body": section["text"],
                "doc_type": doc_type,
                "jurisdiction": jurisdiction,
                "lang": lang,
                "section": section["heading"],
                "valid_from": time.strftime("%Y-%m-%dT%H:%M:%S"),
            }
            
            result = ingest_document(doc_data)
            if "error" not in result:
                ingested_docs.append(result)
                total_chunks += len(result.get("chunks", []))
            else:
                logger.error(f"Failed to ingest section {section['heading']}: {result['error']}")
        
        if progress_callback:
            progress_callback(f"✅ Completed {filename}: {len(ingested_docs)} docs, {total_chunks} chunks")
        
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


def ingest_pdf_directory_with_progress(
    directory_path: str, 
    doc_type: str = None, 
    jurisdiction: str = None, 
    lang: str = "ko",
    show_progress: bool = True
) -> Dict:
    """Ingest all PDF files from a directory with progress tracking."""
    directory = Path(directory_path)
    if not directory.exists():
        return {"error": f"Directory not found: {directory_path}"}
    
    pdf_files = list(directory.glob("*.pdf"))
    if not pdf_files:
        return {"error": f"No PDF files found in {directory_path}"}
    
    print(f"🚀 Starting ingestion of {len(pdf_files)} PDF files...")
    print("📊 Progress will be shown below:")
    print()
    
    # Initialize progress tracker
    progress_tracker = ProgressTracker(len(pdf_files), show_progress)
    
    results = []
    total_docs = 0
    total_chunks = 0
    
    def progress_callback(message: str):
        """Progress callback for individual files."""
        if show_progress:
            # Update the progress bar description
            progress_tracker.pbar.set_description(f"📄 {message[:40]}...")
    
    try:
        for pdf_file in pdf_files:
            filename = pdf_file.name
            progress_tracker.update_file(filename, "starting")
            
            result = ingest_pdf_with_progress(
                str(pdf_file), 
                doc_type=doc_type, 
                jurisdiction=jurisdiction, 
                lang=lang,
                progress_callback=progress_callback
            )
            
            results.append(result)
            
            if "error" not in result:
                total_docs += result.get("documents_ingested", 0)
                total_chunks += result.get("total_chunks", 0)
                progress_tracker.update_file(filename, "✅ success")
            else:
                progress_tracker.update_file(filename, "❌ failed")
                print(f"❌ Failed to process {filename}: {result['error']}")
    
    finally:
        progress_tracker.close()
    
    print()
    print("🎉 Ingestion completed!")
    print(f"📊 Summary:")
    print(f"   Files processed: {len(pdf_files)}")
    print(f"   Total documents: {total_docs}")
    print(f"   Total chunks: {total_chunks}")
    
    return {
        "directory": directory_path,
        "files_processed": len(pdf_files),
        "total_documents": total_docs,
        "total_chunks": total_chunks,
        "results": results,
        "status": "success"
    }


def simple_progress_ingestion():
    """Simple ingestion with basic progress display."""
    print("🚀 Starting PDF ingestion with progress tracking...")
    print("=" * 60)
    
    result = ingest_pdf_directory_with_progress(
        "data",
        doc_type="regulation",
        jurisdiction="KR",
        lang="ko",
        show_progress=True
    )
    
    if "error" in result:
        print(f"❌ Ingestion failed: {result['error']}")
        return False
    else:
        print("✅ Ingestion completed successfully!")
        return True


if __name__ == "__main__":
    simple_progress_ingestion()
