#!/usr/bin/env python3
"""
Test the API server with a query.
"""

import os
import sys
import logging
import json
import uuid
import time
import requests
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

def test_api_query(query: str = "What are the meeting dates?", session_id: str = None):
    """Test the API server with a query."""
    try:
        # Generate a unique session ID if not provided
        if not session_id:
            session_id = f"test_session_{uuid.uuid4().hex[:8]}"
        
        # Generate a unique query ID
        query_id = str(uuid.uuid4())
        
        logger.info(f"Sending query to API: '{query}' with session_id: {session_id}")
        
        # Send the query to the API
        start_time = time.time()
        response = requests.post(
            "http://localhost:8001/agent/query",
            json={
                "query": query,
                "query_id": query_id,
                "session_id": session_id
            },
            timeout=60
        )
        end_time = time.time()
        
        # Check if the request was successful
        if response.status_code == 200:
            result = response.json()
            
            # Log the result
            logger.info(f"Query completed in {end_time - start_time:.2f} seconds")
            logger.info(f"Answer: {result.get('text', '')[:100]}...")
            logger.info(f"Citations: {len(result.get('citations', []))} items")
            
            # Print the first citation if available
            if result.get("citations") and len(result.get("citations")) > 0:
                logger.info(f"First citation: {result['citations'][0]}")
            
            return result
        else:
            logger.error(f"API request failed with status code {response.status_code}")
            logger.error(f"Response: {response.text}")
            return {"error": f"API request failed with status code {response.status_code}"}
    except Exception as e:
        logger.error(f"Error sending query to API: {e}")
        return {"error": str(e)}

def main():
    """Main function."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Test the API server with a query")
    parser.add_argument("--query", "-q", default="What are the meeting dates?", help="Query to test")
    parser.add_argument("--session", "-s", help="Session ID (optional)")
    
    args = parser.parse_args()
    
    # Run the query
    result = test_api_query(query=args.query, session_id=args.session)
    
    # Print the result
    print(json.dumps(result, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
