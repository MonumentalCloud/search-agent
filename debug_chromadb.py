#!/usr/bin/env python3
"""
Debug script to identify chromadb import issues.
"""

import os
import sys
import logging
import traceback
import importlib
import subprocess
from pathlib import Path

# Configure logging
logs_dir = Path(__file__).parent / "logs"
logs_dir.mkdir(exist_ok=True)
log_file = logs_dir / "chromadb_debug.log"

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)
logger.info(f"Starting chromadb debug with logging to {log_file}")

# Print Python environment info
logger.info(f"Python executable: {sys.executable}")
logger.info(f"Python version: {sys.version}")
logger.info(f"Current directory: {os.getcwd()}")
logger.info(f"Python path: {sys.path}")

# Check if chromadb is installed
try:
    result = subprocess.run([sys.executable, "-m", "pip", "list"], 
                           capture_output=True, text=True, check=True)
    logger.info(f"Installed packages:\n{result.stdout}")
    
    # Look for chromadb in the output
    if "chromadb" in result.stdout:
        logger.info("chromadb is listed in installed packages")
    else:
        logger.warning("chromadb is NOT listed in installed packages")
except Exception as e:
    logger.error(f"Error checking installed packages: {e}")

# Try importing chromadb directly
try:
    import chromadb
    logger.info(f"Successfully imported chromadb directly: version {chromadb.__version__}")
    logger.info(f"chromadb path: {chromadb.__file__}")
except ImportError as e:
    logger.error(f"Failed to import chromadb directly: {e}")
    logger.error(f"Traceback: {traceback.format_exc()}")

# Try importing chromadb through importlib
try:
    chromadb_module = importlib.import_module("chromadb")
    logger.info(f"Successfully imported chromadb through importlib: version {chromadb_module.__version__}")
except ImportError as e:
    logger.error(f"Failed to import chromadb through importlib: {e}")
    logger.error(f"Traceback: {traceback.format_exc()}")

# Try importing the ChromaClient from our adapters
try:
    from adapters.chroma_adapter import ChromaClient
    logger.info("Successfully imported ChromaClient from adapters.chroma_adapter")
    
    # Try creating a ChromaClient instance
    try:
        client = ChromaClient()
        logger.info("Successfully created ChromaClient instance")
    except Exception as e:
        logger.error(f"Failed to create ChromaClient instance: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        
except ImportError as e:
    logger.error(f"Failed to import ChromaClient from adapters.chroma_adapter: {e}")
    logger.error(f"Traceback: {traceback.format_exc()}")

# Try importing the websocket_server module
try:
    from apps.api import websocket_server
    logger.info("Successfully imported websocket_server module")
except ImportError as e:
    logger.error(f"Failed to import websocket_server module: {e}")
    logger.error(f"Traceback: {traceback.format_exc()}")

# Try running the websocket server in a subprocess to capture its exact error
try:
    logger.info("Attempting to start websocket_server in a subprocess...")
    result = subprocess.run(
        [sys.executable, "-m", "uvicorn", "apps.api.websocket_server:app", "--host", "0.0.0.0", "--port", "8002", "--log-level", "debug"],
        capture_output=True,
        text=True,
        timeout=5  # Only run for 5 seconds max
    )
    logger.info(f"Subprocess stdout:\n{result.stdout}")
    logger.info(f"Subprocess stderr:\n{result.stderr}")
except subprocess.TimeoutExpired as e:
    logger.info("Subprocess timed out (this is expected if server started successfully)")
    if hasattr(e, 'stdout') and e.stdout:
        logger.info(f"Subprocess stdout before timeout:\n{e.stdout}")
    if hasattr(e, 'stderr') and e.stderr:
        logger.info(f"Subprocess stderr before timeout:\n{e.stderr}")
except Exception as e:
    logger.error(f"Error running websocket_server subprocess: {e}")
    logger.error(f"Traceback: {traceback.format_exc()}")

logger.info("chromadb debug complete")
