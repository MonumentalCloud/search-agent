#!/usr/bin/env python
"""
Start script for the WebSocket-enabled Search Agent frontend.
"""

import os
import sys
import argparse
import subprocess
import signal
import time
from utils.pid_manager import PIDManager

# Add project root to path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, "utils"))

def main():
    """Main function to start or stop the WebSocket frontend."""
    parser = argparse.ArgumentParser(description="Start or stop the WebSocket frontend")
    parser.add_argument("--stop", action="store_true", help="Stop the running WebSocket frontend")
    args = parser.parse_args()
    
    pid_manager = PIDManager()
    
    if args.stop:
        # Stop the WebSocket frontend
        print("Stopping WebSocket frontend...")
        pid_manager.terminate_all_processes()
        return
    
    # Start the WebSocket frontend
    print("Starting WebSocket frontend...")
    
    # Start the WebSocket server
    websocket_cmd = [
        sys.executable, 
        "-m", "uvicorn", 
        "apps.api.websocket_server:app", 
        "--host", "0.0.0.0", 
        "--port", "8000", 
        "--reload"
    ]
    
    # Set environment variables for the Python path
    env = os.environ.copy()
    env["PYTHONPATH"] = f"{project_root}:{env.get('PYTHONPATH', '')}"
    
    # Start the WebSocket server process
    print(f"Starting WebSocket server: {' '.join(websocket_cmd)}")
    websocket_process = subprocess.Popen(
        websocket_cmd,
        env=env,
        cwd=project_root
    )
    
    # Store the PID
    pid_manager.store_pid("websocket_server", websocket_process.pid)
    print(f"WebSocket server started with PID {websocket_process.pid}")
    
    # Open the browser
    try:
        import webbrowser
        webbrowser.open("http://localhost:8000")
    except Exception as e:
        print(f"Failed to open browser: {e}")
    
    print("\nWebSocket frontend is running!")
    print("Open your browser and navigate to http://localhost:8000")
    print("Press Ctrl+C to stop the server")
    
    try:
        # Keep the script running
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping WebSocket frontend...")
        pid_manager.terminate_all_processes()

if __name__ == "__main__":
    main()
