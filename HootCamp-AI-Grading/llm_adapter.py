import os
import time
from typing import List
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Lightweight adapter:
# - chat(...) -> uses LMStudio HTTP API or TrussedAI if available
# - embed(texts) -> prefers LMStudio embed model if configured, otherwise uses sentence-transformers fallback

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "lmstudio")
LMSTUDIO_HOST = os.getenv("LMSTUDIO_HOST", "http://localhost:1234")
LMSTUDIO_MODEL = os.getenv("LMSTUDIO_MODEL", "qwen/qwen3.6-27b")
LMSTUDIO_EMBED_MODEL = os.getenv("LMSTUDIO_EMBED_MODEL", "text-embedding-nomic-embed-text-v1.5")
FALLBACK_EMBED_MODEL = os.getenv("FALLBACK_EMBED_MODEL", "sentence-transformers/all-mpnet-base-v2")
MOCK_MODE = os.getenv("MOCK_MODE", "false").lower() == "true"

# TrussedAI configuration
TRUSSEDAI_HOST = os.getenv("TRUSSEDAI_HOST", "https://fauengtrussed.fau.edu/provider/generic")
TRUSSEDAI_MODEL = os.getenv("TRUSSEDAI_MODEL", "cogito:14b")
TRUSSEDAI_EMBED_MODEL = os.getenv("TRUSSEDAI_EMBED_MODEL", "nomic-embed-text:v1.5")

# API keys for each FAU TrussedAI project
TRUSSEDAI_OPENAI_API_KEY = os.getenv("TRUSSEDAI_OPENAI_API_KEY", "")
TRUSSEDAI_GEMINI_API_KEY = os.getenv("TRUSSEDAI_GEMINI_API_KEY", "")
TRUSSEDAI_HPC_API_KEY = os.getenv("TRUSSEDAI_HPC_API_KEY", "")

def get_trussedai_api_key(model: str) -> str:
    """Select the appropriate API key based on the model being used."""
    if model.startswith("gpt-"):
        return TRUSSEDAI_OPENAI_API_KEY
    elif model.startswith("gemini-"):
        return TRUSSEDAI_GEMINI_API_KEY
    else:
        return TRUSSEDAI_HPC_API_KEY

# Rate limit handling
MAX_RETRIES = 5
INITIAL_RETRY_DELAY = 2  # seconds
MAX_RETRY_DELAY = 60  # seconds

def test_connection() -> bool:
    """Test if LLM provider is reachable."""
    if MOCK_MODE:
        return True
    
    if LLM_PROVIDER.lower() == "trussedai":
        api_key = get_trussedai_api_key(TRUSSEDAI_MODEL)
        if not api_key:
            print("TrussedAI API key not configured for selected model")
            return False
        try:
            import requests
            headers = {"Authorization": f"Bearer {api_key}"}
            r = requests.get(f"{TRUSSEDAI_HOST}/v1/models", headers=headers, timeout=5)
            return r.status_code == 200
        except Exception as e:
            print(f"TrussedAI connection test failed: {e}")
            return False
    else:  # lmstudio
        try:
            import requests
            url = f"{LMSTUDIO_HOST}/v1/models"
            r = requests.get(url, timeout=5)
            return r.status_code == 200
        except Exception as e:
            print(f"LMStudio connection test failed: {e}")
            return False

def chat(system: str, prompt: str, model: str = None, max_tokens: int = 1024, temperature: float = 0.0, timeout: int = None):
    if MOCK_MODE:
        # Mock response for testing without LLM
        return {
            "choices": [{
                "message": {
                    "content": '{"present": true, "explanation": "Mock response - LLM not running"}'
                }
            }],
            "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
        }
    
    import requests
    
    if LLM_PROVIDER.lower() == "trussedai":
        model = model or TRUSSEDAI_MODEL
        api_key = get_trussedai_api_key(model)
        if not api_key:
            raise RuntimeError("TrussedAI API key not configured for selected model")
        headers = {"Authorization": f"Bearer {api_key}"}
        payload = {"model": model, "messages":[{"role":"system","content":system},{"role":"user","content":prompt}], "temperature": temperature, "max_tokens": max_tokens}
        url = f"{TRUSSEDAI_HOST}/chat/completions"
        
        # Use dynamic timeout or default to 120s
        request_timeout = timeout or 120
        
        # Retry logic for rate limiting
        for attempt in range(MAX_RETRIES):
            try:
                r = requests.post(url, json=payload, headers=headers, timeout=request_timeout)
                
                if r.status_code == 429:
                    # Rate limited - wait and retry
                    if attempt == MAX_RETRIES - 1:
                        raise RuntimeError(f"Rate limit exceeded after {MAX_RETRIES} retries")
                    
                    delay = min(INITIAL_RETRY_DELAY * (2 ** attempt), MAX_RETRY_DELAY)
                    print(f"      ⚠ Rate limited (attempt {attempt + 1}/{MAX_RETRIES}). Waiting {delay}s before retry...")
                    time.sleep(delay)
                    continue
                
                r.raise_for_status()
                response = r.json()
                break
                
            except requests.exceptions.RequestException as e:
                if attempt == MAX_RETRIES - 1:
                    raise
                delay = min(INITIAL_RETRY_DELAY * (2 ** attempt), MAX_RETRY_DELAY)
                print(f"      ⚠ Request failed (attempt {attempt + 1}/{MAX_RETRIES}): {e}. Retrying in {delay}s...")
                time.sleep(delay)
                
    else:  # lmstudio
        model = model or LMSTUDIO_MODEL
        payload = {"model": model, "messages":[{"role":"system","content":system},{"role":"user","content":prompt}], "temperature": temperature}
        url = f"{LMSTUDIO_HOST}/v1/chat/completions"
        # Use dynamic timeout or default to 90s
        request_timeout = timeout or 90
        r = requests.post(url, json=payload, timeout=request_timeout)
        r.raise_for_status()
        response = r.json()
    
    # Log token usage
    usage = response.get('usage', {})
    if usage:
        print(f"      Tokens: {usage.get('prompt_tokens', 0)} in, {usage.get('completion_tokens', 0)} out, {usage.get('total_tokens', 0)} total")
    
    return response

def embed(texts: List[str], model: str = None):
    model = model or (LMSTUDIO_EMBED_MODEL or FALLBACK_EMBED_MODEL)
    if model and model.startswith("sentence-transformers/"):
        from sentence_transformers import SentenceTransformer
        m = SentenceTransformer(model.split("/",1)[1])
        embs = m.encode(texts, show_progress_bar=False)
        return [e.tolist() for e in embs]
    if LLM_PROVIDER.lower() == "lmstudio" and LMSTUDIO_EMBED_MODEL:
        import requests
        url = f"{LMSTUDIO_HOST}/v1/embeddings"
        payload = {"model": LMSTUDIO_EMBED_MODEL, "input": texts}
        r = requests.post(url, json=payload, timeout=60)
        r.raise_for_status()
        data = r.json()
        return [item["embedding"] for item in data.get("data", [])]
    raise RuntimeError("No embedding provider configured")
