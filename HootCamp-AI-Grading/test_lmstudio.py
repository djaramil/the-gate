#!/usr/bin/env python3
"""Test LMStudio connection"""

import os
from llm_adapter import test_connection, chat

print("Testing LMStudio connection...")
print(f"LMSTUDIO_HOST: {os.getenv('LMSTUDIO_HOST', 'http://localhost:11434')}")
print(f"MOCK_MODE: {os.getenv('MOCK_MODE', 'false')}")

if test_connection():
    print("✓ Connection successful!")
    
    # Test a simple chat
    print("\nTesting chat...")
    try:
        response = chat(
            system="You are a helpful assistant.",
            prompt="Say 'Hello' in one word.",
            max_tokens=10
        )
        content = response.get('choices', [{}])[0].get('message', {}).get('content', '')
        print(f"Response: {content}")
    except Exception as e:
        print(f"Chat test failed: {e}")
else:
    print("✗ Connection failed!")
    print("Make sure LMStudio server is running.")
    print("Use MOCK_MODE=true for testing without LMStudio.")
