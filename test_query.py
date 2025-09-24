#!/usr/bin/env python3
"""
Test the search agent with a query.
"""

import os
import sys
import logging
import json
import uuid
import time
from pathlib import Path
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Load environment variables
load_dotenv()

def test_query(query: str = "What are the meeting dates?", session_id: str = None):
    """Test the search agent with a query."""
    try:
        # Import the agent module
        from agent.graph import run_graph
        
        # Generate a unique session ID if not provided
        if not session_id:
            session_id = f"test_session_{uuid.uuid4().hex[:8]}"
        
        # Generate a unique trace ID
        trace_id = str(uuid.uuid4())
        
        logger.info(f"Running query: '{query}' with session_id: {session_id}")
        
        # Run the query
        start_time = time.time()
        result = run_graph(
            query=query,
            time_hint=None,
            lang=None,
            trace_id=trace_id,
            session_id=session_id
        )
        end_time = time.time()
        
        # Log the result
        logger.info(f"Query completed in {end_time - start_time:.2f} seconds")
        logger.info(f"Answer: {result.get('text', '')[:100]}...")
        logger.info(f"Citations: {len(result.get('citations', []))} items")
        
        # Print the first citation if available
        if result.get("citations") and len(result.get("citations")) > 0:
            logger.info(f"First citation: {result['citations'][0]}")
        
        return result
    except Exception as e:
        logger.error(f"Error running query: {e}")
        return {"error": str(e)}

def main():
    """Main function."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Test the search agent with a query")
    parser.add_argument("--query", "-q", default="What are the meeting dates?", help="Query to test")
    parser.add_argument("--session", "-s", help="Session ID (optional)")
    
    args = parser.parse_args()
    
    # Run the query
    result = test_query(query=args.query, session_id=args.session)
    
    # Print the result
    print(json.dumps(result, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
