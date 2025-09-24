#!/usr/bin/env python3
"""
Script to directly fix environment variables in the running process
"""

import os
import sys
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

print("\nEnvironment variables set successfully!")
print("Please restart the WebSocket server for the changes to take effect.")
