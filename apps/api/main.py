import logging
from configs.load import get_default_embeddings
import os
import sys
import time
import uuid
from typing import Optional, List

from fastapi import FastAPI, HTTPException, UploadFile, File
from pydantic import BaseModel, Field
from ingestion.background_ingestion import start_background_ingestion, get_ingestion_status, get_all_ingestion_jobs

# Simple JSON logging setup focused on debuggability
logger = logging.getLogger("retrieval_agent.api")
logger.setLevel(logging.DEBUG)
_handler = logging.StreamHandler(sys.stdout)
_formatter = logging.Formatter(
    fmt="%(asctime)s %(levelname)s trace_id=%(trace_id)s module=%(module)s func=%(funcName)s line=%(lineno)d msg=%(message)s"
)
_handler.setFormatter(_formatter)
logger.addHandler(_handler)


class QueryRequest(BaseModel):
    query: str = Field(..., min_length=1)
    time: Optional[str] = None
    lang: Optional[str] = None


class Citation(BaseModel):
    doc_id: str
    chunk_id: str
    section: str
    valid_from: Optional[str] = None
    valid_to: Optional[str] = None


class AnswerResponse(BaseModel):
    text: str
    citations: List[Citation]
    trace_id: str


class IngestionRequest(BaseModel):
    directory_path: str = "data"
    doc_type: Optional[str] = "regulation"
    jurisdiction: Optional[str] = "KR"
    lang: str = "ko"


class IngestionResponse(BaseModel):
    job_id: str
    message: str


class IngestionStatusResponse(BaseModel):
    job_id: str
    status: str
    progress: float
    current_file: str
    current_step: str
    files_processed: int
    total_files: int
    documents_created: int
    chunks_created: int
    started_at: Optional[str]
    completed_at: Optional[str]
    error_message: Optional[str]


# In-memory debug traces for development
_DEBUG_TRACES: dict[str, dict] = {}


def _with_trace(record: logging.LogRecord, trace_id: str) -> None:
    # Inject trace_id into record; our formatter references it
    setattr(record, "trace_id", trace_id)


app = FastAPI(title="Weaviate-First Retrieval Agent", version="0.1.0")


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/agent/query", response_model=AnswerResponse)
async def agent_query(req: QueryRequest) -> AnswerResponse: # Make endpoint async
    trace_id = str(uuid.uuid4())
    start = time.time()

    # Attach trace id to logger via custom filter
    class _TraceFilter(logging.Filter):
        def filter(self, record: logging.LogRecord) -> bool:
            _with_trace(record, trace_id)
            return True

    trace_filter = _TraceFilter()
    logger.addFilter(trace_filter)

    try:
        logger.info("received_query", extra={"trace_id": trace_id})
        logger.debug("query_payload", extra={"trace_id": trace_id, "payload": req.model_dump()})

        # Lazy import to keep API import cost low
        from agent.graph import run_graph

        result = run_graph(query=req.query, time_hint=req.time, lang=req.lang, trace_id=trace_id) # Call the synchronous function

        # Expect result to be dict with keys text, citations
        if not isinstance(result, dict) or "text" not in result or "citations" not in result:
            logger.error("graph_return_invalid_shape", extra={"trace_id": trace_id, "result_type": type(result).__name__})
            raise HTTPException(status_code=500, detail="Graph returned invalid result shape.")

        elapsed_ms = int((time.time() - start) * 1000)
        logger.info("query_completed", extra={"trace_id": trace_id, "elapsed_ms": elapsed_ms})

        # Keep a trimmed debug trace
        _DEBUG_TRACES[trace_id] = {
            "elapsed_ms": elapsed_ms,
            "query": req.model_dump(),
            "result_preview": {
                "text_head": result.get("text", "")[:160],
                "citations_count": len(result.get("citations", [])),
            },
        }

        return AnswerResponse(text=result["text"], citations=result["citations"], trace_id=trace_id)
    finally:
        # Ensure filter is removed so it doesn't leak trace_id to other requests
        logger.removeFilter(trace_filter)


class IngestRequest(BaseModel):
    doc_id: Optional[str] = None
    title: str
    body: str
    doc_type: Optional[str] = None
    section: Optional[str] = None
    jurisdiction: Optional[str] = None
    lang: Optional[str] = None
    valid_from: Optional[str] = None
    valid_to: Optional[str] = None


@app.post("/ingest/doc")
def ingest_doc(req: IngestRequest) -> dict:
    trace_id = str(uuid.uuid4())
    logger.info("ingest_start", extra={"trace_id": trace_id})
    try:
        from ingestion.pipeline import ingest_document
        result = ingest_document(req.model_dump(), trace_id=trace_id)
        
        # Handle different response formats
        if "error" in result:
            raise HTTPException(status_code=500, detail=result["error"])
        
        # Return success response
        return {
            "status": "accepted", 
            "doc_id": result["doc_id"], 
            "trace_id": trace_id,
            "chunks": result.get("chunks", []),
            "message": result.get("message", "Document ingested successfully")
        }
        
    except Exception as exc:  # Explicitly surface exceptions for debuggability
        logger.exception("ingest_failed", extra={"trace_id": trace_id, "error": str(exc)})
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {exc}")


