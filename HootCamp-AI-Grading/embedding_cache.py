import hashlib, json
from pathlib import Path

def file_hash(text):
    return hashlib.sha1(text.encode('utf-8')).hexdigest()

class EmbeddingCache:
    def __init__(self, cache_dir="cache/embeddings"):
        self.base = Path(cache_dir)
        self.base.mkdir(parents=True, exist_ok=True)
    def get(self, repo_tag, file_hash_val):
        p = self.base / repo_tag / f"{file_hash_val}.json"
        if p.exists():
            return json.loads(p.read_text())
        return None
    def set(self, repo_tag, file_hash_val, payload):
        d = self.base / repo_tag
        d.mkdir(parents=True, exist_ok=True)
        p = d / f"{file_hash_val}.json"
        p.write_text(json.dumps(payload))
