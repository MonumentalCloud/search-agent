#!/usr/bin/env python3
"""
Run the SSE server for the search agent.
"""

import logging
import os
import sys
from pathlib import Path

import uvicorn
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join('logs', 'sse_server.log')),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Project root directory
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Load environment variables
env_path = project_root / '.env'
if env_path.exists():
    load_dotenv(dotenv_path=env_path)
    logger.info(f"Loaded environment variables from {env_path}")
else:
    logger.warning(f"No .env file found at {env_path}")

def check_port(port):
    """Check if the port is in use and kill the process if necessary."""
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.bind(("0.0.0.0", port))
        s.close()
        return True
    except socket.error:
        logger.warning(f"Port {port} is already in use")
        
        # Find and kill the process using the port
        try:
            import psutil
            for proc in psutil.process_iter(['pid', 'name', 'connections']):
                for conn in proc.info.get('connections', []):
                    if conn.laddr.port == port:
                        logger.info(f"Killing process {proc.info['pid']} ({proc.info['name']}) using port {port}")
                        psutil.Process(proc.info['pid']).terminate()
                        return True
        except (ImportError, psutil.Error) as e:
            logger.error(f"Error killing process on port {port}: {e}")
        
        return False

if __name__ == "__main__":
    logger.info("Starting SSE server")
    
    # Check if port 8001 is available
    if check_port(8001):
        # Import the SSE server
        from apps.api.sse_server import app
        
        # Run the server on port 8001 instead of 8000
        uvicorn.run(app, host="0.0.0.0", port=8001, log_level="debug")
    else:
        logger.error("Failed to start SSE server: port 8001 is in use")
        sys.exit(1)
