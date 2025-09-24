#!/usr/bin/env python3
"""
Retrieval Agent Startup Script

This script handles the complete setup and startup of the Weaviate-First Retrieval Agent.
It can start Weaviate, ingest PDFs, rebuild metadata vectors, and launch both the API server and chat GUI.

Usage:
  python start.py                    # Full setup + API + Chat GUI
  python start.py --full-stack       # API + Chat GUI only
  python start.py --api-only         # API server only
  python start.py --chat-only        # Chat GUI only
  python start.py --skip-docker      # Skip Weaviate setup
  python start.py --stop             # Stop all background processes
"""

import argparse
import logging
import os
import subprocess
import sys
import time
import json
from pathlib import Path
from typing import Dict
# import threading # Not needed with subprocess.Popen for API/GUI

# Add project root and utils directory to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "utils")) # Add utils to path

from configs.load import setup_root_logger
from utils.pid_manager import PIDManager # Import PIDManager

# Initialize PIDManager
pid_manager = PIDManager(pid_file_path=project_root / ".agent_pids")

logger = logging.getLogger(__name__)

def check_docker():
    """Check if Docker is available."""
    try:
        result = subprocess.run(['docker', '--version'], capture_output=True, text=True)
        return result.returncode == 0
    except FileNotFoundError:
        return False

