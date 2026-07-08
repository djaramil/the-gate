#!/usr/bin/env python3
"""Test retrieval.py with test-repo"""

from ingestion import extract_source_code
from retrieval import CodeRetriever

# Test with test-repo
repo_path = "test-repo"
print(f"Extracting source code from {repo_path}...")
source_files = extract_source_code(repo_path)

print(f"Found {len(source_files)} files")
for filepath in list(source_files.keys())[:5]:
    print(f"  - {filepath}")

print("\nCreating CodeRetriever...")
retriever = CodeRetriever(source_files, chunk_size=1500, overlap=200, repo_tag="test-repo", verbose=True)

print("\nTesting search...")
query = "authentication login"
results = retriever.search(query, top_k=3)

print(f"\nTop 3 chunks for query '{query}':")
for i, chunk in enumerate(results):
    print(f"\n--- Chunk {i} ---")
    print(chunk[:500] + "..." if len(chunk) > 500 else chunk)
