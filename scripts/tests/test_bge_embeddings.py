#!/usr/bin/env python3
"""
Test script for BGE-M3 embeddings integration
"""
import os
from configs.load import get_default_embeddings

def test_bge_embeddings():
    """Test the BGE-M3 embedding service."""
    print("🧪 Testing BGE-M3 Embeddings...")
    
    # Check if API key is set (either in env var or config file)
    api_key = os.getenv('BGE_API_KEY')
    if not api_key:
        print("ℹ️  BGE_API_KEY environment variable not set, will use config file")
    
    try:
        # Load embeddings
        embeddings = get_default_embeddings()
        print("✅ Embeddings loaded successfully")
        
        # Test single query
        test_text = "전자금융 거래"
        print(f"📝 Testing with: '{test_text}'")
        
        vector = embeddings.embed_query(test_text)
        print(f"✅ Generated vector with {len(vector)} dimensions")
        print(f"📊 First 5 values: {vector[:5]}")
        
        # Test batch queries
        test_texts = ["금융회사", "전자금융", "거래"]
        print(f"📝 Testing batch with: {test_texts}")
        
        vectors = embeddings.embed_documents(test_texts)
        print(f"✅ Generated {len(vectors)} vectors")
        for i, vec in enumerate(vectors):
            print(f"  Vector {i+1}: {len(vec)} dims, first 3 values: {vec[:3]}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_bge_embeddings()
    if success:
        print("\n🎉 BGE-M3 embeddings are working!")
    else:
        print("\n💥 BGE-M3 embeddings test failed")
