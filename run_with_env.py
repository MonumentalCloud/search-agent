#!/usr/bin/env python3
"""
Script to run the WebSocket server with environment variables
"""

import os
import sys
import subprocess
from pathlib import Path

# Read the .env file manually
env_path = Path('.env')
if env_path.exists():
    print(f"Reading environment variables from {env_path.absolute()}")
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
            print(f"Set environment variable: {key}")
else:
    print(f"Error: .env file not found at {env_path.absolute()}")
    sys.exit(1)

# Check if required environment variables are set
required_vars = ['OPENROUTER_API_KEY', 'BGE_API_KEY']
for var in required_vars:
    value = os.environ.get(var)
    masked_value = value[:10] + '...' if value else 'Not set'
    print(f"  {var}: {masked_value}")

print("\nStarting WebSocket server with environment variables...")

# Run the WebSocket server
cmd = ["python", "run.py", "--websocket", "--websocket-port=8000"]
subprocess.run(cmd)
