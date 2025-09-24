#!/usr/bin/env python3
"""
Debug WebSocket server with enhanced error logging.
"""

import os
import sys
import logging
from pathlib import Path

# Configure logging
logs_dir = Path(__file__).parent / "logs"
logs_dir.mkdir(exist_ok=True)
log_file = logs_dir / "websocket_debug.log"

# Set up root logger with both file and console output
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler(sys.stdout)
    ]
)

# Get the root logger and set its level to DEBUG
root_logger = logging.getLogger()
root_logger.setLevel(logging.DEBUG)

# Set up specific loggers we want to debug
for logger_name in ["uvicorn", "fastapi", "websockets", "chromadb", "adapters", "agent", "ingestion"]:
    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.DEBUG)

logger = logging.getLogger(__name__)
logger.info(f"Starting WebSocket server with debug logging to {log_file}")

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Print Python path and environment info
logger.info(f"Python executable: {sys.executable}")
logger.info(f"Python version: {sys.version}")
logger.info(f"Python path: {sys.path}")

# Try importing key modules before starting server
try:
    import chromadb
    logger.info(f"ChromaDB version: {chromadb.__version__}")
    import fastapi
    logger.info(f"FastAPI version: {fastapi.__version__}")
    import uvicorn
    logger.info(f"Uvicorn version: {uvicorn.__version__}")
    from adapters.chroma_adapter import ChromaClient
    logger.info("Successfully imported ChromaClient")
except ImportError as e:
    logger.error(f"Import error: {e}")
    sys.exit(1)

# Start the WebSocket server with exception handling
try:
    logger.info("Starting WebSocket server...")
    import uvicorn
    uvicorn.run(
        "apps.api.websocket_server:app",
        host="0.0.0.0",
        port=8000,
        log_level="debug",
        reload=True,
        reload_dirs=[str(project_root)]
    )
except Exception as e:
    logger.exception(f"Failed to start WebSocket server: {e}")
    sys.exit(1)
