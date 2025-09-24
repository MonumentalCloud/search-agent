#!/usr/bin/env python3
"""
Chat GUI Launcher

Simple launcher for the Streamlit chat interface.
"""

import subprocess
import sys
import os
from pathlib import Path

def main():
    """Launch the Streamlit chat GUI."""
    # Get the project root
    project_root = Path(__file__).parent
    
    # Path to the chat GUI
    chat_gui_path = project_root / "apps" / "chat_gui.py"
    
    if not chat_gui_path.exists():
        print("❌ Chat GUI not found. Please check the file path.")
        sys.exit(1)
    
    print("🚀 Starting Retrieval Agent Chat GUI...")
    print("📱 The chat interface will open in your browser")
    print("🔗 URL: http://localhost:8501")
    print("⏹️  Press Ctrl+C to stop")
    print()
    
    try:
        # Launch Streamlit
        subprocess.run([
            sys.executable, "-m", "streamlit", "run", 
            str(chat_gui_path),
            "--server.port", "8501",
            "--server.address", "0.0.0.0",
            "--browser.gatherUsageStats", "false"
        ])
    except KeyboardInterrupt:
        print("\n👋 Chat GUI stopped.")
    except Exception as e:
        print(f"❌ Error starting chat GUI: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
