"""
Background PDF Ingestion with Frontend Tracking

This module provides background ingestion that can be tracked from the frontend
via API endpoints and real-time updates.
"""

import asyncio
import json
import logging
import threading
import time
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Callable
from pathlib import Path
from dataclasses import dataclass, asdict

from ingestion.pipeline import ingest_document
from ingestion.pdf_extractor import extract_text_from_pdf, extract_sections_from_text, detect_document_type, detect_jurisdiction

logger = logging.getLogger(__name__)


@dataclass
class IngestionStatus:
    """Status of an ingestion job."""
    job_id: str
    status: str  # "pending", "running", "completed", "failed"
    progress: float  # 0.0 to 1.0
    current_file: str = ""
    current_step: str = ""
    files_processed: int = 0
    total_files: int = 0
    documents_created: int = 0
    chunks_created: int = 0
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    error_message: Optional[str] = None


class BackgroundIngestionManager:
    """Manages background ingestion jobs with progress tracking."""
    
    def __init__(self):
        self.jobs: Dict[str, IngestionStatus] = {}
        self.job_threads: Dict[str, threading.Thread] = {}
        self._lock = threading.Lock()
    
    def start_ingestion(
        self, 
        directory_path: str,
        doc_type: str = None,
        jurisdiction: str = None,
        lang: str = "ko"
    ) -> str:
        """Start a background ingestion job."""
        job_id = str(uuid.uuid4())
        
        with self._lock:
            self.jobs[job_id] = IngestionStatus(
                job_id=job_id,
                status="pending",
                progress=0.0,
                total_files=len(list(Path(directory_path).glob("*.pdf"))),
                started_at=datetime.now().isoformat()
            )
        
        # Start background thread
        thread = threading.Thread(
            target=self._run_ingestion,
            args=(job_id, directory_path, doc_type, jurisdiction, lang),
            daemon=True
        )
        thread.start()
        
        with self._lock:
            self.job_threads[job_id] = thread
            self.jobs[job_id].status = "running"
        
        logger.info(f"Started background ingestion job {job_id}")
        return job_id
    
    def get_job_status(self, job_id: str) -> Optional[IngestionStatus]:
        """Get the status of an ingestion job."""
        with self._lock:
            return self.jobs.get(job_id)
    
    def get_all_jobs(self) -> List[IngestionStatus]:
        """Get all ingestion jobs."""
        with self._lock:
            return list(self.jobs.values())
    
    def _run_ingestion(
        self, 
        job_id: str, 
        directory_path: str,
        doc_type: str = None,
        jurisdiction: str = None,
        lang: str = "ko"
    ):
        """Run the actual ingestion in background."""
        logger.info(f"Background ingestion thread started for job {job_id}")
        try:
            directory = Path(directory_path)
            if not directory.exists():
                self._update_job_status(job_id, status="failed", error_message=f"Directory not found: {directory_path}")
                logger.error(f"Job {job_id} failed: Directory not found {directory_path}")
                return
            
            pdf_files = list(directory.glob("*.pdf"))
            if not pdf_files:
                self._update_job_status(job_id, status="failed", error_message=f"No PDF files found in {directory_path}")
                logger.error(f"Job {job_id} failed: No PDF files in {directory_path}")
                return
            
            total_files = len(pdf_files)
            files_processed = 0
            total_documents = 0
            total_chunks = 0
            
            logger.info(f"Job {job_id}: Found {total_files} PDF files.")
            
            for pdf_file_idx, pdf_file in enumerate(pdf_files):
                file_progress_base = pdf_file_idx / total_files
                try:
                    filename = pdf_file.name
                    
                    # Update progress
                    self._update_job_status(
                        job_id,
                        current_file=filename,
                        current_step="Extracting text...",
                        files_processed=files_processed,
                        progress=file_progress_base
                    )
                    logger.info(f"Job {job_id} - File {filename}: Extracting text.")
                    
                    # Extract text from PDF
                    pdf_data = extract_text_from_pdf(str(pdf_file))
                    
                    self._update_job_status(
                        job_id,
                        current_step=f"Extracted {pdf_data['page_count']} pages, analyzing structure...",
                        progress=file_progress_base + (0.1 / total_files)
                    )
                    logger.info(f"Job {job_id} - File {filename}: Extracted {pdf_data['page_count']} pages, analyzing structure.")
                    
                    # Auto-detect document type and jurisdiction
                    current_doc_type = doc_type if doc_type else detect_document_type(pdf_data["file_name"])
                    current_jurisdiction = jurisdiction if jurisdiction else detect_jurisdiction(pdf_data["file_name"])
                    
                    # Extract sections
                    sections = extract_sections_from_text(pdf_data["text"])
                    
                    self._update_job_status(
                        job_id,
                        current_step=f"Found {len(sections)} sections, processing with LLM...",
                        progress=file_progress_base + (0.2 / total_files)
                    )
                    logger.info(f"Job {job_id} - File {filename}: Found {len(sections)} sections, processing with LLM.")
                    
                    # Process each section
                    for i, section in enumerate(sections):
                        section_progress_fraction = (i / len(sections)) if len(sections) > 0 else 0
                        self._update_job_status(
                            job_id,
                            current_step=f"LLM processing section {i+1}/{len(sections)}: {section['heading'][:30]}...",
                            progress=file_progress_base + (0.2 + (0.7 * section_progress_fraction)) / total_files
                        )
                        logger.debug(f"Job {job_id} - File {filename} - Section {i+1}: LLM processing {section['heading'][:30]}...")
                        
                        doc_id = f"{pdf_data['file_name']}_{section['order']}"
                        
                        doc_data = {
                            "doc_id": doc_id,
                            "title": f"{pdf_data['file_name']} - {section['heading']}",
                            "body": section["text"],
                            "doc_type": current_doc_type,
                            "jurisdiction": current_jurisdiction,
                            "lang": lang,
                            "section": section["heading"],
                            "valid_from": datetime.now().isoformat(),
                        }
                        
                        result = ingest_document(doc_data) # This uses the LLM
                        if "error" not in result:
                            total_documents += 1
                            total_chunks += len(result.get("chunks", []))
                        else:
                            logger.warning(f"Job {job_id} - File {filename} - Section {i+1}: Failed to ingest: {result['error']}")
                    
                    files_processed += 1
                    
                    self._update_job_status(
                        job_id,
                        current_file=filename,
                        current_step=f"Completed processing {filename}",
                        files_processed=files_processed,
                        documents_created=total_documents,
                        chunks_created=total_chunks,
                        progress=files_processed / total_files
                    )
                    logger.info(f"Job {job_id} - File {filename}: Completed. Total docs: {total_documents}, Chunks: {total_chunks}")
                    
                except Exception as e:
                    logger.error(f"Job {job_id} - Failed to process {pdf_file.name}: {e}", exc_info=True)
                    self._update_job_status(
                        job_id,
                        current_file=pdf_file.name,
                        current_step=f"Failed to process {pdf_file.name}: {str(e)}",
                        progress=files_processed / total_files
                    )
                    files_processed += 1
            
            # Mark as completed
            self._update_job_status(
                job_id,
                status="completed",
                progress=1.0,
                current_step="Ingestion completed successfully!",
                completed_at=datetime.now().isoformat()
            )
            
            logger.info(f"Background ingestion job {job_id} completed successfully")
            
        except Exception as e:
            logger.error(f"Background ingestion job {job_id} failed: {e}", exc_info=True)
            self._update_job_status(
                job_id,
                status="failed",
                error_message=str(e),
                completed_at=datetime.now().isoformat()
            )
    
    def _update_job_status(self, job_id: str, **kwargs):
        """Update job status in a thread-safe manner."""
        with self._lock:
            if job_id in self.jobs:
                job = self.jobs[job_id]
                for key, value in kwargs.items():
                    if hasattr(job, key):
                        setattr(job, key, value)
                logger.debug(f"Job {job_id} status updated: {job}")


