#!/usr/bin/env python3
"""
Script to fix environment variables and test API connections
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
env_path = Path('.env')
if env_path.exists():
    print(f"Loading environment variables from {env_path.absolute()}")
    load_dotenv(env_path)
else:
    print(f"Error: .env file not found at {env_path.absolute()}")
    sys.exit(1)

# Check if required environment variables are set
required_vars = ['OPENROUTER_API_KEY', 'BGE_API_KEY']
missing_vars = [var for var in required_vars if not os.environ.get(var)]

if missing_vars:
    print(f"Error: Missing required environment variables: {', '.join(missing_vars)}")
    print("Please check your .env file and make sure these variables are set correctly.")
    sys.exit(1)

print("All required environment variables are set:")
for var in required_vars:
    value = os.environ.get(var)
    masked_value = value[:10] + '...' if value else 'Not set'
    print(f"  {var}: {masked_value}")

# Test OpenRouter API
print("\nTesting OpenRouter API...")
try:
    from langchain_openai import ChatOpenAI
    
    api_key = os.environ.get('OPENROUTER_API_KEY')
    llm = ChatOpenAI(
        model="openai/gpt-4o-mini",
        temperature=0.1,
        api_key=api_key,
        base_url="https://openrouter.ai/api/v1"
    )
    
    response = llm.invoke("Say hello!")
    print(f"OpenRouter API response: {response.content}")
    print("OpenRouter API test successful!")
except Exception as e:
    print(f"Error testing OpenRouter API: {e}")
    sys.exit(1)

# Test BGE Embeddings API
print("\nTesting BGE Embeddings API...")
try:
    from langchain_community.embeddings import HuggingFaceEmbeddings
    
    embeddings = HuggingFaceEmbeddings(
        model_name="BAAI/bge-m3",
        model_kwargs={'device': 'cpu'},
        encode_kwargs={'normalize_embeddings': True}
    )
    
    text = "This is a test sentence for embeddings."
    embedding = embeddings.embed_query(text)
    
    print(f"BGE Embeddings API embedding dimensions: {len(embedding)}")
    print("BGE Embeddings API test successful!")
except Exception as e:
    print(f"Error testing BGE Embeddings API: {e}")
    
print("\nEnvironment check complete!")
