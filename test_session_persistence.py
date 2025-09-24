#!/usr/bin/env python3
"""
Test script to verify session persistence in conversation memory
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from memory.conversation_memory import conversation_memory

def test_session_persistence():
    """Test if conversation memory persists sessions correctly"""
    print("🧪 Testing Session Persistence")
    
    session_id = "test_persistence_session"
    
    # Test 1: Add user message
    print("\n1. Adding user message...")
    conversation_memory.add_user_message(session_id, "Hello, this is a test message")
    print(f"Session exists: {session_id in conversation_memory._conversations}")
    print(f"History length: {len(conversation_memory._conversations[session_id]['history'])}")
    
    # Test 2: Add assistant message
    print("\n2. Adding assistant message...")
    conversation_memory.add_assistant_message(session_id, "Hello! How can I help you?", [])
    print(f"Session exists: {session_id in conversation_memory._conversations}")
    print(f"History length: {len(conversation_memory._conversations[session_id]['history'])}")
    
    # Test 3: Check conversation history
    print("\n3. Checking conversation history...")
    history = conversation_memory._conversations[session_id]["history"]
    for i, msg in enumerate(history):
        print(f"  Message {i+1}: {msg['role']} - {msg['content'][:50]}...")
    
    # Test 4: Get context for Meta Agent
    print("\n4. Getting context for Meta Agent...")
    context = conversation_memory.get_advanced_context_for_meta_agent(session_id, "What did we discuss?")
    print(f"Context analysis: {context['context_analysis']}")
    
    # Test 5: Check if session persists after getting context
    print("\n5. Checking session persistence...")
    print(f"Session still exists: {session_id in conversation_memory._conversations}")
    print(f"History length: {len(conversation_memory._conversations[session_id]['history'])}")

if __name__ == "__main__":
    test_session_persistence()
