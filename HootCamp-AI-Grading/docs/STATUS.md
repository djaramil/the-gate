## Current Status

- Scaffold created: `HootCamp-AI-Grading/` with core helpers and adapters.  (Completed)
- `llm_adapter.py` and `embedding_cache.py` implemented. (Completed)
- Node AST checker implemented and tested locally (`js_ts_ast_checker.js`). (Completed)
- Embedding smoke test with `all-mpnet-base-v2` succeeded on your machine. (Completed)

In progress / next actions
- Integrate AST checker output into the orchestrator/report pipeline (`hc_check_js_ts.py` is present; integrate deeply). (In progress)
- Wire `retrieval.py` to call `llm_adapter.embed()` and `EmbeddingCache` when building chunk embeddings. (Not started)
- Implement two-phase LLM evaluation prompts in `llm_eval.py` and enforce JSON schema outputs. (Not started)
- Add gate-specific evidence detection rules to the AST checker and README checks. (Not started)
- Add optional sandboxed unit-test runner (gated feature). (Blocked/optional)

Tests to run locally
- `python hc_evaluate.py evaluate-local --path ../submissions` (dry static run)
- Embedding test (already run by you): `python test_embed.py` in scaffold.
