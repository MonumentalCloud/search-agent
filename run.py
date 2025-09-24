#!/usr/bin/env python3
"""
Run the search agent with Server-Sent Events (SSE) implementation.
"""

import argparse
import logging
import os
import signal
import sys
from pathlib import Path

import uvicorn
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join('logs', 'search_agent.log')),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Project root directory
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Load environment variables
env_path = project_root / '.env'
if env_path.exists():
    load_dotenv(dotenv_path=env_path)
    logger.info(f"Loaded environment variables from {env_path}")
else:
    logger.warning(f"No .env file found at {env_path}")

def check_port_available(port):
    """Check if the port is available."""
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.bind(("0.0.0.0", port))
        s.close()
        return True
    except socket.error:
        logger.warning(f"Port {port} is already in use")
        return False

def kill_process_on_port(port):
    """Attempt to kill any process using the specified port."""
    try:
        import subprocess
        result = subprocess.run(['lsof', '-i', f':{port}'], 
                               capture_output=True, text=True)
        
        if result.stdout:
            # Extract PIDs from lsof output
            lines = result.stdout.strip().split('\n')[1:]  # Skip header
            pids = []
            for line in lines:
                parts = line.split()
                if len(parts) > 1:
                    pids.append(parts[1])
            
            # Kill processes
            if pids:
                pids_str = ' '.join(pids)
                logger.info(f"Killing processes using port {port}: {pids_str}")
                subprocess.run(['kill', '-9'] + pids, 
                              capture_output=True, text=True)
                return True
        return False
    except Exception as e:
        logger.error(f"Error killing process on port {port}: {e}")
        return False

def kill_processes_on_ports(ports):
    """Kill processes on multiple ports."""
    for port in ports:
        if not check_port_available(port):
            logger.warning(f"Port {port} is in use, attempting to free it")
            if kill_process_on_port(port):
                logger.info(f"Successfully freed port {port}")
            else:
                logger.warning(f"Failed to free port {port} automatically")

def stop_server():
    """Stop any running server instances."""
    logger.info("Stopping any running server instances...")
    kill_processes_on_ports([8000, 8001])
    logger.info("Server instances stopped.")
    return True

if __name__ == "__main__":
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Run the search agent with SSE implementation")
    parser.add_argument("--stop", action="store_true", help="Stop any running server instances")
    parser.add_argument("--port", type=int, default=8001, help="Port to run the server on (default: 8001)")
    args = parser.parse_args()
    
    # Define the port to use
    PORT = args.port
    
    # If --stop flag is provided, stop the server and exit
    if args.stop:
        stop_server()
        sys.exit(0)
    
    logger.info(f"Starting search agent with SSE on port {PORT}")
    
    # Kill any processes on ports 8000 and 8001
    kill_processes_on_ports([8000, 8001])
    
    # Final check to ensure our port is available
    if not check_port_available(PORT):
        logger.error(f"Failed to free port {PORT}, please close the application using it manually")
        sys.exit(1)
    
    # Create a stop flag file path
    stop_flag_file = project_root / "stop.flag"
    
    # Function to handle stop signals
    def handle_stop_signal(signum, frame):
        logger.info(f"Received signal {signum}, stopping server...")
        # Create a stop flag file
        with open(stop_flag_file, "w") as f:
            f.write("1")
        # Kill any processes on ports 8000 and 8001
        kill_processes_on_ports([8000, 8001])
        sys.exit(0)
    
    # Register signal handlers
    signal.signal(signal.SIGINT, handle_stop_signal)
    signal.signal(signal.SIGTERM, handle_stop_signal)
    
    # Remove stop flag file if it exists
    if stop_flag_file.exists():
        stop_flag_file.unlink()
        logger.info(f"Removed existing stop flag file: {stop_flag_file}")
    
    # Import the SSE server
    from apps.api.sse_server import app
    
    try:
        # Run the server
        logger.info(f"Server starting on port {PORT}. Press Ctrl+C to stop.")
        uvicorn.run(app, host="0.0.0.0", port=PORT, log_level="debug")
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received, stopping server...")
    finally:
        # Clean up
        if stop_flag_file.exists():
            stop_flag_file.unlink()
        logger.info("Server stopped")