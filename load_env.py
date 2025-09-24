#!/usr/bin/env python3
"""
Load environment variables from .env file
"""

import os
import sys
import logging
from pathlib import Path
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def load_environment():
    """Load environment variables from .env file."""
    # Get the project root directory
    project_root = Path(__file__).parent.absolute()
    
    # Path to .env file
    env_path = project_root / '.env'
    
    # Check if .env file exists
    if not env_path.exists():
        logger.warning(f".env file not found at {env_path}")
        logger.info("Please create a .env file with your API keys (see env_template.txt)")
        return False
    
    # Load environment variables from .env file
    load_dotenv(env_path)
    
    # Check if required environment variables are set
    required_vars = ['OPENROUTER_API_KEY', 'BGE_API_KEY']
    missing_vars = [var for var in required_vars if not os.environ.get(var)]
    
    if missing_vars:
        logger.warning(f"Missing required environment variables: {', '.join(missing_vars)}")
        logger.info("Please add these variables to your .env file")
        return False
    
    logger.info("Environment variables loaded successfully")
    return True

if __name__ == "__main__":
    if load_environment():
        print("Environment variables loaded successfully")
        print("\nAvailable environment variables:")
        print(f"OPENROUTER_API_KEY: {'✓ Set' if os.environ.get('OPENROUTER_API_KEY') else '✗ Not set'}")
        print(f"BGE_API_KEY: {'✓ Set' if os.environ.get('BGE_API_KEY') else '✗ Not set'}")
    else:
        print("Failed to load environment variables")
        sys.exit(1)
