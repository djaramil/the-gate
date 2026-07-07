## Remaining Todos (actionable)

1. Integrate embedding cache into `retrieval.py`
   - Use `EmbeddingCache` to skip re-embedding unchanged files by file-hash or commit hash.

2. Wire `llm_adapter.embed()` into `retrieval.CodeRetriever`
   - Ensure provider detection (LMStudio vs fallback) works at runtime.

3. Implement two-phase LLM evaluation in `llm_eval.py`
   - Phase 1: extract factual observations from top-k chunks.
   - Phase 2: ask model to score each rubric item and cite chunk IDs.

4. Expand AST checker ruleset
   - Add explicit gate-evidence rules: detect Supabase usage, presence of CRUD endpoints, auth patterns, README fields (demo link, Z-number), and deployment link validation.

5. Improve orchestrator (`hc_evaluate.py`)
   - Add `evaluate-latest` local-first mode scanning `submissions/`.
   - Add `--no-llm` dry run for bulk static evaluation.

6. Reporting & Gate Pass decision
   - Implement `report_generator.py` usage to include objective findings + LLM scores and compute a `Gate Pass` boolean based on thresholds.

7. Documentation & examples
   - Update README with LMStudio setup instructions and examples for embedding fallback and how to run the full evaluation.

Priority items: (1) Integrate retrieval embedding cache and adapter, (2) implement two-phase evaluation prompts, (3) expand AST checker for gate evidence.
