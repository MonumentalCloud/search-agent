import requests
import json
import sys
import os

# Genos endpoint information from configs/throwaway.py
serving_id = 15
bearer_token = 'a972ad45b0f845ef9ea29badd5423d20'
genos_url = 'https://genos.genon.ai:3443'

# Endpoint for the LLM
endpoint = f"{genos_url}/api/gateway/rep/serving/{serving_id}"
headers = {"Authorization": f"Bearer {bearer_token}", "Content-Type": "application/json"}

def test_chat_completion():
    """Test if we can get a chat completion directly"""
    try:
        chat_url = f"{genos_url}/v1/chat/completions"
        payload = {
            "model": "gpt-4o",  # Try using a known model name
            "messages": [
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Hello, what can you do?"}
            ],
            "temperature": 0.1
        }
        
        print("\n=== Chat Completion Test ===")
        print(f"Request URL: {chat_url}")
        print(f"Request payload: {json.dumps(payload, indent=2)}")
        
        response = requests.post(chat_url, headers=headers, json=payload, timeout=60)
        response.raise_for_status()
        
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        
        # Check if response contains expected fields
        result = response.json()
        if 'choices' in result and len(result['choices']) > 0:
            message = result['choices'][0].get('message', {})
            content = message.get('content', '')
            if content:
                print("\nChat completion successful!")
                print(f"Response content: {content[:100]}...")
            else:
                print("No content in response")
        else:
            print("No choices in response")
            
    except Exception as e:
        print(f"Error testing chat completion: {e}")

def test_embeddings():
    """Test if we can get embeddings from the embeddings endpoint"""
    try:
        # Using the embeddings endpoint from default.yaml
        embeddings_url = "https://genos.genon.ai:3443/api/gateway/rep/serving/10/v1/embeddings"
        embeddings_token = "your_bge_api_key_here"
        embeddings_headers = {"Authorization": f"Bearer {embeddings_token}", "Content-Type": "application/json"}
        
        payload = {
            "input": ["This is a test sentence for embedding."]
        }
        
        print("\n=== Embeddings Test ===")
        print(f"Request URL: {embeddings_url}")
        
        response = requests.post(embeddings_url, headers=embeddings_headers, json=payload, timeout=30)
        response.raise_for_status()
        
        print(f"Status Code: {response.status_code}")
        result = response.json()
        
        # Check if we got embeddings
        if 'data' in result and len(result['data']) > 0:
            embedding = result['data'][0].get('embedding', [])
            if embedding:
                print(f"Embedding dimension: {len(embedding)}")
                print(f"First 5 values: {embedding[:5]}")
                print("Embeddings test successful!")
            else:
                print("No embedding in response")
        else:
            print("No data in response")
            
    except Exception as e:
        print(f"Error testing embeddings: {e}")

def test_with_genos_llm_class():
    """Test using the GenosLLM class from configs/load.py"""
    try:
        print("\n=== Testing with GenosLLM class ===")
        
        # Import the GenosLLM class from configs/load.py
        sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from configs.load import get_default_llm
        
        # Create a custom config
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("""
llm:
  provider: genos
  bearer_token: a972ad45b0f845ef9ea29badd5423d20
  genos_url: https://genos.genon.ai:3443
  model: gpt-4o
  temperature: 0.1
            """)
            temp_config_path = f.name
        
        try:
            # Get the LLM instance
            llm = get_default_llm(config_path=temp_config_path)
            print(f"LLM type: {type(llm)}")
            
            # Test the LLM
            response = llm.invoke("Hello, what can you do?")
            print(f"LLM response: {response.content[:100]}...")
            print("GenosLLM test successful!")
        finally:
            # Clean up the temporary file
            os.unlink(temp_config_path)
            
    except Exception as e:
        print(f"Error testing GenosLLM class: {e}")

if __name__ == "__main__":
    print("Testing Genos LLM Endpoint...")
    test_chat_completion()
    test_embeddings()
    test_with_genos_llm_class()
    print("\nTests completed.")