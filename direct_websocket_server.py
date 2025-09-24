#!/usr/bin/env python3
"""
Run the WebSocket server directly with debug logging.
"""

import os
import sys
import logging
from pathlib import Path
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Project root directory
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Load environment variables
load_dotenv()

def run_websocket_server():
    """Run the WebSocket server directly with debug logging."""
    try:
        import uvicorn
        from apps.api.websocket_server import app
        
        logger.info("Starting WebSocket server with debug logging...")
        uvicorn.run(app, host="0.0.0.0", port=8000, log_level="debug")
    except Exception as e:
        logger.error(f"Error starting WebSocket server: {e}")
        return False

if __name__ == "__main__":
    run_websocket_server()
