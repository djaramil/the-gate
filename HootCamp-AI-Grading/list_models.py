#!/usr/bin/env python3
"""List available models from LMStudio and TrussedAI"""

import os
import requests
from dotenv import load_dotenv
from llm_adapter import get_trussedai_api_key

# Load environment variables from .env file
load_dotenv()

def list_lmstudio_models():
    """List available models from LMStudio"""
    host = os.getenv("LMSTUDIO_HOST", "http://localhost:1234")
    print(f"\n{'='*60}")
    print(f"LMStudio Models ({host})")
    print(f"{'='*60}")
    
    try:
        response = requests.get(f"{host}/v1/models", timeout=5)
        response.raise_for_status()
        data = response.json()
        
        models = data.get('data', [])
        if not models:
            print("No models found")
            return
        
        print(f"Found {len(models)} model(s):\n")
        for model in models:
            model_id = model.get('id', 'unknown')
            owned_by = model.get('owned_by', 'unknown')
            print(f"  • {model_id}")
            print(f"    Owner: {owned_by}")
    except Exception as e:
        print(f"Error: {e}")
        print("Make sure LMStudio server is running")

def list_trussedai_models():
    """List available models from TrussedAI by testing common model names"""
    host = os.getenv("TRUSSEDAI_HOST", "https://api.trussed.ai")
    configured_model = os.getenv("TRUSSEDAI_MODEL", "gpt-4o-mini")
    
    print(f"\n{'='*60}")
    print(f"TrussedAI Chat Models ({host})")
    print(f"{'='*60}")
    
    # Check if any API keys are configured
    openai_key = os.getenv("TRUSSEDAI_OPENAI_API_KEY", "")
    gemini_key = os.getenv("TRUSSEDAI_GEMINI_API_KEY", "")
    hpc_key = os.getenv("TRUSSEDAI_HPC_API_KEY", "")
    
    if not any([openai_key, gemini_key, hpc_key]):
        print("No API keys configured")
        print("Set TRUSSEDAI_OPENAI_API_KEY, TRUSSEDAI_GEMINI_API_KEY, or TRUSSEDAI_HPC_API_KEY in .env file")
        return
    
    # FAU TrussedAI models from actual project access
    test_models = [
        configured_model,  # Test configured model first
        # HootCamp OpenAI project
        "gpt-5.4",
        # HootCamp Gemini project
        "gemini-2.5-pro",
        # HootCamp HPC project (local models)
        "cogito:14b",
        "gemma4-vibe",
        "ministral-3:14b",
        "gemma4:26b",
        "lfm2.5-thinking:1.2b",
        "rnj-1:8b",
        "granite4:350m",
        "laguna-xs.2"
    ]
    
    # Remove duplicates while preserving order
    test_models = list(dict.fromkeys(test_models))
    
    print(f"Testing {len(test_models)} model names (starting with configured: {configured_model})...\n")
    
    available_models = []
    
    for model_name in test_models:
        # Get the appropriate API key for this model
        api_key = get_trussedai_api_key(model_name)
        if not api_key:
            print(f"  ✗ {model_name} (no API key configured for this model)")
            continue
            
        headers = {"Authorization": f"Bearer {api_key}"}
        
        try:
            payload = {
                "model": model_name,
                "messages": [{"role": "user", "content": "test"}],
                "max_tokens": 10
            }
            # Try different endpoint paths
            endpoints = ["/chat/completions", "/v1/chat/completions", "/api/v1/chat/completions"]
            
            for endpoint in endpoints:
                try:
                    response = requests.post(f"{host}{endpoint}", 
                                            json=payload, 
                                            headers=headers, 
                                            timeout=10)
                    
                    if response.status_code == 200:
                        available_models.append(model_name)
                        marker = "★" if model_name == configured_model else "✓"
                        print(f"  {marker} {model_name} (via {endpoint})")
                        break
                    elif response.status_code == 401:
                        print(f"  ✗ Authentication failed - check API key")
                        return
                    elif response.status_code == 429:
                        print(f"  ✗ {model_name} (rate limited)")
                        break
                    elif response.status_code == 400:
                        # Try next endpoint
                        continue
                    else:
                        print(f"  ✗ {model_name} (HTTP {response.status_code}: {response.text[:50]})")
                        break
                except requests.exceptions.RequestException as e:
                    # Try next endpoint
                    continue
            else:
                print(f"  ✗ {model_name} (all endpoints failed)")
                
        except requests.exceptions.Timeout:
            print(f"  ✗ {model_name} (timeout)")
        except Exception as e:
            print(f"  ✗ {model_name} (error: {str(e)[:30]})")
    
    if available_models:
        print(f"\nFound {len(available_models)} available chat model(s):")
        for model in available_models:
            marker = "★" if model == configured_model else "•"
            print(f"  {marker} {model}")
    else:
        print("\nNo chat models found or API endpoint may be different")
    
    # Test embedding models
    print(f"\n{'='*60}")
    print(f"TrussedAI Embedding Models")
    print(f"{'='*60}")
    
    embedding_models = [
        # HootCamp HPC project (local embedding models)
        "nomic-embed-text:v1.5",
        "nomic-embed-text-v2-moe:latest",
        "embeddinggemma:300m"
    ]
    
    print(f"Testing {len(embedding_models)} embedding model names...\n")
    
    available_embeddings = []
    
    for model_name in embedding_models:
        # Get the appropriate API key for this model (embedding models use HPC key)
        api_key = get_trussedai_api_key(model_name)
        if not api_key:
            print(f"  ✗ {model_name} (no API key configured for this model)")
            continue
            
        headers = {"Authorization": f"Bearer {api_key}"}
        
        try:
            payload = {
                "model": model_name,
                "input": ["test text"]
            }
            # Try different endpoint paths
            endpoints = ["/embeddings", "/v1/embeddings", "/api/v1/embeddings"]
            
            for endpoint in endpoints:
                try:
                    response = requests.post(f"{host}{endpoint}", 
                                            json=payload, 
                                            headers=headers, 
                                            timeout=10)
                    
                    if response.status_code == 200:
                        available_embeddings.append(model_name)
                        print(f"  ✓ {model_name} (via {endpoint})")
                        break
                    elif response.status_code == 429:
                        print(f"  ✗ {model_name} (rate limited)")
                        break
                    elif response.status_code == 400:
                        # Try next endpoint
                        continue
                    else:
                        print(f"  ✗ {model_name} (HTTP {response.status_code}: {response.text[:50]})")
                        break
                except requests.exceptions.RequestException as e:
                    # Try next endpoint
                    continue
            else:
                print(f"  ✗ {model_name} (all endpoints failed)")
                
        except requests.exceptions.Timeout:
            print(f"  ✗ {model_name} (timeout)")
        except Exception as e:
            print(f"  ✗ {model_name} (error: {str(e)[:30]})")
    
    if available_embeddings:
        print(f"\nFound {len(available_embeddings)} available embedding model(s):")
        for model in available_embeddings:
            print(f"  • {model}")
    else:
        print("\nNo embedding models found")
    
    # Summary
    print(f"\n{'='*60}")
    print("Summary:")
    print(f"  Chat models: {len(available_models)}")
    print(f"  Embedding models: {len(available_embeddings)}")
    print(f"{'='*60}")

def main():
    print("Available LLM Models")
    print("="*60)
    
    # List LMStudio models
    list_lmstudio_models()
    
    # List TrussedAI models
    list_trussedai_models()
    
    print(f"\n{'='*60}")
    print("Configuration from .env:")
    print(f"  LLM_PROVIDER: {os.getenv('LLM_PROVIDER', 'lmstudio')}")
    print(f"  LMSTUDIO_MODEL: {os.getenv('LMSTUDIO_MODEL', 'qwen/qwen3.6-27b')}")
    print(f"  TRUSSEDAI_MODEL: {os.getenv('TRUSSEDAI_MODEL', 'gpt-4o-mini')}")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()
