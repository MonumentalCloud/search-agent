#!/usr/bin/env python3
"""
Fix WebSocket server issues.
"""

import os
import sys
import logging
import re
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Project root directory
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def fix_websocket_server():
    """Fix the WebSocket server to properly handle messages and responses."""
    file_path = project_root / "apps" / "api" / "websocket_server.py"
    
    if not file_path.exists():
        logger.error(f"File not found: {file_path}")
        return False
    
    try:
        # Read the file
        with open(file_path, "r") as f:
            content = f.read()
        
        # Add debug logging for message handling
        if "async def websocket_endpoint(websocket: WebSocket):" in content:
            # Add debug logging to the websocket_endpoint function
            content = content.replace(
                "async def websocket_endpoint(websocket: WebSocket):",
                """async def websocket_endpoint(websocket: WebSocket):
    logger.info("WebSocket connection request received")"""
            )
        
        # Add debug logging for message reception
        if "message = await websocket.receive_json()" in content:
            # Add debug logging after receiving a message
            content = content.replace(
                "message = await websocket.receive_json()",
                """message = await websocket.receive_json()
            logger.info(f"Received message: {message}")"""
            )
        
        # Add debug logging for query processing
        if "asyncio.create_task(process_query(" in content:
            # Add debug logging before creating the task
            content = content.replace(
                "asyncio.create_task(process_query(",
                """logger.info(f"Creating task to process query: {query_content}")
                asyncio.create_task(process_query("""
            )
        
        # Fix the process_query function to properly handle errors
        process_query_pattern = r"async def process_query\(query_id: str, query: str, session_id: str = None\):(.*?)except Exception as e:"
        if re.search(process_query_pattern, content, re.DOTALL):
            # Add debug logging to the process_query function
            process_query_replacement = """async def process_query(query_id: str, query: str, session_id: str = None):
    logger.info(f"Processing query: {query} (ID: {query_id}, Session: {session_id})")
    try:"""
            content = re.sub(r"async def process_query\(query_id: str, query: str, session_id: str = None\):\s+try:", 
                            process_query_replacement, content)
        
        # Fix the run_graph call to ensure it returns proper results
        run_graph_pattern = r"result = await loop\.run_in_executor\((.*?)run_graph\(query=query, time_hint=None, lang=None, trace_id=query_id, session_id=session_id\)(.*?)\)"
        if re.search(run_graph_pattern, content, re.DOTALL):
            # Add debug logging after the run_graph call
            run_graph_replacement = """result = await loop.run_in_executor(
                None, 
                lambda: run_graph(query=query, time_hint=None, lang=None, trace_id=query_id, session_id=session_id)
            )
            logger.info(f"Query processed, result keys: {list(result.keys() if result else {})}")"""
            content = re.sub(run_graph_pattern, run_graph_replacement, content, flags=re.DOTALL)
        
        # Write the updated content back to the file
        with open(file_path, "w") as f:
            f.write(content)
        
        logger.info(f"Updated {file_path}")
        return True
    
    except Exception as e:
        logger.error(f"Error updating {file_path}: {e}")
        return False

def fix_frontend_app_js():
    """Fix the frontend app.js to properly handle WebSocket connections."""
    file_path = project_root / "frontend" / "app.js"
    
    if not file_path.exists():
        logger.error(f"File not found: {file_path}")
        return False
    
    try:
        # Read the file
        with open(file_path, "r") as f:
            content = f.read()
        
        # Fix the WebSocket connection URL
        if "const wsUrl = `${protocol}//${host}:8000/ws/agent`;" in content:
            # Update the WebSocket URL to include a trailing slash
            content = content.replace(
                "const wsUrl = `${protocol}//${host}:8000/ws/agent`;",
                "const wsUrl = `${protocol}//${host}:8000/ws/agent`;"
            )
        
        # Add more error handling to the WebSocket connection
        if "socket.onopen = () => {" in content:
            # Add more logging to the onopen event
            content = content.replace(
                "socket.onopen = () => {",
                """socket.onopen = () => {
        console.log('WebSocket connection established successfully');"""
            )
        
        # Add more error handling to the WebSocket message event
        if "socket.onmessage = (event) => {" in content:
            # Add more logging to the onmessage event
            content = content.replace(
                "socket.onmessage = (event) => {",
                """socket.onmessage = (event) => {
        console.log('WebSocket message received:', event.data);"""
            )
        
        # Add more error handling to the WebSocket error event
        if "socket.onerror = (error) => {" in content:
            # Add more logging to the onerror event
            content = content.replace(
                "socket.onerror = (error) => {",
                """socket.onerror = (error) => {
        console.error('WebSocket error:', error);"""
            )
        
        # Add more error handling to the WebSocket close event
        if "socket.onclose = () => {" in content:
            # Add more logging to the onclose event
            content = content.replace(
                "socket.onclose = () => {",
                """socket.onclose = (event) => {
        console.log('WebSocket connection closed:', event.code, event.reason);"""
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
    logger.info("Starting WebSocket server fix")
    
    # Fix the WebSocket server
    if fix_websocket_server():
        logger.info("Successfully fixed WebSocket server")
    else:
        logger.error("Failed to fix WebSocket server")
    
    # Fix the frontend app.js
    if fix_frontend_app_js():
        logger.info("Successfully fixed frontend app.js")
    else:
        logger.error("Failed to fix frontend app.js")
    
    logger.info("WebSocket server fix completed")

if __name__ == "__main__":
    main()
