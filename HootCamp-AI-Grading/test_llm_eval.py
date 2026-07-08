#!/usr/bin/env python3
"""Test llm_eval.py with test-repo"""

from ingestion import extract_source_code
from retrieval import CodeRetriever
from llm_eval import perform_gate_evaluations

# Test with test-repo
repo_path = "test-repo"
print(f"Extracting source code from {repo_path}...")
source_files = extract_source_code(repo_path)

print(f"Found {len(source_files)} files")

print("\nCreating CodeRetriever...")
retriever = CodeRetriever(source_files, chunk_size=1500, overlap=200, repo_tag="test-repo", verbose=True)

print("\nTesting gate evaluations...")
results = perform_gate_evaluations(retriever, verbose=True, top_k=5)

print("\n=== Gate Evaluation Results ===")
for feature, result in results.items():
    print(f"\n{feature}:")
    print(f"  Present: {result['present']}")
    print(f"  Explanation: {result['explanation'][:200]}..." if len(result['explanation']) > 200 else f"  Explanation: {result['explanation']}")
