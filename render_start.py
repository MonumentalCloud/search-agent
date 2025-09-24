#!/usr/bin/env python3
"""
Render.com startup script for the search agent.
This script handles the startup process for Render deployment.
"""

import os
import sys
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Project root directory
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Set environment variables for Render
os.environ.setdefault('PYTHONPATH', str(project_root))
os.environ.setdefault('CONFIG_PATH', 'configs/default.yaml')

# Load environment variables from .env if it exists
env_path = project_root / '.env'
if env_path.exists():
    from dotenv import load_dotenv
    load_dotenv(dotenv_path=env_path)
    logger.info(f"Loaded environment variables from {env_path}")
else:
    logger.warning(f"No .env file found at {env_path}")

def main():
    """Main startup function for Render deployment."""
    logger.info("Starting search agent on Render...")
    
    # Get port from Render environment
    port = int(os.environ.get('PORT', 8000))
    logger.info(f"Using port: {port}")
    
    # Import and run the SSE server
    try:
        logger.info("Importing SSE server...")
        from apps.api.sse_server import app
        import uvicorn
        
        logger.info(f"Starting server on port {port}")
        uvicorn.run(
            app, 
            host="0.0.0.0", 
            port=port, 
            log_level="info",
            access_log=True
        )
    except ImportError as e:
        logger.error(f"Import error: {e}")
        logger.error("Available modules:")
        import pkgutil
        for importer, modname, ispkg in pkgutil.walk_packages(path=['apps'], prefix='apps.'):
            logger.error(f"  {modname}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Failed to start server: {e}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)

if __name__ == "__main__":
    main()
