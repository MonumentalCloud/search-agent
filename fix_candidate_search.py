#!/usr/bin/env python3
"""
Fix the candidate_search_chroma.py file to use the correct embedding dimensions.
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

def fix_candidate_search_chroma():
    """Fix the candidate_search_chroma.py file to use the correct embedding dimensions."""
    file_path = project_root / "agent" / "nodes" / "candidate_search_chroma.py"
    
    if not file_path.exists():
        logger.error(f"File not found: {file_path}")
        return False
    
    try:
        # Read the file
        with open(file_path, "r") as f:
            content = f.read()
        
        # Replace the hybrid_search call with a direct call to soft_filters
        if "client.hybrid_search(" in content:
            # Find the hybrid_search block and replace it
            hybrid_search_pattern = r"client\.hybrid_search\(\s*query=search_query,\s*alpha=search_alpha,\s*limit=search_limit,\s*where=None\s*\)"
            
            replacement = """apply_soft_filters(
                        collection=collection,
                        query=search_query,
                        facets={},
                        alpha=search_alpha,
                        limit=search_limit
                    )"""
            
            content = re.sub(hybrid_search_pattern, replacement, content)
        
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
    logger.info("Starting candidate search fix")
    
    # Fix the candidate_search_chroma.py file
    if fix_candidate_search_chroma():
        logger.info("Successfully fixed candidate_search_chroma.py")
    else:
        logger.error("Failed to fix candidate_search_chroma.py")
    
    logger.info("Candidate search fix completed")

if __name__ == "__main__":
    main()
