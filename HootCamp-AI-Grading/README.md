# HootCamp AI Grading

AI-powered grading system for HootCamp submissions. Evaluates student repositories against gate requirements using LMStudio (or mock mode for testing) and static analysis.

## Features

- **Submission Ingestion**: Clone and clean repos from CSV submissions
- **AST Analysis**: JavaScript/TypeScript static analysis for gate evidence
- **LLM Evaluation**: Gate requirement evaluation using LMStudio or FAU TrussedAI
- **Gate Pass Decision**: Automated pass/fail based on gate requirements
- **Embedding Cache**: Efficient caching to avoid re-embedding unchanged files
- **Multi-Provider Support**: Switch between local LMStudio and cloud FAU TrussedAI

## Setup

### 1. Python Dependencies

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Node Dependencies

```bash
npm install
```

### 3. LLM Provider Setup

Choose between LMStudio (local) or FAU TrussedAI (cloud):

#### Option A: LMStudio (Local, Free)

1. Download [LMStudio](https://lmstudio.ai/)
2. Install and open LMStudio
3. Search for and download `qwen/qwen3.6-27b` model
4. Start the LMStudio server (default: http://localhost:1234)

#### Option B: FAU TrussedAI (Cloud)

1. Go to https://trussed.hpc.fau.edu
2. Log in with FAU SSO
3. Select "HootCamp OpenAI" project
4. Request API key and copy it
5. Configure in `.env` (see below)

**Note**: FAU TrussedAI has rate limits. The system automatically retries with exponential backoff (up to 5 retries, max 60s delay) when rate limited.

**Mock Mode**: For testing without LLM, set `MOCK_MODE=true`:
```bash
MOCK_MODE=true python3 hc_evaluate.py evaluate-single --path test-repo
```

### 4. Configuration

Copy `.env.example` to `.env` and configure:

```bash
cp .env.example .env
```

**For LMStudio (local):**
```
LLM_PROVIDER=lmstudio
LMSTUDIO_HOST=http://localhost:1234
LMSTUDIO_MODEL=qwen/qwen3.6-27b
LMSTUDIO_EMBED_MODEL=text-embedding-nomic-embed-text-v1.5
FALLBACK_EMBED_MODEL=sentence-transformers/all-mpnet-base-v2
MOCK_MODE=false
```

**For FAU TrussedAI (cloud):**
```
LLM_PROVIDER=trussedai
TRUSSEDAI_HOST=https://fauengtrussed.fau.edu/provider/generic
MOCK_MODE=false

# API keys for each project (get from https://trussed.hpc.fau.edu)
TRUSSEDAI_OPENAI_API_KEY=your_openai_key_here
TRUSSEDAI_GEMINI_API_KEY=your_gemini_key_here
TRUSSEDAI_HPC_API_KEY=your_hpc_key_here

# Select your project and uncomment the appropriate section:
# HootCamp OpenAI Project
TRUSSEDAI_MODEL=gpt-5.4
TRUSSEDAI_EMBED_MODEL=

# HootCamp Gemini Project  
# TRUSSEDAI_MODEL=gemini-2.5-pro
# TRUSSEDAI_EMBED_MODEL=

# HootCamp HPC Project (local models)
# TRUSSEDAI_MODEL=cogito:14b
# TRUSSEDAI_EMBED_MODEL=nomic-embed-text:v1.5
```

**Available FAU TrussedAI Models by Project:**
- **HootCamp OpenAI**: `gpt-5.4` (requires `TRUSSEDAI_OPENAI_API_KEY`)
- **HootCamp Gemini**: `gemini-2.5-pro` (requires `TRUSSEDAI_GEMINI_API_KEY`)
- **HootCamp HPC** (local models, requires `TRUSSEDAI_HPC_API_KEY`):
  - Chat: `cogito:14b`, `gemma4-vibe`, `ministral-3:14b`, `gemma4:26b`, `lfm2.5-thinking:1.2b`, `rnj-1:8b`, `granite4:350m`, `laguna-xs.2`
  - Embedding: `nomic-embed-text:v1.5`, `nomic-embed-text-v2-moe:latest`, `embeddinggemma:300m`

Each project requires its own API key from https://trussed.hpc.fau.edu. The system automatically selects the correct API key based on the model name. See `docs/FAU-Trussed-AI-Guide.md` for detailed FAU TrussedAI setup.

## Usage

### Ingest Submissions

Clone repos from CSV to `repos/` directory:

```bash
python3 submissions_ingestion.py --csv submissions/week3_submissions_updated.csv
```

Dry run (parse CSV without cloning):
```bash
python3 submissions_ingestion.py --dry-run
```

### Evaluate Single Repository

Full evaluation (AST + LLM):
```bash
python3 hc_evaluate.py evaluate-single --path test-repo
```

AST only (no LLM):
```bash
python3 hc_evaluate.py evaluate-single --path test-repo --no-llm
```

### Evaluate All Repositories

Evaluate all repos in `repos/`:
```bash
python3 hc_evaluate.py evaluate-latest
```

AST only for all repos:
```bash
python3 hc_evaluate.py evaluate-latest --no-llm
```

### Run AST Checker Directly

```bash
node js_ts_ast_checker.js path/to/repo
```

## Gate Requirements

The system evaluates against these gate requirements:

1. **AI Integration** - 1+ meaningful AI-powered features
2. **Backend & Database** - Supabase (or equivalent) with full CRUD operations
3. **Authentication** - User auth with protected routes
4. **Documentation** - README with deployment link + design/planning documents
5. **Deployment** - Live, publicly accessible application
6. **Demo Video** - 3-5 minute video showcasing all features
7. **Commit Hygiene** - Clean code with proper commit history

## Output

Evaluation results include:

- **AST Findings**: Static analysis results (Supabase usage, auth patterns, AI libraries)
- **Gate Evaluations**: LLM-based assessment of each gate requirement
- **Gate Pass Decision**: Boolean pass/fail with detailed reasoning
- **Missing Requirements**: List of unmet gate requirements
- **AST Issues**: Discrepancies between LLM and AST analysis

Results are saved to `results/evaluation_results.json` when using `evaluate-latest`.

## Testing

### Unit Tests

Test AST checker (fast, no LLM required):
```bash
python3 test_ast_checker.py
```

Test gate decision logic (fast, no LLM required):
```bash
python3 test_gate_decision.py
```

### Integration Tests

Test LLM connection:
```bash
python3 test_lmstudio.py
```

List available models:
```bash
python3 list_models.py
```

Performance comparison (LMStudio vs TrussedAI):
```bash
python3 test_llm_performance.py
```

Test retrieval system:
```bash
python3 test_retrieval.py
```

## Architecture

- `submissions_ingestion.py` - CSV parsing and repo cloning
- `ingestion.py` - Source code extraction
- `retrieval.py` - Code chunking and embedding search
- `llm_adapter.py` - LLM provider abstraction (LMStudio/fallback)
- `llm_eval.py` - Gate requirement evaluation
- `js_ts_ast_checker.js` - JavaScript/TypeScript static analysis
- `hc_evaluate.py` - Main orchestrator
- `embedding_cache.py` - Embedding caching system
