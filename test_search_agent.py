#!/usr/bin/env python3
"""
Test script for the search agent with our fixes.
This script tests the actual search functionality with ChromaDB.
"""

import asyncio
import json
import logging
import os
import sys
import uuid
from pathlib import Path
import websockets

# Add the project root to the Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
def load_environment_variables():
    """Load environment variables from .env file."""
    env_path = project_root / '.env'
    if env_path.exists():
        try:
            # Try to use python-dotenv if available
            try:
                from dotenv import load_dotenv
                load_dotenv(env_path)
                print(f"Loaded environment variables from {env_path} using python-dotenv")
            except ImportError:
                # Fall back to manual loading
                with open(env_path, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if not line or line.startswith('#'):
                            continue
                        
                        key, value = line.split('=', 1)
                        key = key.strip()
                        value = value.strip()
                        
                        # Set the environment variable
                        os.environ[key] = value
                print(f"Loaded environment variables from {env_path} manually")
            
            return True
        except Exception as e:
            print(f"Error loading environment variables: {e}")
            return False
    else:
        print(f"Warning: .env file not found at {env_path}")
        return False

# Load environment variables
load_environment_variables()

# Import the graph module to test
from agent.graph import run_graph

async def send_websocket_message(uri, message):
    """Send a message to the WebSocket server and receive the response."""
    try:
        async with websockets.connect(uri) as websocket:
            # Generate a unique query ID
            query_id = str(uuid.uuid4())
            
            # Create message payload
            payload = {
                "type": "query",
                "query_id": query_id,
                "content": message
            }
            
            # Send the message
            logger.info(f"Sending message: {payload}")
            await websocket.send(json.dumps(payload))
            
            # Wait for response
            logger.info("Waiting for response...")
            response = await websocket.recv()
            logger.info(f"Received response: {response}")
            
            # Parse and return the response
            return json.loads(response)
    except Exception as e:
        logger.error(f"Error in WebSocket communication: {e}")
        return {"error": str(e)}

def test_direct_graph():
    """Test the search agent graph directly."""
    logger.info("Testing search agent graph directly...")
    
    # Test queries
    test_queries = [
        "안녕하세요",  # Korean greeting
        "What is in the marketing meeting?",  # English query about marketing
        "Tell me about the sprint meeting"  # English query about sprint
    ]
    
    results = []
    for query in test_queries:
        logger.info(f"Testing query: {query}")
        
        # Run the graph with the query
        result = run_graph(
            query=query,
            time_hint=None,
            lang=None,
            trace_id=str(uuid.uuid4()),
            session_id=str(uuid.uuid4())
        )
        
        # Log the result
        logger.info(f"Result: {result}")
        results.append({
            "query": query,
            "result": result
        })
    
    # Print summary
    print("\n=== Test Results ===")
    for i, result_data in enumerate(results):
        query = result_data["query"]
        result = result_data["result"]
        
        print(f"\nQuery {i+1}: {query}")
        print(f"Response: {result.get('text', 'No text')}")
        print(f"Has context: {result.get('has_context', False)}")
        print(f"Citations: {len(result.get('citations', []))}")
    
    return results

async def test_websocket_server():
    """Test the search agent through the WebSocket server."""
    logger.info("Testing search agent through WebSocket server...")
    
    # WebSocket URI
    uri = "ws://localhost:8000/ws/agent"
    
    # Test queries
    test_queries = [
        "안녕하세요",  # Korean greeting
        "What is in the marketing meeting?",  # English query about marketing
        "Tell me about the sprint meeting"  # English query about sprint
    ]
    
    results = []
    for query in test_queries:
        logger.info(f"Testing query: {query}")
        
        # Send the query to the WebSocket server
        result = await send_websocket_message(uri, query)
        
        # Log the result
        logger.info(f"Result: {result}")
        results.append({
            "query": query,
            "result": result
        })
    
    # Print summary
    print("\n=== WebSocket Test Results ===")
    for i, result_data in enumerate(results):
        query = result_data["query"]
        result = result_data["result"]
        
        print(f"\nQuery {i+1}: {query}")
        print(f"Response: {result.get('text', 'No text')}")
        print(f"Citations: {len(result.get('citations', []))}")
    
    return results

async def main():
    """Main function to run the tests."""
    # Test the search agent graph directly
    direct_results = test_direct_graph()
    
    # Test the search agent through the WebSocket server
    websocket_results = await test_websocket_server()
    
    # Compare results
    print("\n=== Comparison ===")
    for i in range(min(len(direct_results), len(websocket_results))):
        direct_query = direct_results[i]["query"]
        websocket_query = websocket_results[i]["query"]
        
        direct_text = direct_results[i]["result"].get("text", "No text")
        websocket_text = websocket_results[i]["result"].get("text", "No text")
        
        print(f"\nQuery: {direct_query}")
        print(f"Direct response: {direct_text[:100]}..." if len(direct_text) > 100 else direct_text)
        print(f"WebSocket response: {websocket_text[:100]}..." if len(websocket_text) > 100 else websocket_text)

if __name__ == "__main__":
    asyncio.run(main())
