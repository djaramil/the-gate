import os
from typing import List

# Lightweight adapter:
# - chat(...) -> uses LMStudio HTTP API if available
# - embed(texts) -> prefers LMStudio embed model if configured, otherwise uses sentence-transformers fallback

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "lmstudio")
LMSTUDIO_HOST = os.getenv("LMSTUDIO_HOST", "http://localhost:11434")
LMSTUDIO_MODEL = os.getenv("LMSTUDIO_MODEL", "qwen-3.6")
LMSTUDIO_EMBED_MODEL = os.getenv("LMSTUDIO_EMBED_MODEL", "")
FALLBACK_EMBED_MODEL = os.getenv("FALLBACK_EMBED_MODEL", "sentence-transformers/all-mpnet-base-v2")

def chat(system: str, prompt: str, model: str = None, max_tokens: int = 1024, temperature: float = 0.0):
    model = model or LMSTUDIO_MODEL
    if LLM_PROVIDER.lower() != "lmstudio":
        raise RuntimeError("Chat currently supports LMStudio provider only in this adapter.")
    import requests
    payload = {"model": model, "messages":[{"role":"system","content":system},{"role":"user","content":prompt}], "temperature": temperature}
    url = f"{LMSTUDIO_HOST}/v1/chat/completions"
    r = requests.post(url, json=payload, timeout=60)
    r.raise_for_status()
    return r.json()

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
