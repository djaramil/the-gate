## Remaining Todos (actionable)

### Phase 0: Submission Ingestion Workflow (High Priority)

1. Implement submission ingestion workflow
   - Parse latest CSV from `submissions/` folder to get repo list
   - Extract/unzip repos from `submissions-1/`, `submissions-2/`, `submissions-3/` into `repos/` folder
   - Clean extracted repos: remove `node_modules/`, `.venv/`, `__pycache__/`, `dist/`, `build/`, `.next/` directories
   - Verify repo structure and skip invalid/incomplete submissions
   - Create `submissions_ingestion.py` to handle this workflow

### Phase 1: Core Integration (High Priority)

2. Copy and adapt `retrieval.py` from FullStack-AI-Grading
   - Replace ollama client with `llm_adapter.embed()`
   - Integrate `EmbeddingCache` to skip re-embedding unchanged files by file-hash
   - Ensure provider detection (LMStudio vs fallback) works at runtime

3. Copy and adapt `llm_eval.py` from FullStack-AI-Grading
   - Replace ollama client with `llm_adapter.chat()`
   - Adapt rubric features to match HootCamp gate requirements
   - Implement two-phase LLM evaluation:
     - Phase 1: extract factual observations from top-k chunks
     - Phase 2: ask model to score each rubric item and cite chunk IDs

4. Copy and adapt `ingestion.py` from FullStack-AI-Grading
   - Ensure it works with local repos in `repos/` directory (from Phase 0)
   - Extract README content for documentation checks

### Phase 2: Gate-Specific Checks (High Priority)

5. Expand AST checker ruleset for gate evidence
   - Add explicit Supabase usage detection (createClient, supabase.auth, supabase.from)
   - Detect CRUD endpoint patterns (insert, select, update, delete operations)
   - Add auth pattern detection (signInWithPassword, signUp, signOut)
   - Add README field extraction (demo link, Z-number, deployment URL)
   - Add deployment link validation (check if URL is live/accessible)

6. Implement README analysis for gate requirements
   - Extract and validate: name, Z-number, FAU email
   - Extract and validate: deployment link
   - Extract and validate: demo video link (3-5 minutes)
   - Check for design/planning documents (wireframes, schema, architecture)

### Phase 3: Orchestrator & Reporting (Medium Priority)

7. Improve orchestrator (`hc_evaluate.py`)
   - Add `evaluate-latest` mode to scan all repos in `repos/` (from Phase 0)
   - Add `--no-llm` dry run for bulk static evaluation (AST + README only)
   - Add `--single-repo` mode for testing individual repos
   - Integrate all phases: ingestion → static analysis → retrieval → LLM eval → reporting

8. Implement Gate Pass decision logic
   - Create `report_generator.py` adapted from FullStack-AI-Grading
   - Define pass/fail thresholds for each gate requirement
   - Compute boolean `Gate Pass` based on:
     - AI integration present (1+ meaningful features)
     - Backend complete (Supabase + CRUD)
     - Authentication implemented
     - README complete (all required fields)
     - Deployment link present and valid
     - Demo video present
     - Commit hygiene (meaningful history, not 1-2 commits)

### Phase 4: Documentation & Testing (Low Priority)

9. Update README with LMStudio setup instructions
   - How to install and configure LMStudio
   - How to load qwen-3.6 model
   - How to configure embedding fallback
   - Example .env file setup

10. Add example usage and testing
   - Example command to evaluate single repo
   - Example command to evaluate all submissions
   - Example output format
   - How to interpret Gate Pass results

Priority items: (1) Implement submission ingestion workflow, (2) integrate retrieval with adapter and cache, (3) adapt llm_eval for gate requirements.
