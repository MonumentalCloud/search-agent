#!/usr/bin/env python3
"""
Fix the API server to use the correct embedding dimensions.
"""

import os
import sys
import logging
import re
from pathlib import Path
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Project root directory
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Load environment variables
load_dotenv()

def fix_api_server():
    """Fix the API server to use the correct embedding dimensions."""
    file_path = project_root / "apps" / "api" / "main.py"
    
    if not file_path.exists():
        logger.error(f"File not found: {file_path}")
        return False
    
    try:
        # Read the file
        with open(file_path, "r") as f:
            content = f.read()
        
        # Add import for get_default_embeddings if it's not already there
        if "from configs.load import get_default_embeddings" not in content:
            if "from configs.load import" in content:
                content = re.sub(
                    r"from configs.load import (.+)",
                    r"from configs.load import \1, get_default_embeddings",
                    content
                )
            else:
                content = content.replace(
                    "import logging",
                    "import logging\nfrom configs.load import get_default_embeddings",
                    1
                )
        
        # Replace SentenceTransformer usage with get_default_embeddings
        if "from sentence_transformers import SentenceTransformer" in content:
            content = content.replace(
                "from sentence_transformers import SentenceTransformer",
                "# from sentence_transformers import SentenceTransformer"
            )
        
        # Replace model initialization
        if "model = SentenceTransformer(" in content:
            content = content.replace(
                "model = SentenceTransformer(",
                "# model = SentenceTransformer("
            )
        
        # Replace embedding generation
        if "embedding = model.encode(" in content:
            content = content.replace(
                "embedding = model.encode(",
                "embeddings = get_default_embeddings()\n    embedding = embeddings.embed_query("
            )
        
        # Write the updated content back to the file
        with open(file_path, "w") as f:
            f.write(content)
        
        logger.info(f"Updated {file_path}")
        return True
    
    except Exception as e:
        logger.error(f"Error updating {file_path}: {e}")
        return False

def main():
    """Main function."""
    logger.info("Starting API server fix")
    
    # Fix the API server
    if fix_api_server():
        logger.info("Successfully fixed API server")
    else:
        logger.error("Failed to fix API server")
    
    logger.info("API server fix completed")

if __name__ == "__main__":
    main()
