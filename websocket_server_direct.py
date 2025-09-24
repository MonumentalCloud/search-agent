#!/usr/bin/env python3
"""
Direct WebSocket server implementation that imports the actual app.
"""

import os
import sys
import logging
from pathlib import Path

# Configure logging
logs_dir = Path(__file__).parent / "logs"
logs_dir.mkdir(exist_ok=True)
log_file = logs_dir / "websocket_direct.log"

# Set up logging
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
logger.info(f"Starting direct WebSocket server with logging to {log_file}")

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Print Python path and environment info
logger.info(f"Python executable: {sys.executable}")
logger.info(f"Python version: {sys.version}")
logger.info(f"Python path: {sys.path}")

# Try importing chromadb directly
try:
    import chromadb
    logger.info(f"ChromaDB version: {chromadb.__version__}")
    logger.info(f"ChromaDB path: {chromadb.__file__}")
except ImportError as e:
    logger.error(f"Failed to import chromadb: {e}")
    sys.exit(1)

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    env_path = Path('.env')
    if env_path.exists():
        logger.info(f"Loading environment variables from {env_path.absolute()}")
        load_dotenv(env_path)
        
        # Check if required environment variables are set
        required_vars = ['OPENROUTER_API_KEY', 'BGE_API_KEY']
        for var in required_vars:
            value = os.environ.get(var)
            masked_value = value[:10] + '...' if value and len(value) > 10 else 'Not set'
            logger.info(f"  {var}: {masked_value}")
    else:
        logger.error(f"Error: .env file not found at {env_path.absolute()}")
        sys.exit(1)
except Exception as e:
    logger.error(f"Error loading environment variables: {e}")
    sys.exit(1)

# Try importing the actual websocket_server app
try:
    from apps.api.websocket_server import app
    logger.info("Successfully imported websocket_server app")
except ImportError as e:
    logger.error(f"Failed to import websocket_server app: {e}")
    sys.exit(1)

# Start the server
if __name__ == "__main__":
    try:
        import uvicorn
        logger.info("Starting WebSocket server on port 8000...")
        uvicorn.run(app, host="0.0.0.0", port=8000, log_level="debug")
    except Exception as e:
        logger.exception(f"Failed to start WebSocket server: {e}")
        sys.exit(1)
