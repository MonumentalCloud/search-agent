#!/usr/bin/env python3
"""
Fix environment variable loading issues.
"""

import os
import sys
import logging
from pathlib import Path
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def fix_env_loading():
    """Fix environment variable loading issues."""
    # Get the project root directory
    project_root = Path(__file__).parent.absolute()
    
    # Path to the .env file
    env_file = project_root / ".env"
    
    if not env_file.exists():
        logger.error(f".env file not found at {env_file}")
        return False
    
    # Load the .env file
    logger.info(f"Loading environment variables from {env_file}")
    load_dotenv(env_file)
    
    # Check if the environment variables are loaded correctly
    openrouter_api_key = os.environ.get("OPENROUTER_API_KEY")
    bge_api_key = os.environ.get("BGE_API_KEY")
    
    if not openrouter_api_key or openrouter_api_key.startswith("${"):
        logger.error("OPENROUTER_API_KEY not loaded correctly")
        return False
    
    if not bge_api_key or bge_api_key.startswith("${"):
        logger.error("BGE_API_KEY not loaded correctly")
        return False
    
    # Print the loaded environment variables (with masking for security)
    logger.info(f"OPENROUTER_API_KEY: {openrouter_api_key[:10]}...")
    logger.info(f"BGE_API_KEY: {bge_api_key[:10]}...")
    
    # Check configs/load.py to ensure it's loading environment variables correctly
    load_py = project_root / "configs" / "load.py"
    if not load_py.exists():
        logger.error(f"configs/load.py not found at {load_py}")
        return False
    
    with open(load_py, "r") as f:
        load_py_content = f.read()
    
    # Check if the file contains code to expand environment variables
    if "os.environ.get" not in load_py_content and "os.getenv" not in load_py_content:
        logger.warning("configs/load.py may not be expanding environment variables correctly")
    
    # Test the environment variable expansion in configs/load.py
    sys.path.insert(0, str(project_root))
    try:
        from configs.load import get_default_llm, get_default_embeddings
        
        # Test LLM configuration
        llm_config = get_default_llm()
        logger.info(f"LLM API key: {llm_config.api_key[:10]}..." if hasattr(llm_config, "api_key") else "LLM API key not available")
        
        # Test embeddings configuration
        embeddings = get_default_embeddings()
        logger.info(f"Embeddings API key: {embeddings.api_key[:10]}..." if hasattr(embeddings, "api_key") else "Embeddings API key not available")
        
        return True
    except Exception as e:
        logger.error(f"Error testing configs/load.py: {e}")
        return False

if __name__ == "__main__":
    if fix_env_loading():
        logger.info("Environment variable loading fixed successfully")
    else:
        logger.error("Failed to fix environment variable loading")
        sys.exit(1)