def start_weaviate():
    """Start Weaviate using Docker."""
    if not check_docker():
        logger.error("Docker is not installed or not available")
        return False
    
    logger.info("Starting Weaviate...")
    
    # Stop existing container if it exists
    subprocess.run(['docker', 'stop', 'weaviate'], check=False, capture_output=True)
    subprocess.run(['docker', 'rm', 'weaviate'], check=False, capture_output=True)
    
    # Start new Weaviate container
    cmd = [
        'docker', 'run', '-d',
        '--name', 'weaviate',
        '-p', '8080:8080',
        '-p', '50051:50051',
        '-e', 'QUERY_DEFAULTS_LIMIT=25',
        '-e', 'AUTHENTICATION_ANONYMOUS_ACCESS_ENABLED=true',
        '-e', 'PERSISTENCE_DATA_PATH=/var/lib/weaviate',
        '-e', 'DEFAULT_VECTORIZER_MODULE=none',
        '-e', 'ENABLE_MODULES=',
        '-e', 'CLUSTER_HOSTNAME=node1',
        'semitechnologies/weaviate:latest'
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        logger.error(f"Failed to start Weaviate: {result.stderr}")
        return False
    
    # Wait for Weaviate to be ready
    logger.info("Waiting for Weaviate to be ready...")
    for i in range(30):  # Wait up to 30 seconds
        try:
            import requests
            response = requests.get('http://localhost:8080/v1/meta', timeout=5)
            if response.status_code == 200:
                logger.info("✅ Weaviate is ready!")
                return True
        except:
            pass
        time.sleep(1)
    
    logger.error("Weaviate failed to start within 30 seconds")
    return False

def check_weaviate_connection():
    """Check if Weaviate is accessible."""
    try:
        import requests
        response = requests.get('http://localhost:8080/v1/meta', timeout=5)
        return response.status_code == 200
    except:
        return False

def install_dependencies():
    """Install Python dependencies."""
    logger.info("Installing Python dependencies...")
    result = subprocess.run([sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt'], 
                          capture_output=True, text=True)
    if result.returncode != 0:
        logger.error(f"Failed to install dependencies: {result.stderr}")
        return False
    logger.info("✅ Dependencies installed")
    return True

def ingest_pdfs():
    """Ingest PDFs from the data directory."""
    logger.info("Ingesting PDFs from data directory...")
    
    try:
        from ingestion.pipeline import ingest_pdf_directory
        
        result = ingest_pdf_directory(
            "data",
            doc_type="regulation",
            jurisdiction="KR",
            lang="ko"
        )
        
        if "error" in result:
            logger.error(f"PDF ingestion failed: {result['error']}")
            return False
        
        logger.info(f"✅ Ingested {result['files_processed']} PDF files")
        logger.info(f"   Total documents: {result['total_documents']}")
        logger.info(f"   Total chunks: {result['total_chunks']}")
        
        return True
        
    except Exception as e:
        logger.error(f"PDF ingestion failed: {e}")
        return False

def rebuild_metadata_vectors():
    """Rebuild metadata vectors."""
    logger.info("Rebuilding metadata vectors...")
    
    try:
        from ingestion.metadata_vectors import rebuild_all_facet_value_vectors
        
        count = rebuild_all_facet_value_vectors()
        logger.info(f"✅ Rebuilt {count} metadata vectors")
        return True
        
    except Exception as e:
        logger.error(f"Failed to rebuild metadata vectors: {e}")
        return False

def start_api_server(host="0.0.0.0", port=8001):
    """Start the FastAPI server in a subprocess and return its PID."""
    logger.info(f"Starting API server on {host}:{port}...")
    
    try:
        process = subprocess.Popen([
            sys.executable, "-m", "uvicorn", 
            "apps.api.main:app",
            "--host", host,
            "--port", str(port),
            "--log-level", "info"
        ])
        logger.info(f"API server started with PID: {process.pid}")
        return process.pid
        
    except Exception as e:
        logger.error(f"Failed to start API server: {e}")
        return None

def start_chat_gui():
    """Start the Streamlit chat GUI in a subprocess and return its PID."""
    try:
        logger.info("💬 Starting chat GUI...")
        chat_gui_path = os.path.join(project_root, "apps", "chat_gui.py")
        
        process = subprocess.Popen([
            sys.executable, "-m", "streamlit", "run", 
            chat_gui_path,
            "--server.port", "8501",
            "--server.address", "0.0.0.0",
            "--browser.gatherUsageStats", "false"
        ])
        logger.info(f"Chat GUI started with PID: {process.pid}")
        return process.pid
        
    except Exception as e:
        logger.error(f"Failed to start chat GUI: {e}")
        return None

def test_system():
    """Test the system with a sample query."""
    logger.info("Testing system with sample query...")
    
    try:
        import requests
        import json
        
        # Wait a moment for server to be ready
        time.sleep(2)
        
        # Test health endpoint
        response = requests.get(f'http://localhost:8001/health', timeout=10)
        if response.status_code != 200:
            logger.error("Health check failed")
            return False
        
        # Test query endpoint
        query_data = {
            "query": "전자금융거래법 시행령에서 규정하는 내용은 무엇인가요?",
            "lang": "ko"
        }
        
        response = requests.post(
            f'http://localhost:8001/agent/query',
            json=query_data,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            logger.info("✅ System test successful!")
            logger.info(f"   Query: {query_data['query']}")
            logger.info(f"   Response: {result['text'][:100]}...")
            return True
        else:
            logger.error(f"Query test failed: {response.status_code}")
            return False
            
    except Exception as e:
        logger.error(f"System test failed: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Retrieval Agent Startup Script")
    parser.add_argument("--skip-docker", action="store_true", help="Skip Docker/Weaviate setup")
    parser.add_argument("--skip-ingest", action="store_true", help="Skip PDF ingestion")
    parser.add_argument("--skip-vectors", action="store_true", help="Skip metadata vector rebuild")
    parser.add_argument("--skip-test", action="store_true", help="Skip system test")
    parser.add_argument("--api-only", action="store_true", help="Only start the API server")
    parser.add_argument("--chat-only", action="store_true", help="Only start the chat GUI")
    parser.add_argument("--full-stack", action="store_true", help="Start both API server and chat GUI")
    parser.add_argument("--host", default="0.0.0.0", help="API server host")
    parser.add_argument("--port", type=int, default=8001, help="API server port")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose logging")
    parser.add_argument("--stop", action="store_true", help="Stop all running background processes")
    parser.add_argument("--explorer-only", action="store_true", help="Only start the Weaviate Explorer GUI")
    
    args = parser.parse_args()
    
    # Setup logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    setup_root_logger(log_level)
    
    # Handle --stop flag
    if args.stop:
        pid_manager.terminate_all_processes() # Use PIDManager
        pid_manager.force_kill_streamlit() # Ensure streamlit is dead
        return
        
    # Handle --explorer-only flag (just the Weaviate Explorer GUI)
    if args.explorer_only:
        logger.info("Starting Weaviate Explorer GUI...")
        # Create a simplified version of the chat GUI that only shows the explorer
        explorer_script = """
import os
import sys
import streamlit as st

# Set page config must be the first Streamlit command
st.set_page_config(
    page_title="Weaviate Explorer",
    page_icon="🔍",
    layout="wide"
)

# Add project root to Python path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# Import weaviate directly instead of importing from chat_gui
import weaviate

st.title("🔍 Weaviate Explorer")
st.write("This is a standalone explorer for your Weaviate database.")

# Standalone weaviate explorer function
def weaviate_explorer():
    query = st.text_input("Search chunks (leave blank for random):", "")
    n = st.number_input("Number of chunks", min_value=1, max_value=20, value=5)
    try:
        client = weaviate.connect_to_local(host="localhost", port=8080)
        chunk_class = "Chunk"
        if query:
            # Simple BM25 search
            results = client.collections.get(chunk_class).query.bm25(
                query=query,
                limit=n,
                # Get all properties by not specifying return_properties
                include_vector=True
            )
        else:
            # Fetch random/recent chunks
            results = client.collections.get(chunk_class).query.fetch_objects(
                limit=n,
                # Get all properties by not specifying return_properties
                include_vector=True
            )
        
        # Display each chunk with all its properties
        for i, obj in enumerate(results.objects, 1):
            with st.expander(f"Chunk #{i}: {obj.properties.get('chunk_id', 'Unknown ID')}", expanded=True):
                # First show the body text
                if "body" in obj.properties:
                    st.markdown("### Content")
                    st.markdown(f"```\\n{obj.properties['body']}\\n```")
                
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

# Run the explorer function
weaviate_explorer()
"""
        # Write the temporary script
        temp_script_path = os.path.join(project_root, "explorer_temp.py")
        with open(temp_script_path, "w") as f:
            f.write(explorer_script)
            
        # Run the explorer script
        process = subprocess.Popen([
            sys.executable, "-m", "streamlit", "run", 
            temp_script_path,
            "--server.port", "8502",
            "--server.address", "0.0.0.0",
            "--browser.gatherUsageStats", "false"
        ])
        
        if process.pid:
            pid_manager.store_pid("explorer", process.pid)
            logger.info(f"Explorer GUI started with PID: {process.pid}")
            logger.info(f"🔍 Explorer GUI: http://localhost:8502")
            logger.info("Press Ctrl+C to stop.")
            
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                logger.info("Ctrl+C detected. Stopping explorer...")
                pid_manager.terminate_all_processes()
                # Clean up temp file
                if os.path.exists(temp_script_path):
                    os.remove(temp_script_path)
            return
        else:
            logger.error("Failed to start Explorer GUI")
            return

    logger.info("🚀 Starting Retrieval Agent...")
    
    # Install dependencies
    if not install_dependencies():
        sys.exit(1)
    
    # Chat-only mode
    if args.chat_only:
        logger.info("Starting chat GUI...")
        pid = start_chat_gui()
        if pid: pid_manager.store_pid("chat_gui", pid)
        # The script should then block/wait for the GUI, not exit
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Ctrl+C detected. Stopping chat GUI...")
            pid_manager.terminate_all_processes()
        return
    
    # API-only mode
    if args.api_only:
        logger.info("Starting in API-only mode...")
        pid = start_api_server(args.host, args.port)
        if pid: pid_manager.store_pid("api", pid)
        # The script should then block/wait for the API server, not exit
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Ctrl+C detected. Stopping API server...")
            pid_manager.terminate_all_processes()
        return
    
    # Full-stack mode (both API and chat GUI)
    if args.full_stack:
        logger.info("🚀 Starting full-stack mode (API + Chat GUI)...")
        
        # Start API server process
        api_pid = start_api_server(args.host, args.port)
        if api_pid: pid_manager.store_pid("api", api_pid)
        logger.info(f"API server started with PID: {api_pid}")
        
        # Wait for API server to start (optional, but good practice)
        logger.info("⏳ Waiting for API server to start...")
        time.sleep(5)
        
        # Start chat GUI process
        chat_gui_pid = start_chat_gui()
        if chat_gui_pid: pid_manager.store_pid("chat_gui", chat_gui_pid)
        logger.info(f"Chat GUI started with PID: {chat_gui_pid}")

        logger.info("🌐 API Server: http://localhost:8001")
        logger.info("💬 Chat GUI: http://localhost:8501")
        logger.info("Press Ctrl+C to stop both services.")
        
        try:
            # Keep the main script alive so background processes can run
            while True: 
                time.sleep(1) # Keep main thread alive
        except KeyboardInterrupt:
            logger.info("Ctrl+C detected. Stopping services...")
            pid_manager.terminate_all_processes()
        
        return
    
    # Start Weaviate
    weaviate_ready = False
    if not args.skip_docker:
        weaviate_ready = start_weaviate()
    else:
        weaviate_ready = check_weaviate_connection()
        if weaviate_ready:
            logger.info("✅ Weaviate is already running")
        else:
            logger.warning("⚠️  Weaviate is not running - system will work in offline mode")
    
    # Ingest PDFs
    if not args.skip_ingest:
        if not ingest_pdfs():
            logger.warning("⚠️  PDF ingestion failed - continuing anyway")
    
    # Rebuild metadata vectors
    if not args.skip_vectors and weaviate_ready:
        if not rebuild_metadata_vectors():
            logger.warning("⚠️  Metadata vector rebuild failed - continuing anyway")
    
    # Final full-stack start (if no specific mode was chosen)
    logger.info("🚀 Starting final full-stack mode (API + Chat GUI)...")
    logger.info(f"🌐 API Server: http://localhost:{args.port}")
    logger.info(f"   Health: http://localhost:{args.port}/health")
    logger.info(f"   Query: http://localhost:{args.port}/agent/query")
    logger.info(f"   Ingest: http://localhost:{args.port}/ingest/data-directory")
    logger.info(f"   Docs: http://localhost:{args.port}/docs")
    logger.info(f"💬 Chat GUI: http://localhost:8501")
    
    # Start API server process
    api_pid = start_api_server(args.host, args.port)
    if api_pid: pid_manager.store_pid("api", api_pid)
    logger.info(f"API server started with PID: {api_pid}")
    
    # Wait for API server to start (optional, but good practice)
    logger.info("⏳ Waiting for API server to start...")
    time.sleep(5)
    
    # Test system if requested
    if not args.skip_test:
        test_system()
    
    # Start chat GUI process
    chat_gui_pid = start_chat_gui()
    if chat_gui_pid: pid_manager.store_pid("chat_gui", chat_gui_pid)
    logger.info(f"Chat GUI started with PID: {chat_gui_pid}")

    logger.info("Press Ctrl+C to stop both services.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Ctrl+C detected. Stopping services...")
        pid_manager.terminate_all_processes()


if __name__ == "__main__":
    main()
