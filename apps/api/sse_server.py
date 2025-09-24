import asyncio
import json
import logging
import uuid
from typing import Dict, Any, List, Optional

from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from agent.adaptive_graph import run_adaptive_graph
from agent.nodes.observer import register_observer
from memory.conversation_memory import conversation_memory

logger = logging.getLogger(__name__)

# Initialize conversation memory to ensure database is created
logger.info(f"Conversation memory initialized with {len(conversation_memory._conversations)} sessions")

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# SSE connection manager
class SSEManager:
    def __init__(self):
        self.active_connections = {}
        logger.info("SSEManager initialized")
    
    def disconnect(self, client_id: str):
        if client_id in self.active_connections:
            del self.active_connections[client_id]
            logger.info(f"Client {client_id} disconnected")

# Global manager instance
manager = SSEManager()

# SSE Observer class
class SSEObserver:
    def __init__(self):
        self.callbacks = []
    
    def on_update(self, node_id: str, status: str, content: Any = None, raw_content: Any = None):
        self.callbacks.append((node_id, status, content, raw_content))
        logger.debug(f"Observer received update: {node_id} - {status}")

# Request model
class QueryRequest(BaseModel):
    query: str = Field(..., description="The search query")
    time: Optional[str] = Field(None, description="Time hint for the query")
    lang: Optional[str] = Field(None, description="Language hint for the query")
    query_id: Optional[str] = Field(None, description="Optional query ID")
    session_id: Optional[str] = Field(None, description="Optional session ID")

def format_sse_message(data: Dict[str, Any], event_type: str = "message") -> str:
    """Format data as an SSE message."""
    return f"event: {event_type}\ndata: {json.dumps(data)}\n\n"

