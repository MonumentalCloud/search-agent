#!/usr/bin/env python3
"""
Streaming Chat GUI for Retrieval Agent

A Streamlit-based chat interface that shows the agent's thought process in real-time.
"""

import json
import logging
import os
import sys
import time
from datetime import datetime
from typing import Dict, List, Optional

import requests
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, project_root)

from configs.load import setup_root_logger

# Setup logging
setup_root_logger(logging.INFO)
logger = logging.getLogger(__name__)

# API Configuration
API_BASE_URL = "http://localhost:8001"
DEFAULT_QUERY = "전자금융거래법 시행령에서 규정하는 내용은 무엇인가요?"

# Streamlit page config
st.set_page_config(
    page_title="Retrieval Agent Chat",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .chat-message {
        padding: 1rem;
        border-radius: 10px;
        margin: 1rem 0;
        border-left: 4px solid #1f77b4;
    }
    .user-message {
        background-color: #f0f2f6;
        border-left-color: #ff6b6b;
    }
    .agent-message {
        background-color: #e8f4fd;
        border-left-color: #1f77b4;
    }
    .thinking-process {
        background-color: #fff3cd;
        border-left-color: #ffc107;
        font-family: monospace;
        font-size: 0.9rem;
    }
    .citation {
        background-color: #d1ecf1;
        border-left-color: #17a2b8;
        padding: 0.5rem;
        margin: 0.5rem 0;
        border-radius: 5px;
    }
    .metric-card {
        background-color: #f8f9fa;
        padding: 1rem;
        border-radius: 8px;
        border: 1px solid #dee2e6;
        text-align: center;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []
if "thinking_process" not in st.session_state:
    st.session_state.thinking_process = []
if "api_status" not in st.session_state:
    st.session_state.api_status = "unknown"


def check_api_status() -> str:
    """Check if the API is running."""
    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=5)
        if response.status_code == 200:
            return "online"
        else:
            return "error"
    except requests.exceptions.RequestException:
        return "offline"


def get_trace_details(trace_id: str) -> Optional[Dict]:
    """Get detailed trace information."""
    try:
        response = requests.get(f"{API_BASE_URL}/debug/trace/{trace_id}", timeout=10)
        if response.status_code == 200:
            return response.json()
        else:
            return None
    except requests.exceptions.RequestException:
        return None


def stream_query(query: str, lang: str = "ko", time_hint: str = None) -> Dict:
    """Send query to the agent and return response."""
    try:
        payload = {
            "query": query,
            "lang": lang,
            "time": time_hint
        }
        
        response = requests.post(
            f"{API_BASE_URL}/agent/query",
            json=payload,
            timeout=60
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            return {"error": f"API error: {response.status_code}"}
            
    except requests.exceptions.RequestException as e:
        return {"error": f"Connection error: {str(e)}"}


def display_thinking_process(trace_data: Dict, message_index: int = 0):
    """Display the agent's thinking process."""
    if not trace_data:
        return
    
    with st.expander("🧠 Agent Thinking Process", expanded=False):
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("📊 Query Analysis")
            if "query" in trace_data:
                query_info = trace_data["query"]
                st.write(f"**Query:** {query_info.get('query', 'N/A')}")
                st.write(f"**Language:** {query_info.get('lang', 'N/A')}")
                st.write(f"**Time Hint:** {query_info.get('time', 'N/A')}")
        
        with col2:
            st.subheader("⏱️ Performance")
            if "elapsed_ms" in trace_data:
                elapsed = trace_data["elapsed_ms"]
                st.metric("Response Time", f"{elapsed}ms")
                
                # Performance indicator
                if elapsed < 1000:
                    st.success("⚡ Fast response")
                elif elapsed < 3000:
                    st.warning("🐌 Moderate response")
                else:
                    st.error("🐢 Slow response")
        
        # Result preview
        if "result_preview" in trace_data:
            preview = trace_data["result_preview"]
            st.subheader("📝 Result Preview")
            st.write(f"**Text Length:** {len(preview.get('text_head', ''))} chars")
            st.write(f"**Citations:** {preview.get('citations_count', 0)}")
            
            if preview.get('text_head'):
                # Add unique key to prevent duplicate element ID error
                unique_key = f"response_preview_{message_index}"
                st.text_area("Response Preview", preview['text_head'], height=100, key=unique_key)


def display_citations(citations: List[Dict]):
    """Display citations in a nice format."""
    if not citations:
        return
    
    st.subheader("📚 Sources & Citations")
    
    for i, citation in enumerate(citations, 1):
        with st.container():
            st.markdown(f"""
            <div class="citation">
                <strong>Source {i}:</strong> {citation.get('doc_id', 'Unknown')}<br>
                <strong>Section:</strong> {citation.get('section', 'N/A')}<br>
                <strong>Chunk ID:</strong> {citation.get('chunk_id', 'N/A')}<br>
                <strong>Valid From:</strong> {citation.get('valid_from', 'N/A')}<br>
                <strong>Valid To:</strong> {citation.get('valid_to', 'N/A')}
            </div>
            """, unsafe_allow_html=True)


def create_performance_chart(trace_data: Dict):
    """Create a performance visualization."""
    if not trace_data or "elapsed_ms" not in trace_data:
        return
    
    elapsed = trace_data["elapsed_ms"]
    
    # Create a simple performance gauge
    fig = go.Figure(go.Indicator(
        mode = "gauge+number+delta",
        value = elapsed,
        domain = {'x': [0, 1], 'y': [0, 1]},
        title = {'text': "Response Time (ms)"},
        delta = {'reference': 2000},  # Reference point
        gauge = {
            'axis': {'range': [None, 5000]},
            'bar': {'color': "darkblue"},
            'steps': [
                {'range': [0, 1000], 'color': "lightgreen"},
                {'range': [1000, 3000], 'color': "yellow"},
                {'range': [3000, 5000], 'color': "red"}
            ],
            'threshold': {
                'line': {'color': "red", 'width': 4},
                'thickness': 0.75,
                'value': 3000
            }
        }
    ))
    
    fig.update_layout(height=300)
    return fig


def weaviate_explorer():
    import weaviate
    st.header("🔍 Weaviate Explorer")
    query = st.text_input("Search chunks (leave blank for random):", "")
    n = st.number_input("Number of chunks", min_value=1, max_value=20, value=5)
    try:
        client = weaviate.connect_to_local(host="localhost", port=8080)
        chunk_class = "Chunk"
        if query:
            # Simple BM25 search (or use hybrid if you want)
            results = client.collections.get(chunk_class).query.bm25(
                query=query,
                limit=n,
                # Get all properties by not specifying return_properties
                # Get metadata using include_vector=True
                include_vector=True
            )
        else:
            # Fetch random/recent chunks
            results = client.collections.get(chunk_class).query.fetch_objects(
                limit=n,
                # Get all properties by not specifying return_properties
                # Get metadata using include_vector=True
                include_vector=True
            )
        
        # Display each chunk with all its properties
        for i, obj in enumerate(results.objects, 1):
            with st.expander(f"Chunk #{i}: {obj.properties.get('chunk_id', 'Unknown ID')}", expanded=True):
                # First show the body text
                if "body" in obj.properties:
                    st.markdown("### Content")
                    st.markdown(f"```\n{obj.properties['body']}\n```")
                
                # Then show all metadata in a more organized way
                st.markdown("### Metadata")
                
                # Core identifiers in one row
                col1, col2 = st.columns(2)
                with col1:
                    st.write("**Chunk ID:**", obj.properties.get("chunk_id", "N/A"))
                with col2:
                    st.write("**Doc ID:**", obj.properties.get("doc_id", "N/A"))
                
                # Entities and relationships (if present)
                if "entities" in obj.properties:
                    st.markdown("#### Entities")
                    entities = obj.properties["entities"]
                    if entities:
                        for i, entity in enumerate(entities):
                            st.write(f"- {entity}")
                    else:
                        st.write("*No entities*")
                
                if "relationships" in obj.properties:
                    st.markdown("#### Relationships")
                    relationships = obj.properties["relationships"]
                    if relationships:
                        for rel in relationships:
                            st.write(f"- {rel.get('subject', '')} → {rel.get('relation', '')} → {rel.get('object', '')}")
                    else:
                        st.write("*No relationships*")
                
                # All other properties
                st.markdown("#### All Properties")
                other_props = {k: v for k, v in obj.properties.items() 
                              if k not in ["body", "chunk_id", "doc_id", "entities", "relationships"]}
                for k, v in other_props.items():
                    st.write(f"**{k}:** {v}")
                
                # Show score if available
                if hasattr(obj, "metadata") and obj.metadata and hasattr(obj.metadata, "score"):
                    st.write(f"**Score:** {obj.metadata.score}")
    except Exception as e:
        st.error(f"Weaviate Explorer error: {e}")


def main():
    # Header
    st.markdown('<h1 class="main-header">🤖 Retrieval Agent Chat</h1>', unsafe_allow_html=True)
    
    # Sidebar
    with st.sidebar:
        st.header("🔧 Configuration")
        
        # API Status
        api_status = check_api_status()
        if api_status == "online":
            st.success("🟢 API Online")
        elif api_status == "offline":
            st.error("🔴 API Offline")
        else:
            st.warning("🟡 API Status Unknown")
        
        st.session_state.api_status = api_status
        
        # Language selection
        lang = st.selectbox(
            "Language",
            ["ko", "en"],
            index=0,
            help="Select the language for your queries"
        )
        
        # Time hint
        time_hint = st.text_input(
            "Time Hint (Optional)",
            placeholder="e.g., 2024, recent, before 2023",
            help="Add a time context to your query"
        )
        
        # Sample queries
        st.header("💡 Sample Queries")
        sample_queries = [
            "전자금융거래법 시행령에서 규정하는 내용은 무엇인가요?",
            "ISA 계좌 이전하는 방법",
            "장기주택마련저축 정의",
            "출산 장려금 자격 요건",
            "금융감독규정 시행세칙"
        ]
        
        for query in sample_queries:
            if st.button(f"📝 {query[:30]}...", key=f"sample_{query}"):
                st.session_state.sample_query = query
        
        # Database Management
        st.header("🗄️ Database Management")
        
        # Initialize ingestion job tracking
        if "ingestion_job_id" not in st.session_state:
            st.session_state.ingestion_job_id = None
        if "ingestion_status" not in st.session_state:
            st.session_state.ingestion_status = None
        
        # Start ingestion button
        if st.button("🚀 Reset & Ingest PDFs", type="primary"):
            with st.spinner("Starting background ingestion..."):
                try:
                    response = requests.post(
                        f"{API_BASE_URL}/ingest/reset-and-start",
                        json={
                            "directory_path": "data",
                            "doc_type": "regulation",
                            "jurisdiction": "KR",
                            "lang": "ko"
                        },
                        timeout=10
                    )
                    
                    if response.status_code == 200:
                        result = response.json()
                        st.session_state.ingestion_job_id = result["job_id"]
                        st.success(f"✅ Started ingestion job: {result['job_id'][:8]}...")
                        st.rerun()
                    else:
                        st.error(f"❌ Failed to start ingestion: {response.text}")
                except Exception as e:
                    st.error(f"❌ Error: {e}")
        
        # Show ingestion progress
        if st.session_state.ingestion_job_id:
            st.subheader("📊 Ingestion Progress")
            
            # Get current status
            try:
                response = requests.get(
                    f"{API_BASE_URL}/ingest/status/{st.session_state.ingestion_job_id}",
                    timeout=5
                )
                
                if response.status_code == 200:
                    status = response.json()
                    st.session_state.ingestion_status = status
                    
                    # Progress bar
                    progress = status["progress"]
                    st.progress(progress)
                    st.write(f"**Progress:** {progress:.1%}")
                    
                    # Status details
                    st.write(f"**Status:** {status['status']}")
                    st.write(f"**Current File:** {status['current_file']}")
                    st.write(f"**Current Step:** {status['current_step']}")
                    st.write(f"**Files Processed:** {status['files_processed']}/{status['total_files']}")
                    st.write(f"**Documents Created:** {status['documents_created']}")
                    st.write(f"**Chunks Created:** {status['chunks_created']}")
                    
                    # Auto-refresh if still running
                    if status["status"] == "running":
                        time.sleep(2)
                        st.rerun()
                    elif status["status"] == "completed":
                        st.success("🎉 Ingestion completed successfully!")
                    elif status["status"] == "failed":
                        st.error(f"❌ Ingestion failed: {status.get('error_message', 'Unknown error')}")
                        
            except Exception as e:
                st.warning(f"⚠️ Could not fetch status: {e}")
        
        # Clear chat
        if st.button("🗑️ Clear Chat"):
            st.session_state.messages = []
            st.session_state.thinking_process = []
            st.rerun()
    
    # Main chat area
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.header("💬 Chat")
        
        # Display chat messages
        for message_index, message in enumerate(st.session_state.messages):
            with st.container():
                if message["role"] == "user":
                    st.markdown(f"""
                    <div class="chat-message user-message">
                        <strong>👤 You:</strong><br>
                        {message["content"]}
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.markdown(f"""
                    <div class="chat-message agent-message">
                        <strong>🤖 Agent:</strong><br>
                        {message["content"]}
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Show citations if available
                    if "citations" in message and message["citations"]:
                        display_citations(message["citations"])
                    
                    # Show thinking process if available
                    if "trace_id" in message:
                        trace_data = get_trace_details(message["trace_id"])
                        if trace_data:
                            display_thinking_process(trace_data, message_index)
        
        # Chat input
        if st.session_state.api_status != "online":
            st.error("⚠️ API is not running. Please start the API server first.")
            st.info("Run: `python start.py --api-only`")
        else:
            # Handle sample query
            if hasattr(st.session_state, 'sample_query'):
                query = st.session_state.sample_query
                delattr(st.session_state, 'sample_query')
            else:
                query = st.text_input(
                    "Ask a question:",
                    placeholder=DEFAULT_QUERY,
                    key="chat_input"
                )
            
            if st.button("🚀 Send", disabled=not query) or (query and query != DEFAULT_QUERY):
                if query:
                    # Add user message
                    st.session_state.messages.append({
                        "role": "user",
                        "content": query,
                        "timestamp": datetime.now()
                    })
                    
                    # Show thinking indicator
                    with st.spinner("🤔 Agent is thinking..."):
                        # Send query to agent
                        response = stream_query(query, lang, time_hint if time_hint else None)
                    
                    if "error" in response:
                        # Error response
                        st.session_state.messages.append({
                            "role": "assistant",
                            "content": f"❌ Error: {response['error']}",
                            "timestamp": datetime.now()
                        })
                    else:
                        # Success response
                        st.session_state.messages.append({
                            "role": "assistant",
                            "content": response.get("text", "No response"),
                            "citations": response.get("citations", []),
                            "trace_id": response.get("trace_id"),
                            "timestamp": datetime.now()
                        })
                    
                    # Rerun to show new messages
                    st.rerun()
    
    with col2:
        st.header("📊 Analytics")
        
        # Performance metrics
        if st.session_state.messages:
            total_messages = len(st.session_state.messages)
            user_messages = len([m for m in st.session_state.messages if m["role"] == "user"])
            agent_messages = len([m for m in st.session_state.messages if m["role"] == "assistant"])
            
            col_a, col_b = st.columns(2)
            with col_a:
                st.metric("Total Messages", total_messages)
            with col_b:
                st.metric("User Queries", user_messages)
            
            # Performance chart for last response
            last_agent_message = None
            for message in reversed(st.session_state.messages):
                if message["role"] == "assistant" and "trace_id" in message:
                    last_agent_message = message
                    break
            
            if last_agent_message:
                trace_data = get_trace_details(last_agent_message["trace_id"])
                if trace_data:
                    fig = create_performance_chart(trace_data)
                    if fig:
                        st.plotly_chart(fig, use_container_width=True)
        
        # System info
        st.header("ℹ️ System Info")
        st.info(f"""
        **API URL:** {API_BASE_URL}
        **Status:** {st.session_state.api_status}
        **Language:** {lang}
        **Time Hint:** {time_hint or 'None'}
        """)

    # Add to sidebar
    with st.sidebar:
        st.header("🧭 Navigation")
        weaviate_explorer()


if __name__ == "__main__":
    main()
