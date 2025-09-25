#!/usr/bin/env python3
"""
Debug script to check environment variables on Render
"""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def debug_environment():
    """Debug environment variables and configuration"""
    print("=== Environment Debug ===")
    print(f"Python path: {sys.path[0]}")
    print(f"Working directory: {os.getcwd()}")
    print(f"RENDER environment: {os.environ.get('RENDER', 'Not set')}")
    print()
    
    print("=== Environment Variables ===")
    env_vars = [
        'OPENROUTER_API_KEY',
        'BGE_API_KEY', 
        'CONFIG_PATH',
        'PYTHONPATH',
        'PORT'
    ]
    
    for var in env_vars:
        value = os.environ.get(var)
        if value:
            # Mask the API key for security
            if 'API_KEY' in var:
                masked_value = value[:10] + '...' if len(value) > 10 else '***'
                print(f"{var}: {masked_value}")
            else:
                print(f"{var}: {value}")
        else:
            print(f"{var}: NOT SET")
    
    print()
    print("=== Configuration Test ===")
    try:
        from configs.load import get_default_config, get_default_llm
        
        config = get_default_config()
        print(f"Config loaded: {bool(config)}")
        
        llm_config = config.get('llm', {})
        print(f"LLM provider: {llm_config.get('provider')}")
        print(f"LLM model: {llm_config.get('model')}")
        print(f"LLM api_key: {'SET' if llm_config.get('api_key') else 'NOT SET'}")
        print(f"LLM base_url: {llm_config.get('base_url')}")
        
        print()
        print("=== LLM Initialization Test ===")
        try:
            llm = get_default_llm()
            print("LLM initialized successfully")
        except Exception as e:
            print(f"LLM initialization failed: {e}")
            
    except Exception as e:
        print(f"Configuration error: {e}")

if __name__ == "__main__":
    debug_environment()
