#!/usr/bin/env python3
"""
Fix for OpenRouter API configuration
"""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.absolute()
sys.path.insert(0, str(project_root))

# Import load_environment from load_env.py
from load_env import load_environment

# Load environment variables
load_environment()

def test_openrouter_fixed():
    """Test OpenRouter API with correct base URL."""
    from langchain_openai import ChatOpenAI
    
    api_key = os.environ.get('OPENROUTER_API_KEY')
    if not api_key:
        print("OPENROUTER_API_KEY is not set")
        return False
    
    try:
        # Initialize the ChatOpenAI with OpenRouter
        print("Initializing ChatOpenAI with OpenRouter...")
        llm = ChatOpenAI(
            model="openai/gpt-4o-mini",
            temperature=0.1,
            api_key=api_key,
            base_url="https://openrouter.ai/api/v1"  # Explicitly set the base URL
        )
        
        # Test with a simple query
        print("Testing with a simple query...")
        response = llm.invoke("Say hello!")
        
        print(f"Response: {response.content}")
        print("OpenRouter API test successful!")
        return True
    except Exception as e:
        print(f"Error testing OpenRouter API: {e}")
        return False

if __name__ == "__main__":
    print("Testing OpenRouter API with fixed configuration...")
    test_openrouter_fixed()
