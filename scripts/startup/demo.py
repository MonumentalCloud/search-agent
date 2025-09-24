#!/usr/bin/env python3
"""
Demo Script for Retrieval Agent

This script demonstrates how to use the Retrieval Agent system.
It can start the API server, chat GUI, or both.
"""

import argparse
import subprocess
import sys
import time
import threading
from pathlib import Path

def start_api_server():
    """Start the API server in a separate thread."""
    print("🚀 Starting API server...")
    subprocess.run([sys.executable, "start.py", "--api-only", "--skip-test"])

def start_chat_gui():
    """Start the chat GUI in a separate thread."""
    print("💬 Starting chat GUI...")
    subprocess.run([sys.executable, "chat.py"])

def main():
    parser = argparse.ArgumentParser(description="Retrieval Agent Demo")
    parser.add_argument("--mode", choices=["api", "chat", "both"], default="both",
                       help="What to start: api, chat, or both")
    parser.add_argument("--wait", type=int, default=3,
                       help="Wait time between starting services (seconds)")
    
    args = parser.parse_args()
    
    print("🤖 Retrieval Agent Demo")
    print("=" * 50)
    
    if args.mode == "api":
        start_api_server()
    elif args.mode == "chat":
        start_chat_gui()
    elif args.mode == "both":
        print(f"Starting both API server and chat GUI...")
        print(f"Waiting {args.wait} seconds between services...")
        
        # Start API server in background
        api_thread = threading.Thread(target=start_api_server, daemon=True)
        api_thread.start()
        
        # Wait for API to start
        time.sleep(args.wait)
        
        # Start chat GUI
        start_chat_gui()
    
    print("\n👋 Demo finished!")

if __name__ == "__main__":
    main()
