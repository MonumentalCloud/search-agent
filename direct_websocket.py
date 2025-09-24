#!/usr/bin/env python3
"""
Direct WebSocket server script that bypasses uvicorn's reloading mechanism.
"""

import os
import sys
import logging
from pathlib import Path

# Configure logging
logs_dir = Path(__file__).parent / "logs"
logs_dir.mkdir(exist_ok=True)
log_file = logs_dir / "direct_websocket.log"

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
except ImportError as e:
    logger.error(f"Failed to import chromadb: {e}")
    sys.exit(1)

# Create a simple FastAPI app for testing
from fastapi import FastAPI, WebSocket
from fastapi.responses import JSONResponse

app = FastAPI()

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.websocket("/ws/test")
async def websocket_test(websocket: WebSocket):
    await websocket.accept()
    await websocket.send_json({"message": "Connected to test WebSocket"})
    
    try:
        while True:
            data = await websocket.receive_text()
            await websocket.send_json({
                "message": "Echo",
                "data": data
            })
    except Exception as e:
        logger.exception(f"WebSocket error: {e}")

# Start the server directly
if __name__ == "__main__":
    try:
        import uvicorn
        logger.info("Starting direct WebSocket server on port 8000...")
        uvicorn.run(app, host="0.0.0.0", port=8000, log_level="debug")
    except Exception as e:
        logger.exception(f"Failed to start WebSocket server: {e}")
        sys.exit(1)
