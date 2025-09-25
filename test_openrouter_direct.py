#!/usr/bin/env python3
"""
Direct test of OpenRouter API without LangChain to isolate the issue
"""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_openrouter_direct():
    """Test OpenRouter API directly"""
    print("=== Direct OpenRouter Test ===")
    
    # Load environment
    from dotenv import load_dotenv
    load_dotenv()
    
    api_key = os.environ.get('OPENROUTER_API_KEY')
    if not api_key:
        print("ERROR: OPENROUTER_API_KEY not found")
        return False
    
    print(f"API Key found: {api_key[:10]}...")
    
    # Test 1: Direct OpenAI client
    print("\n--- Test 1: Direct OpenAI Client ---")
    try:
        import openai
        client = openai.OpenAI(
            api_key=api_key,
            base_url="https://openrouter.ai/api/v1"
        )
        
        response = client.chat.completions.create(
            model="openai/gpt-4o-mini",
            messages=[{"role": "user", "content": "Say hello!"}],
            max_tokens=50
        )
        print(f"Direct OpenAI client success: {response.choices[0].message.content}")
    except Exception as e:
        print(f"Direct OpenAI client failed: {e}")
        return False
    
    # Test 2: LangChain ChatOpenAI with explicit parameters
    print("\n--- Test 2: LangChain with explicit parameters ---")
    try:
        from langchain_openai import ChatOpenAI
        
        llm = ChatOpenAI(
            model="openai/gpt-4o-mini",
            temperature=0.1,
            openai_api_key=api_key,
            openai_api_base="https://openrouter.ai/api/v1"
        )
        
        response = llm.invoke("Say hello!")
        print(f"LangChain explicit success: {response.content}")
    except Exception as e:
        print(f"LangChain explicit failed: {e}")
        return False
    
    # Test 3: LangChain ChatOpenAI with api_key parameter
    print("\n--- Test 3: LangChain with api_key parameter ---")
    try:
        from langchain_openai import ChatOpenAI
        
        llm = ChatOpenAI(
            model="openai/gpt-4o-mini",
            temperature=0.1,
            api_key=api_key,
            base_url="https://openrouter.ai/api/v1"
        )
        
        response = llm.invoke("Say hello!")
        print(f"LangChain api_key success: {response.content}")
    except Exception as e:
        print(f"LangChain api_key failed: {e}")
        return False
    
    # Test 4: LangChain with environment variable
    print("\n--- Test 4: LangChain with environment variable ---")
    try:
        # Set environment variable
        os.environ["OPENAI_API_KEY"] = api_key
        
        from langchain_openai import ChatOpenAI
        
        llm = ChatOpenAI(
            model="openai/gpt-4o-mini",
            temperature=0.1,
            base_url="https://openrouter.ai/api/v1"
        )
        
        response = llm.invoke("Say hello!")
        print(f"LangChain env var success: {response.content}")
    except Exception as e:
        print(f"LangChain env var failed: {e}")
        return False
    
    print("\n✅ All tests passed!")
    return True

if __name__ == "__main__":
    test_openrouter_direct()