def create_node_summary(node_id: str, status: str, content: Any = None) -> str:
    """Create a user-friendly summary of a node update."""
    if node_id == "candidate_search":
        if status == "in_progress":
            return "Searching for relevant documents..."
        elif status == "completed":
            if content and isinstance(content, dict):
                count = content.get("count", 0)
                return f"Found {count} relevant documents"
            return "Search completed"
    elif node_id == "narrowed_search":
        if status == "in_progress":
            return "Narrowing down search results..."
        elif status == "completed":
            if content and isinstance(content, dict):
                count = content.get("count", 0)
                return f"Narrowed to {count} most relevant results"
            return "Narrowed search completed"
    elif node_id == "rerank_diversify":
        if status == "in_progress":
            return "Reranking and applying memory boosts..."
        elif status == "completed":
            if content and isinstance(content, dict):
                count = content.get("count", 0)
                boosted_count = content.get("boosted_count", 0)
                if boosted_count > 0:
                    return f"Reranked {count} results (memory boosted {boosted_count} chunks)"
                return f"Reranked {count} results"
            return "Reranking completed"
    elif node_id == "validator":
        if status == "in_progress":
            return "Validating search results..."
        elif status == "completed":
            if content and isinstance(content, dict):
                valid = content.get("valid", False)
                confidence = content.get("confidence", 0)
                if valid:
                    return f"Results validated (confidence: {confidence:.1%})"
                else:
                    return "Results need refinement"
            return "Validation completed"
    elif node_id == "planner":
        if content and isinstance(content, dict):
            search_type = content.get("search_type")
            if search_type:
                return f"Search strategy: {search_type}"
        return "Planning search strategy"
    elif node_id == "answerer":
        if status == "in_progress":
            return "Generating answer..."
        elif status == "completed":
            if content and isinstance(content, dict):
                citation_count = content.get("citation_count", 0)
                return f"Answer generated with {citation_count} citations"
            return "Answer generated"
    elif node_id == "memory_updater":
        if status == "in_progress":
            return "Updating memory with cited chunks..."
        elif status == "completed":
            if content and isinstance(content, dict):
                updated_count = content.get("updated_count", 0)
                if updated_count > 0:
                    return f"Updated memory for {updated_count} cited chunks"
                return "Memory update completed"
            return "Memory update completed"
    elif node_id == "meta_agent":
        if status == "in_progress":
            return "Analyzing query complexity and generating workflow..."
        elif status == "completed":
            if content and isinstance(content, dict):
                workflow_type = content.get("workflow_type", "unknown")
                complexity_score = content.get("complexity_score", 0)
                agent_summary = content.get("agent_summary", "")
                return f"Generated {workflow_type} workflow (complexity: {complexity_score}/10)\nAgent: {agent_summary}"
            return "Workflow analysis completed"
    elif node_id == "comprehensive_search":
        if status == "in_progress":
            return "Performing comprehensive search for analysis..."
        elif status == "completed":
            if content and isinstance(content, dict):
                count = content.get("count", 0)
                return f"Retrieved {count} documents for comprehensive analysis"
            return "Comprehensive search completed"
    elif node_id == "data_extraction":
        if status == "in_progress":
            return "Extracting and preparing data for computation..."
        elif status == "completed":
            if content and isinstance(content, dict):
                count = content.get("extracted_count", 0)
                return f"Extracted data from {count} documents"
            return "Data extraction completed"
    elif node_id == "computation":
        if status == "in_progress":
            return "Running custom computation logic..."
        elif status == "completed":
            if content and isinstance(content, dict):
                input_count = content.get("input_count", 0)
                output_count = content.get("output_count", 0)
                comp_type = content.get("computation_type", "unknown")
                return f"Computed {input_count} → {output_count} results ({comp_type})"
            return "Computation completed"
    elif node_id == "complex_filtering":
        if status == "in_progress":
            return "Applying complex filtering logic..."
        elif status == "completed":
            if content and isinstance(content, dict):
                original_count = content.get("original_count", 0)
                filtered_count = content.get("filtered_count", 0)
                return f"Filtered {original_count} → {filtered_count} results"
            return "Complex filtering completed"
    elif node_id == "quality_monitor":
        if status == "in_progress":
            assessment_type = content.get("assessment_type", "quality") if content else "quality"
            return f"Assessing {assessment_type.replace('_', ' ')}..."
        elif status == "completed":
            if content and isinstance(content, dict):
                quality_score = content.get("quality_score", 0)
                assessment_type = content.get("assessment_type", "quality")
                issues_count = len(content.get("issues", []))
                return f"{assessment_type.replace('_', ' ').title()} quality: {quality_score:.2f} ({issues_count} issues found)"
            return "Quality assessment completed"
    elif node_id == "adaptive_response":
        if status == "in_progress":
            trigger = content.get("trigger", "quality issue") if content else "quality issue"
            return f"Adapting to {trigger.replace('_', ' ')}..."
        elif status == "completed":
            if content and isinstance(content, dict):
                action = content.get("action", "adjustment")
                return f"Applied {action.replace('_', ' ')}"
            return "Adaptive response completed"
    elif node_id == "context_agent":
        if status == "in_progress":
            return "Analyzing conversation context..."
        elif status == "completed":
            if content and isinstance(content, dict):
                is_follow_up = content.get("is_follow_up", False)
                topic = content.get("conversation_topic", "general")
                relevance = content.get("context_relevance", "low")
                return f"Context analyzed: {topic} (follow-up: {is_follow_up}, relevance: {relevance})"
            return "Context analysis completed"
    
    return f"{node_id.replace('_', ' ').title()} is {status.replace('_', ' ')}"

# SSE endpoint
@app.get("/sse/agent")
async def sse_endpoint(request: Request, query_id: Optional[str] = None):
    client_id = query_id or str(uuid.uuid4())
    logger.info(f"SSE connection request received from {client_id} with query_id: {query_id}")
    
    async def event_generator():
        try:
            # Send initial connection message
            yield format_sse_message({"client_id": client_id}, "connected")
            
            # Keep connection alive
            while True:
                if await request.is_disconnected():
                    logger.info(f"Client {client_id} disconnected")
                    break
                    
                # Check for a small delay to avoid high CPU usage
                await asyncio.sleep(0.1)
                
        except Exception as e:
            logger.exception(f"Error in SSE connection: {e}")
        finally:
            manager.disconnect(client_id)
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )

