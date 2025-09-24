#!/usr/bin/env python3
"""
Test WebSocket connection to the server.
"""

import asyncio
import websockets
import json
import logging
import sys

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_websocket_connection():
    """Test WebSocket connection to the server."""
    uri = "ws://localhost:8000/ws/agent"
    
    try:
        logger.info(f"Connecting to {uri}...")
        async with websockets.connect(uri) as websocket:
            logger.info("Connected to WebSocket server")
            
            # Send a test message
            test_message = {
                "type": "query",
                "query_id": "test_123",
                "content": "What are the meeting dates?",
                "session_id": "test_session"
            }
            
            logger.info(f"Sending message: {test_message}")
            await websocket.send(json.dumps(test_message))
            
            # Wait for a response
            logger.info("Waiting for response...")
            response = await asyncio.wait_for(websocket.recv(), timeout=30.0)
            
            # Parse and display the response
            response_data = json.loads(response)
            logger.info(f"Received response: {json.dumps(response_data, indent=2)}")
            
            return True
    except websockets.exceptions.ConnectionClosed as e:
        logger.error(f"WebSocket connection closed: {e}")
        return False
    except asyncio.TimeoutError:
        logger.error("Timed out waiting for response")
        return False
    except Exception as e:
        logger.error(f"Error connecting to WebSocket: {e}")
        return False

if __name__ == "__main__":
    try:
        result = asyncio.run(test_websocket_connection())
        sys.exit(0 if result else 1)
    except KeyboardInterrupt:
        logger.info("Test interrupted by user")
        sys.exit(1)