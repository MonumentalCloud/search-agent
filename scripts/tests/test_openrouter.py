import requests
import json
import sys
import os

# Get the OpenRouter API key from default.yaml
def get_openrouter_key():
    try:
        with open(os.path.join(os.path.dirname(__file__), "configs/default.yaml"), "r") as f:
            import yaml
            config = yaml.safe_load(f)
            return config["llm"]["api_key"]
    except Exception as e:
        print(f"Error reading API key from config: {e}")
        return None

def test_openrouter():
    api_key = get_openrouter_key()
    if not api_key:
        print("Failed to get OpenRouter API key")
        return
    
    print(f"Using OpenRouter API key: {api_key[:10]}...")
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    url = "https://openrouter.ai/api/v1/chat/completions"
    
    payload = {
        "model": "openai/gpt-4o-mini",
        "messages": [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello, what can you do?"}
        ],
        "temperature": 0.1
    }
    
    print("\n=== OpenRouter API Test ===")
    print(f"Request URL: {url}")
    print(f"Request model: {payload['model']}")
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        
        print(f"Status Code: {response.status_code}")
        result = response.json()
        
        # Print the response content
        if 'choices' in result and len(result['choices']) > 0:
            message = result['choices'][0].get('message', {})
            content = message.get('content', '')
            if content:
                print("\nAPI call successful!")
                print(f"Response content: {content[:200]}...")
                print("\nModel used:", result.get('model', 'Unknown'))
                print("OpenRouter API key is working correctly!")
                return True
            else:
                print("No content in response")
        else:
            print("No choices in response")
            print(f"Full response: {json.dumps(result, indent=2)}")
    
    except Exception as e:
        print(f"Error testing OpenRouter API: {e}")
        if hasattr(e, 'response') and e.response is not None:
            try:
                print(f"Response content: {e.response.text}")
            except:
                pass
    
    return False

if __name__ == "__main__":
    print("Testing OpenRouter API key...")
    success = test_openrouter()
    print("\nTest completed. Success:", success)
