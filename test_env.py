#!/usr/bin/env python3
"""
Test script for environment variables and API connections
"""

import os
import sys
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Add project root to path
project_root = Path(__file__).parent.absolute()
sys.path.insert(0, str(project_root))

# Import load_environment from load_env.py
from load_env import load_environment

def test_environment_variables():
    """Test if environment variables are properly loaded."""
    # Load environment variables
    if not load_environment():
        logger.error("Failed to load environment variables")
        return False
    
    # Check if required environment variables are set
    required_vars = ['OPENROUTER_API_KEY', 'BGE_API_KEY']
    missing_vars = [var for var in required_vars if not os.environ.get(var)]
    
    if missing_vars:
        logger.error(f"Missing required environment variables: {', '.join(missing_vars)}")
        return False
    
    logger.info("All required environment variables are set")
    
    # Print the environment variables (first few characters only)
    for var in required_vars:
        value = os.environ.get(var, '')
        masked_value = value[:10] + '...' if value else 'Not set'
        logger.info(f"{var}: {masked_value}")
    
    return True

def test_openrouter_api():
    """Test the OpenRouter API connection."""
    from langchain_openai import ChatOpenAI
    
    api_key = os.environ.get('OPENROUTER_API_KEY')
    if not api_key:
        logger.error("OPENROUTER_API_KEY is not set")
        return False
    
    try:
        # Initialize the ChatOpenAI with OpenRouter
        logger.info("Initializing ChatOpenAI with OpenRouter...")
        llm = ChatOpenAI(
            model="openai/gpt-4o-mini",
            temperature=0.1,
            api_key=api_key,
        )
        
        # Test with a simple query
        logger.info("Testing with a simple query...")
        response = llm.invoke("Say hello!")
        
        logger.info(f"Response: {response.content}")
        logger.info("OpenRouter API test successful!")
        return True
    except Exception as e:
        logger.error(f"Error testing OpenRouter API: {e}")
        return False

def test_bge_embeddings():
    """Test the BGE embeddings API connection."""
    from configs.load import get_default_embeddings
    
    api_key = os.environ.get('BGE_API_KEY')
    if not api_key:
        logger.error("BGE_API_KEY is not set")
        return False
    
    try:
        # Initialize the embeddings model
        logger.info("Initializing BGE embeddings model...")
        embeddings = get_default_embeddings()
        
        # Test with a simple text
        logger.info("Testing with a simple text...")
        text = "This is a test sentence for embeddings."
        embedding = embeddings.embed_query(text)
        
        logger.info(f"Embedding dimensions: {len(embedding)}")
        logger.info("BGE embeddings API test successful!")
        return True
    except Exception as e:
        logger.error(f"Error testing BGE embeddings API: {e}")
        return False

if __name__ == "__main__":
    print("Testing environment variables and API connections...\n")
    
    # Test environment variables
    print("\n=== Testing Environment Variables ===")
    env_ok = test_environment_variables()
    
    if env_ok:
        # Test OpenRouter API
        print("\n=== Testing OpenRouter API ===")
        openrouter_ok = test_openrouter_api()
        
        # Test BGE embeddings API
        print("\n=== Testing BGE Embeddings API ===")
        bge_ok = test_bge_embeddings()
        
        # Print summary
        print("\n=== Summary ===")
        print(f"Environment Variables: {'✓ OK' if env_ok else '✗ Failed'}")
        print(f"OpenRouter API: {'✓ OK' if openrouter_ok else '✗ Failed'}")
        print(f"BGE Embeddings API: {'✓ OK' if bge_ok else '✗ Failed'}")
        
        if env_ok and openrouter_ok and bge_ok:
            print("\nAll tests passed successfully!")
            sys.exit(0)
        else:
            print("\nSome tests failed. Please check the logs above.")
            sys.exit(1)
    else:
        print("\nEnvironment variables test failed. Please check your .env file.")
        sys.exit(1)