# Global instance
ingestion_manager = BackgroundIngestionManager()


def start_background_ingestion(
    directory_path: str,
    doc_type: str = None,
    jurisdiction: str = None,
    lang: str = "ko"
) -> str:
    """Start a background ingestion job."""
    return ingestion_manager.start_ingestion(directory_path, doc_type, jurisdiction, lang)


def get_ingestion_status(job_id: str) -> Optional[Dict]:
    """Get ingestion job status as dictionary."""
    status = ingestion_manager.get_job_status(job_id)
    return asdict(status) if status else None


def get_all_ingestion_jobs() -> List[Dict]:
    """Get all ingestion jobs as dictionaries."""
    jobs = ingestion_manager.get_all_jobs()
    return [asdict(job) for job in jobs]


# Example usage
if __name__ == "__main__":
    # Start background ingestion
    job_id = start_background_ingestion("data", doc_type="regulation", jurisdiction="KR", lang="ko")
    print(f"Started ingestion job: {job_id}")
    
    # Monitor progress
    while True:
        status = get_ingestion_status(job_id)
        if status:
            print(f"Progress: {status['progress']:.1%} - {status['current_step']}")
            if status['status'] in ['completed', 'failed']:
                break
        time.sleep(2)
    
    print("Ingestion completed!")
