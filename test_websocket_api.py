#!/usr/bin/env python3
"""
Test the WebSocket API with the Genos API embedder.
"""

import websocket
import json
import uuid
import threading
import time
import sys
import logging
from pathlib import Path
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

def on_message(ws, message):
    """Handle incoming WebSocket messages."""
    logger.info(f"Received: {message}")
    
    try:
        data = json.loads(message)
        if data.get("type") == "answer":
            logger.info(f"Answer received: {data.get('text', '')[:100]}...")
            logger.info(f"Citations: {len(data.get('citations', []))} items")
            
            # Print the first citation if available
            if data.get("citations") and len(data.get("citations")) > 0:
                logger.info(f"First citation: {data['citations'][0]}")
    except Exception as e:
        logger.error(f"Error processing message: {e}")

def on_error(ws, error):
    """Handle WebSocket errors."""
    logger.error(f"Error: {error}")

def on_close(ws, close_status_code, close_msg):
    """Handle WebSocket connection closure."""
    logger.info(f"Connection closed: {close_status_code} - {close_msg}")

def on_open(ws):
    """Handle WebSocket connection opening."""
    logger.info("Connection opened")
    
    # Generate a unique query ID
    query_id = str(uuid.uuid4())
    session_id = "test_session_" + str(uuid.uuid4())[:8]
    
    # Create a message
    message = {
        "type": "query",
        "query_id": query_id,
        "content": "What are the meeting dates?",
        "session_id": session_id
    }
    
    # Send the message
    logger.info(f"Sending query: {message}")
    ws.send(json.dumps(message))
    logger.info("Query sent")

def main():
    """Main function to test the WebSocket API."""
    # Enable WebSocket trace
    websocket.enableTrace(True)
    
    # Connect to the WebSocket server
    ws = websocket.WebSocketApp("ws://localhost:8000/ws/agent",
                              on_open=on_open,
                              on_message=on_message,
                              on_error=on_error,
                              on_close=on_close)
    
    # Start the WebSocket connection in a separate thread
    wst = threading.Thread(target=ws.run_forever)
    wst.daemon = True
    wst.start()
    
    # Wait for the specified time or until user interrupts
    try:
        timeout = 30  # seconds
        logger.info(f"Waiting for responses for {timeout} seconds...")
        time.sleep(timeout)
    except KeyboardInterrupt:
        pass
    
    # Close the WebSocket connection
    ws.close()
    logger.info("Test completed")

if __name__ == "__main__":
    main()