# Query endpoint - returns streaming SSE response
@app.post("/api/query")
async def query_endpoint_post(request: QueryRequest):
    return StreamingResponse(
        process_query_stream(request),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )

@app.get("/api/query")
async def query_endpoint_get(query: str, query_id: Optional[str] = None, session_id: Optional[str] = None):
    request = QueryRequest(query=query, query_id=query_id, session_id=session_id)
    return StreamingResponse(
        process_query_stream(request),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )

async def process_query_stream(request: QueryRequest):
    query_id = request.query_id or str(uuid.uuid4())
    session_id = request.session_id or query_id
    logger.info(f"Processing query: {request.query} (ID: {query_id}, Session: {session_id})")
    
    try:
        # Create a node observer for this query
        node_observer = SSEObserver()
        
        # Create a simple synchronous observer function that directly updates our SSE observer
        def notify_observer(node_id, status, content=None, raw_content=None):
            try:
                node_observer.on_update(node_id, status, content, raw_content)
                logger.debug(f"Observer received: {node_id} - {status}")
            except Exception as e:
                logger.error(f"Error notifying observer: {e}")
        
        # Replace the notify_observers function completely to avoid async issues
        import agent.nodes.observer as observer_module
        
        def simple_notify_observers(node_id, status, content=None):
            # Only call our simple observer
            notify_observer(node_id, status, content)
            # Print debug info like the original
            print(f"[DEBUG] Queued update for {node_id}: {status}")
        
        # Patch the observer module function
        observer_module.notify_observers = simple_notify_observers
        
        # Also patch the function in the adaptive_graph module if it's already imported
        import sys
        if 'agent.adaptive_graph' in sys.modules:
            adaptive_graph_module = sys.modules['agent.adaptive_graph']
            if hasattr(adaptive_graph_module, 'notify_observers'):
                adaptive_graph_module.notify_observers = simple_notify_observers
        
        # Send initial processing message
        yield format_sse_message({
            "query_id": query_id,
            "status": "processing_started",
            "summary": "Starting query processing..."
        }, "processing_started")
        
        # Run the adaptive graph in a separate thread and monitor for updates in real-time
        import threading
        import queue

        # Create a queue to collect results
        result_queue = queue.Queue()

        def run_adaptive_graph_thread():
            try:
                from agent.adaptive_graph import run_adaptive_graph
                result = run_adaptive_graph(query=request.query, time_hint=request.time, lang=request.lang, trace_id=query_id, session_id=session_id)
                result_queue.put(result)
            except Exception as e:
                result_queue.put({"error": str(e)})

        # Start the adaptive graph in a separate thread
        graph_thread = threading.Thread(target=run_adaptive_graph_thread)
        graph_thread.start()
        
        # Monitor for updates while the graph is running
        while graph_thread.is_alive():
            # Send any queued updates
            if node_observer.callbacks:
                callbacks = node_observer.callbacks.copy()
                node_observer.callbacks.clear()
                
                for node_id, status, content, raw_content in callbacks:
                    summary = create_node_summary(node_id, status, content)
                    
                    yield format_sse_message({
                        "node_id": node_id,
                        "status": status,
                        "summary": summary,
                        "content": content,
                        "query_id": query_id
                    }, "node_update")
            
            # Small delay to avoid busy waiting
            await asyncio.sleep(0.1)
        
        # Get the final result
        try:
            result = result_queue.get_nowait()
        except queue.Empty:
            result = {"error": "Graph execution failed"}
        
        logger.info(f"Query processed, result keys: {list(result.keys() if result else {})}")
        
        # Send any remaining updates
        if node_observer.callbacks:
            callbacks = node_observer.callbacks.copy()
            node_observer.callbacks.clear()
            
            for node_id, status, content, raw_content in callbacks:
                summary = create_node_summary(node_id, status, content)
                
                yield format_sse_message({
                    "node_id": node_id,
                    "status": status,
                    "summary": summary,
                    "content": content,
                    "query_id": query_id
                }, "node_update")
        
        # Send final answer
        if result:
            yield format_sse_message({
                "text": result.get("text", ""),
                "citations": result.get("citations", []),
                "session_id": session_id,
                "has_context": result.get("has_context", False),
                "query_id": query_id
            }, "answer")
        else:
            yield format_sse_message({
                "error": "No result generated",
                "query_id": query_id
            }, "error")
        
    except Exception as e:
        logger.exception(f"Error in process_query_stream: {e}")
        yield format_sse_message({"error": str(e), "query_id": query_id}, "error")

