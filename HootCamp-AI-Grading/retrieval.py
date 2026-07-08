import re
from typing import List
from llm_adapter import embed
from embedding_cache import EmbeddingCache, file_hash

def cosine_similarity(v1: List[float], v2: List[float]) -> float:
    dot = sum(a * b for a, b in zip(v1, v2))
    mag1 = sum(a * a for a in v1) ** 0.5
    mag2 = sum(b * b for b in v2) ** 0.5
    if mag1 == 0 or mag2 == 0:
        return 0.0
    return dot / (mag1 * mag2)

def compute_keyword_score(query: str, text: str) -> float:
    """Computes a simple frequency-based keyword match score."""
    query_words = set(re.findall(r'\w+', query.lower()))
    text_lower = text.lower()
    score = 0.0
    for word in query_words:
        if len(word) > 2: # Ignore very short stop words
            count = len(re.findall(r'\b' + re.escape(word) + r'\b', text_lower))
            if count > 0:
                # 1 point for existence, small bonus for frequency (capped)
                score += 1.0 + (0.1 * min(count, 10))
    return score

class CodeRetriever:
    def __init__(self, source_files: dict, chunk_size: int = 1500, overlap: int = 200, verbose: bool = True, repo_tag: str = "default"):
        self.chunks = []
        self.embeddings = []
        self.verbose = verbose
        self.repo_tag = repo_tag
        self.cache = EmbeddingCache()
        
        if self.verbose: print("Chunking source files...")
        self._chunk_files(source_files, chunk_size, overlap)
        
        if self.verbose: print(f"Generating embeddings for {len(self.chunks)} chunks...")
        self._generate_embeddings()

    def _chunk_files(self, source_files: dict, chunk_size: int, overlap: int):
        for filepath, content in source_files.items():
            # Simple character-based sliding window chunking
            text = f"File: {filepath}\n{content}"
            start = 0
            while start < len(text):
                end = min(start + chunk_size, len(text))
                chunk = text[start:end]
                self.chunks.append(chunk)
                start += (chunk_size - overlap)

    def _generate_embeddings(self):
        # Check cache for each chunk
        for i, chunk in enumerate(self.chunks):
            chunk_hash = file_hash(chunk)
            cached = self.cache.get(self.repo_tag, chunk_hash)
            
            if cached:
                if self.verbose: print(f"Cache hit for chunk {i}")
                self.embeddings.append(cached['embedding'])
            else:
                try:
                    embedding = embed([chunk])[0]
                    self.embeddings.append(embedding)
                    # Cache the result
                    self.cache.set(self.repo_tag, chunk_hash, {'embedding': embedding})
                except Exception as e:
                    if self.verbose: print(f"Warning: Failed to generate embedding for chunk {i}: {e}")
                    # Append a zero vector as fallback
                    self.embeddings.append([0.0] * 768) # typical dimension, doesn't matter much if zero

    def search(self, query: str, top_k: int = 3) -> List[str]:
        try:
            query_embed = embed([query])[0]
        except Exception as e:
            if self.verbose: print(f"Error embedding query '{query}': {e}")
            return [c for c in self.chunks[:top_k]] # Fallback: return first k chunks
            
        semantic_scores = []
        keyword_scores = []
        
        for i, emb in enumerate(self.embeddings):
            chunk = self.chunks[i]
            
            s_score = cosine_similarity(query_embed, emb)
            k_score = compute_keyword_score(query, chunk)
            
            semantic_scores.append((s_score, i))
            keyword_scores.append((k_score, i))
            
        # Sort by highest score first
        semantic_scores.sort(key=lambda x: x[0], reverse=True)
        keyword_scores.sort(key=lambda x: x[0], reverse=True)
        
        # Hybrid Search via Reciprocal Rank Fusion (RRF)
        # RRF formula: score = 1 / (k + rank)
        rrf_scores = {i: 0.0 for i in range(len(self.chunks))}
        rrf_k = 60
        
        for rank, (score, idx) in enumerate(semantic_scores):
            rrf_scores[idx] += 1.0 / (rrf_k + rank + 1)
            
        for rank, (score, idx) in enumerate(keyword_scores):
            rrf_scores[idx] += 1.0 / (rrf_k + rank + 1)
            
        # Sort chunks by final RRF score
        sorted_indices = sorted(rrf_scores.keys(), key=lambda idx: rrf_scores[idx], reverse=True)
        
        return [self.chunks[idx] for idx in sorted_indices[:top_k]]
