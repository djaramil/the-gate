## HootCamp AI Grading — Implementation Plan (LMStudio)

Goal: scaffold a reusable grading agent that evaluates latest submissions in `submissions/`, uses LMStudio (chat) and a local embedding fallback, and scores repos against the gate requirements (see `../the-gate_submission_announcement.md`).

High-level steps
- Create `HootCamp-AI-Grading/` scaffold reusing FullStack-AI-Grading components.
- Add a provider-agnostic `llm_adapter.py` supporting LMStudio and a sentence-transformers fallback for embeddings.
- Implement a JS/TS AST checker (Node script) that finds evidence of AI features, backend/DB, auth, tests, and also flags security items (secondary).
- Implement embedding cache to avoid re-embedding unchanged files.
- Add a minimal orchestrator CLI `hc_evaluate.py` with `evaluate-local` and `dry-run` modes.
- Improve retrieval and LLM evaluation prompts into a two-phase flow (extract facts, then score with evidence).

Config & defaults
- Top-level config: `config.template.json` (JSON, env overrides via `.env`).
- Default LLM provider: `lmstudio` with `qwen-3.6` for chat and `sentence-transformers/all-mpnet-base-v2` as the embedding fallback on Apple M4.

Gate mapping
- The evaluator will map specific gate items to objective checks and LLM-evaluated rubric features (AI integration, backend, auth, README, deployment, demo video, commit hygiene).