@app.get("/api/document/{chunk_id}")
async def get_document_details(chunk_id: str):
    """Get detailed document information for a chunk ID."""
    try:
        logger.info(f"API request for document: {chunk_id}")
        from adapters.chroma_adapter import ChromaClient
        
        with ChromaClient() as client:
            if not client._connected:
                return {"error": "Database not connected"}
            
            collection = client._client.get_collection(client.chunk_collection)
            
            # Get document by ID - try multiple approaches
            # First, try to get by the exact ID
            logger.info(f"Trying to get document by ID: {chunk_id}")
            results = collection.get(
                ids=[chunk_id],
                include=["metadatas", "documents"]
            )
            logger.info(f"Results from ID query: {len(results.get('ids', []))} documents found")
            
            # If not found, try to find by topic or other metadata
            if not results or not results['ids']:
                logger.info("ID query failed, trying fallback approach")
                # Extract topic from chunk_id (e.g., "회의록_01_마케팅_1:0" -> "마케팅")
                topic_keywords = chunk_id.split('_')
                if len(topic_keywords) >= 3:
                    topic_keyword = topic_keywords[2]  # Get the topic part
                    # Try to find documents that contain this topic
                    all_results = collection.get(include=["metadatas", "documents"])
                    logger.info(f"Found {len(all_results['ids'])} total documents in collection")
                    for i, doc_id in enumerate(all_results['ids']):
                        if chunk_id == doc_id:
                            # Found exact match
                            logger.info(f"Found exact match: {doc_id}")
                            results = {
                                'ids': [doc_id],
                                'metadatas': [all_results['metadatas'][i]],
                                'documents': [all_results['documents'][i]]
                            }
                            break
            
            if not results or not results['ids']:
                return {"error": "Document not found"}
            
            metadata = results['metadatas'][0]
            document = results['documents'][0]
            
            # Parse metadata into a more useful format (generic for any document type)
            doc_info = {
                "chunk_id": chunk_id,
                "doc_id": metadata.get("doc_id", ""),
                "title": metadata.get("title", metadata.get("topic", "")),
                "topic": metadata.get("topic", ""),
                "date": metadata.get("date", metadata.get("meeting_date", "")),
                "meeting_date": metadata.get("meeting_date", ""),  # Keep for backward compatibility
                "location": metadata.get("location", metadata.get("venue", "")),
                "venue": metadata.get("venue", ""),
                "attendees": metadata.get("attendees", ""),
                "authors": metadata.get("authors", ""),
                "participants": metadata.get("participants", ""),
                "key_decisions": metadata.get("key_decisions", ""),
                "conclusions": metadata.get("conclusions", ""),
                "findings": metadata.get("findings", ""),
                "action_items": metadata.get("action_items", ""),
                "next_steps": metadata.get("next_steps", ""),
                "recommendations": metadata.get("recommendations", ""),
                "file_name": metadata.get("file_name", ""),
                "content_preview": document[:500] + "..." if len(document) > 500 else document,
                "full_content": document
            }
            
            # Parse JSON fields (generic for any document type)
            try:
                json_fields = [
                    "attendees", "authors", "participants",
                    "key_decisions", "conclusions", "findings", 
                    "action_items", "next_steps", "recommendations"
                ]
                for field in json_fields:
                    if doc_info[field] and isinstance(doc_info[field], str):
                        try:
                            doc_info[field] = json.loads(doc_info[field])
                        except:
                            pass  # Keep as string if parsing fails
            except:
                pass  # Keep as string if parsing fails
            
            return doc_info
            
    except Exception as e:
        logger.exception(f"Error getting document details: {e}")
        return {"error": str(e)}

# Mount static files
app.mount("/", StaticFiles(directory="frontend", html=True), name="static")