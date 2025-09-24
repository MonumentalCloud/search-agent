#!/usr/bin/env python3
"""
Test script for OpenRouter API
"""

import os
import sys
import logging
import json
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Add project root to path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from configs.load import load_yaml_config, get_default_llm

def test_openrouter_api():
    """Test the OpenRouter API connection and configuration."""
    
    # Load the config
    config_path = os.path.join(project_root, "configs", "default.yaml")
    cfg = load_yaml_config(config_path)
    llm_cfg = cfg["llm"]
    
    # Print the configuration
    print("LLM Configuration:")
    print(f"  Provider: {llm_cfg.get('provider')}")
    print(f"  Model: {llm_cfg.get('model')}")
    print(f"  API Key: {llm_cfg.get('api_key')[:10]}... (truncated)")
    
    # Check if the API key is set in the environment
    api_key_env_var = "OPENROUTER_API_KEY"
    api_key_in_env = api_key_env_var in os.environ
    print(f"\nEnvironment:")
    print(f"  {api_key_env_var} in environment: {api_key_in_env}")
    if api_key_in_env:
        print(f"  {api_key_env_var} value: {os.environ[api_key_env_var][:10]}... (truncated)")
    
    # Try to get the LLM
    print("\nTrying to initialize the LLM...")
    try:
        llm = get_default_llm()
        print(f"  LLM initialized successfully: {type(llm).__name__}")
        
        # Try a simple query
        print("\nTesting LLM with a simple query...")
        response = llm.invoke("Say hello!")
        print(f"  Response: {response.content}")
        
        print("\nOpenRouter API is working correctly!")
        return True
    except Exception as e:
        print(f"\nError initializing or using LLM: {e}")
        return False

if __name__ == "__main__":
    test_openrouter_api()