@app.post("/ingest/pdf")
async def ingest_pdf(
    file: UploadFile = File(...),
    doc_type: Optional[str] = None,
    jurisdiction: str = "KR",
    lang: str = "ko"
) -> dict:
    """Upload and ingest a PDF file."""
    trace_id = str(uuid.uuid4())
    logger.info("pdf_ingest_start", extra={"trace_id": trace_id, "filename": file.filename})
    
    try:
        # Save uploaded file temporarily
        import tempfile
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
            content = await file.read()
            tmp_file.write(content)
            tmp_path = tmp_file.name
        
        try:
            from ingestion.pipeline import ingest_pdf_file
            result = ingest_pdf_file(
                tmp_path,
                doc_type=doc_type,
                jurisdiction=jurisdiction,
                lang=lang
            )
            
            if "error" in result:
                raise HTTPException(status_code=500, detail=result["error"])
            
            return {
                "status": "accepted",
                "file_name": result["file_name"],
                "sections_processed": result["sections_processed"],
                "documents_ingested": result["documents_ingested"],
                "total_chunks": result["total_chunks"],
                "trace_id": trace_id
            }
            
        finally:
            # Clean up temporary file
            os.unlink(tmp_path)
            
    except Exception as exc:
        logger.exception("pdf_ingest_failed", extra={"trace_id": trace_id, "error": str(exc)})
        raise HTTPException(status_code=500, detail=f"PDF ingestion failed: {exc}")


@app.post("/ingest/data-directory")
def ingest_data_directory(
    doc_type: Optional[str] = None,
    jurisdiction: str = "KR",
    lang: str = "ko"
) -> dict:
    """Ingest all PDFs from the data directory."""
    trace_id = str(uuid.uuid4())
    logger.info("data_directory_ingest_start", extra={"trace_id": trace_id})
    
    try:
        from ingestion.pipeline import ingest_pdf_directory
        result = ingest_pdf_directory(
            "data",
            doc_type=doc_type,
            jurisdiction=jurisdiction,
            lang=lang
        )
        
        if "error" in result:
            raise HTTPException(status_code=500, detail=result["error"])
        
        return {
            "status": "accepted",
            "files_processed": result["files_processed"],
            "total_documents": result["total_documents"],
            "total_chunks": result["total_chunks"],
            "results": result["results"],
            "trace_id": trace_id
        }
        
    except Exception as exc:
        logger.exception("data_directory_ingest_failed", extra={"trace_id": trace_id, "error": str(exc)})
        raise HTTPException(status_code=500, detail=f"Data directory ingestion failed: {exc}")


@app.post("/maintenance/rebuild-metadata-vectors")
def rebuild_metadata_vectors() -> dict:
    trace_id = str(uuid.uuid4())
    logger.info("rebuild_metadata_vectors_start", extra={"trace_id": trace_id})
    try:
        from ingestion.metadata_vectors import rebuild_all_facet_value_vectors
        count = rebuild_all_facet_value_vectors(trace_id=trace_id)
        return {"status": "ok", "updated_count": count, "trace_id": trace_id}
    except Exception as exc:
        logger.exception("rebuild_metadata_vectors_failed", extra={"trace_id": trace_id, "error": str(exc)})
        raise HTTPException(status_code=500, detail=f"Rebuild failed: {exc}")


@app.get("/debug/trace/{trace_id}")
def get_trace(trace_id: str) -> dict:
    trace = _DEBUG_TRACES.get(trace_id)
    if not trace:
        raise HTTPException(status_code=404, detail="Trace not found")
    return trace


# Background Ingestion Endpoints
@app.post("/ingest/start", response_model=IngestionResponse)
async def start_ingestion(request: IngestionRequest):
    """Start a background PDF ingestion job."""
    try:
        job_id = start_background_ingestion(
            directory_path=request.directory_path,
            doc_type=request.doc_type,
            jurisdiction=request.jurisdiction,
            lang=request.lang
        )
        
        return IngestionResponse(
            job_id=job_id,
            message=f"Started background ingestion job {job_id}"
        )
    except Exception as e:
        logger.error(f"Failed to start ingestion: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/ingest/status/{job_id}", response_model=IngestionStatusResponse)
async def get_ingestion_job_status(job_id: str):
    """Get the status of a background ingestion job."""
    status = get_ingestion_status(job_id)
    if not status:
        raise HTTPException(status_code=404, detail=f"Ingestion job {job_id} not found")
    
    return IngestionStatusResponse(**status)


@app.get("/ingest/jobs", response_model=List[IngestionStatusResponse])
async def get_all_ingestion_jobs_endpoint():
    """Get all ingestion jobs."""
    jobs = get_all_ingestion_jobs()
    return [IngestionStatusResponse(**job) for job in jobs]


@app.post("/ingest/reset-and-start", response_model=IngestionResponse)
async def reset_and_start_ingestion(request: IngestionRequest):
    """Reset database and start background ingestion."""
    try:
        # Reset database first
        from adapters.weaviate_adapter import WeaviateClient
        with WeaviateClient() as client:
            if not client._connected:
                raise HTTPException(status_code=500, detail="Cannot connect to Weaviate")
            
            if not client.reset_database():
                raise HTTPException(status_code=500, detail="Failed to reset database")
        
        # Start background ingestion
        job_id = start_background_ingestion(
            directory_path=request.directory_path,
            doc_type=request.doc_type,
            jurisdiction=request.jurisdiction,
            lang=request.lang
        )
        
        return IngestionResponse(
            job_id=job_id,
            message=f"Database reset and started background ingestion job {job_id}"
        )
    except Exception as e:
        logger.error(f"Failed to reset and start ingestion: {e}")
        raise HTTPException(status_code=500, detail=str(e))
