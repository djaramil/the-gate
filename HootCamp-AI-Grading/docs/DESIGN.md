# HootCamp AI Grading - Design Document

## Overview

The HootCamp AI Grading system is an automated evaluation platform designed to assess student project submissions against specific gate requirements. The system combines static analysis, large language model (LLM) evaluation, and deterministic checks to provide comprehensive grading feedback.

### Problem Statement

Manual grading of student coding projects is time-consuming and subjective. Instructors need to evaluate multiple gate requirements across dozens of submissions, including:
- AI integration quality
- Backend/database implementation
- Authentication systems
- Documentation completeness
- Deployment status
- Demo video presence
- Code quality and commit hygiene

### Solution

An automated grading pipeline that:
1. **Ingests submissions** from Canvas CSV exports
2. **Performs static analysis** using AST (Abstract Syntax Tree) parsing
3. **Evaluates code semantically** using LLMs with retrieval-augmented generation
4. **Applies deterministic overrides** for objective checks (URLs, file presence)
5. **Computes gate pass/fail decisions** based on comprehensive criteria
6. **Generates detailed reports** for each submission

## System Design

### Core Components

#### 1. Submission Ingestion (`submissions_ingestion.py`)
**Purpose**: Parse Canvas CSV exports and clone student repositories

**Design Decisions**:
- Uses CSV parsing to extract GitHub URLs from Canvas exports
- Implements shallow git clones (`--depth 1`) for performance
- Removes unnecessary directories (`node_modules`, `.venv`, etc.) to save space
- Validates repository structure before processing

**Key Functions**:
- `find_latest_csv()`: Automatically selects most recent submission file
- `parse_submission_csv()`: Extracts student metadata and GitHub URLs
- `clone_repo()`: Git cloning with timeout and error handling
- `clean_repo()`: Removes build artifacts and dependencies
- `validate_repo()`: Ensures minimum file count and structure

#### 2. Source Code Ingestion (`ingestion.py`)
**Purpose**: Extract relevant source files from repositories

**Design Decisions**:
- Filters by file extensions (`.js`, `.jsx`, `.ts`, `.tsx`, `.py`, `.html`, `.css`, `.md`)
- Skips common ignore directories (`.git`, `node_modules`, etc.)
- Extracts README content separately for documentation checks

**Key Functions**:
- `extract_source_code()`: Returns dictionary of filepath → content
- `extract_readme()`: Retrieves README.md content for analysis

#### 3. Code Retrieval System (`retrieval.py`)
**Purpose**: Enable semantic search over codebase using embeddings

**Design Decisions**:
- Uses sliding window chunking (1500 chars with 200 char overlap)
- Implements hybrid search: semantic similarity + keyword matching
- Uses Reciprocal Rank Fusion (RRF) for combining search signals
- Caches embeddings to avoid re-computation

**Key Functions**:
- `CodeRetriever.__init__()`: Chunks files and generates embeddings
- `CodeRetriever.search()`: Hybrid semantic + keyword search
- `cosine_similarity()`: Vector similarity computation
- `compute_keyword_score()`: Frequency-based keyword matching

**Caching Strategy**:
- File-hash based caching in `embedding_cache.py`
- Avoids re-embedding unchanged files across evaluations
- Significant performance improvement for batch processing

#### 4. LLM Adapter (`llm_adapter.py`)
**Purpose**: Provider-agnostic interface for LLM operations

**Design Decisions**:
- Supports multiple providers: LMStudio (local) and FAU TrussedAI (cloud)
- Implements automatic fallback for embeddings
- Includes mock mode for testing without LLM
- Handles rate limiting with exponential backoff

**Provider Support**:
- **LMStudio**: Local inference using qwen/qwen3.6-27b
- **FAU TrussedAI**: Cloud access to GPT-5.4, Gemini-2.5-pro, and local models
- **Fallback**: sentence-transformers/all-mpnet-base-v2 for embeddings

**Key Functions**:
- `chat()`: Unified chat completion interface
- `embed()`: Embedding generation with provider selection
- `test_connection()`: Health check for configured provider
- `get_trussedai_api_key()`: Automatic API key selection based on model

**Rate Limiting**:
- Max 5 retries with exponential backoff
- Initial delay: 2s, max delay: 60s
- Automatic retry on HTTP 429 responses

#### 5. LLM Evaluation (`llm_eval.py`)
**Purpose**: Evaluate gate requirements using LLM analysis

**Design Decisions**:
- Two-phase evaluation: retrieval → analysis
- Uses strict JSON prompts for consistent output
- Implements dynamic timeout based on code size
- Includes fallback regex parsing for malformed responses

**Gate Features Evaluated**:
- `ai_integration`: AI-powered features and LLM usage
- `backend_database`: Database integration and CRUD operations
- `authentication`: User authentication and protected routes
- `readme_completeness`: Documentation quality and completeness
- `deployment_live`: Live deployment status
- `demo_video_present`: Demo video availability

**Key Functions**:
- `evaluate_feature()`: Single gate evaluation with retrieval
- `perform_gate_evaluations()`: Batch evaluation of all gates
- `FeatureEvaluation`: Data class for evaluation results

**Prompt Engineering**:
- System prompt: "You are a code analysis expert. Always respond with valid JSON."
- Structured prompt with clear evaluation criteria
- Requests specific evidence from code (file names, function names)

#### 6. AST Checker (`js_ts_ast_checker.js`)
**Purpose**: Static analysis for JavaScript/TypeScript codebases

**Design Decisions**:
- Uses Babel parser for JavaScript/TypeScript
- Traverses AST to detect specific patterns
- Provides objective evidence complementary to LLM analysis
- Runs as Node.js subprocess from Python orchestrator

**Detection Patterns**:
- **Supabase**: `createClient`, `supabase.auth`, `supabase.from`
- **Back4App**: Parse SDK imports and usage
- **MongoDB**: MongoDB driver imports and operations
- **SQL/ORM**: Prisma, Drizzle, Neon, pg libraries
- **Authentication**: Auth libraries and patterns
- **AI Integration**: OpenAI, Anthropic, Gemini SDK usage
- **Security**: Dangerous patterns (eval, child_process)

**Output Format**:
```json
{
  "repo": "repository_name",
  "findings": [
    {
      "code": "SUPABASE_CLIENT",
      "message": "Supabase client initialization",
      "file": "src/db/supabase.js",
      "line": 10
    }
  ]
}
```

#### 7. Main Orchestrator (`hc_evaluate.py`)
**Purpose**: Coordinate all evaluation phases

**Design Decisions**:
- Three-phase evaluation: AST → LLM → Gate Decision
- Implements deterministic overrides to correct LLM false negatives
- Supports both single-repo and batch evaluation
- Includes checkpoint/resume functionality for batch processing

**Evaluation Pipeline**:
1. **Phase 1 - AST Analysis**: Run static analysis checker
2. **Phase 2 - LLM Evaluation**: 
   - Extract source code
   - Build retrieval index
   - Evaluate each gate requirement
   - Apply deterministic overrides
3. **Phase 3 - Gate Decision**: Compute pass/fail based on all evidence

**Deterministic Overrides**:
- `apply_readme_override()`: Field-based README validation
- `apply_link_overrides()`: URL validation for deployment/demo
- `apply_ai_override()`: AI integration detection from README/AST

**Gate Pass Logic**:
- Must-have gates: AI integration, backend/database, authentication, README, deployment, demo video
- AST validation for JS/TS projects (database, auth, AI libraries)
- Fails if any must-have gate is missing or AST validation fails

**CLI Commands**:
- `evaluate-single --path <repo>`: Evaluate single repository
- `evaluate-latest --repos-dir <dir>`: Batch evaluation with checkpointing
- `--no-llm`: AST-only mode for fast static analysis
- `--resume`: Resume from existing checkpoint

### Data Flow

```
Canvas CSV → Submission Ingestion → Git Clone → Clean → Validate
                                                          ↓
Source Code → Ingestion → File Extraction → Chunking → Embeddings
                                                          ↓
                                              Retrieval System
                                                          ↓
                                              LLM Evaluation
                                                          ↓
                                              AST Analysis
                                                          ↓
                                              Deterministic Overrides
                                                          ↓
                                              Gate Pass Decision
                                                          ↓
                                              Report Generation
```

### Configuration Management

**Environment Variables** (`.env`):
- `LLM_PROVIDER`: lmstudio or trussedai
- `LMSTUDIO_HOST`: Local LMStudio server URL
- `LMSTUDIO_MODEL`: Chat model name
- `LMSTUDIO_EMBED_MODEL`: Embedding model name
- `FALLBACK_EMBED_MODEL`: Fallback embedding model
- `MOCK_MODE`: Enable mock responses for testing
- `TRUSSEDAI_HOST`: FAU TrussedAI endpoint
- `TRUSSEDAI_MODEL`: Selected TrussedAI model
- `TRUSSEDAI_*_API_KEY`: Project-specific API keys

**Configuration File** (`config.template.json`):
- Template for JSON-based configuration
- Environment variables override template values

## Technical Decisions

### Why Hybrid Search (Semantic + Keyword)?

**Rationale**: Pure semantic search can miss exact keyword matches, while pure keyword search misses semantic context. Hybrid search combines both for better retrieval.

**Implementation**: Reciprocal Rank Fusion (RRF) combines rankings from both methods:
```
score = 1 / (k + rank_semantic) + 1 / (k + rank_keyword)
```

### Why Deterministic Overrides?

**Rationale**: LLMs can produce false negatives due to context limits or interpretation issues. Deterministic checks for objective criteria (URLs, file presence) provide reliable corrections.

**Examples**:
- README field validation (name, email, Z-number)
- URL pattern matching for deployment links
- AST-based library detection

### Why AST Analysis + LLM?

**Rationale**: 
- AST provides objective, fast detection of specific patterns
- LLM provides semantic understanding of implementation quality
- Combining both reduces false positives/negatives

**Trade-off**: AST is language-specific (currently JS/TS only), while LLM is language-agnostic but slower.

### Why Embedding Cache?

**Rationale**: Re-embedding unchanged files is wasteful. File-hash based caching provides significant speedup for batch evaluation and re-runs.

**Implementation**: 
- Cache key: `repo_tag + file_hash(content)`
- Cache storage: JSON file in `cache/` directory
- Cache hit: Return stored embedding immediately

### Why Multiple LLM Providers?

**Rationale**: 
- LMStudio: Free, local, no rate limits, but requires hardware
- TrussedAI: Cloud-based, more powerful models, but has rate limits
- Flexibility to choose based on use case and resources

### Why Checkpoint/Resume?

**Rationale**: Batch evaluation of many repos can take hours. Checkpointing allows resuming from failures without re-processing completed repos.

**Implementation**: 
- Save after each repo to `results/evaluation_results.json`
- Load existing results on resume
- Skip completed repos, re-process failed repos

## Performance Considerations

### Optimization Strategies

1. **Shallow Git Clones**: `--depth 1` reduces clone time and space
2. **Embedding Cache**: Avoid re-embedding unchanged files
3. **Chunking Strategy**: 1500 char chunks with 200 char overlap balances context and granularity
4. **Dynamic Timeouts**: Scale LLM timeout based on code size
5. **Parallel Processing**: Future enhancement for concurrent repo evaluation

### Bottlenecks

1. **LLM Inference**: Slowest component, especially with large codebases
2. **Embedding Generation**: Computationally expensive, mitigated by caching
3. **Git Cloning**: Network-dependent, uses shallow clones to reduce impact

### Scalability

**Current Capacity**: 
- Single-repo evaluation: 2-5 minutes (depending on codebase size)
- Batch evaluation: ~3 minutes/repo average

**Scaling Options**:
- Parallel repo evaluation with worker pool
- Distributed LLM inference
- Incremental evaluation (only changed repos)

## Security Considerations

### Code Execution Safety

- No code execution from student repositories
- AST analysis is read-only
- LLM evaluation uses text representation only

### API Key Management

- API keys stored in `.env` file (gitignored)
- Different keys for different TrussedAI projects
- No hardcoded credentials in source code

### Dependency Security

- Uses pinned dependency versions where possible
- Regular updates for security patches
- Node.js dependencies from npm registry

## Testing Strategy

### Unit Tests

- `test_ast_checker.py`: AST pattern detection
- `test_gate_decision.py`: Gate pass logic
- `test_llm_eval.py`: LLM evaluation prompts
- `test_retrieval.py`: Search and retrieval

### Integration Tests

- `test_lmstudio.py`: LLM provider connection
- `test_llm_performance.py`: Provider comparison
- Full workflow test: ingestion → evaluation → reporting

### Test Data

- `test-repo/`: Sample repository for testing
- Mock CSV files for ingestion testing
- Invalid submissions for edge case testing

## Future Enhancements

### Short-term

1. **Multi-language AST Support**: Python, Java, Go AST checkers
2. **Parallel Batch Processing**: Concurrent repo evaluation
3. **Web Interface**: Dashboard for viewing results
4. **Export Formats**: CSV, PDF, HTML reports

### Long-term

1. **ML-based Scoring**: Train models on human-graded examples
2. **Plagiarism Detection**: Code similarity analysis
3. **Feedback Generation**: Specific improvement suggestions
4. **Integration with Canvas**: Automatic grade posting

## Conclusion

The HootCamp AI Grading system successfully automates the evaluation of student coding projects by combining static analysis, LLM evaluation, and deterministic checks. The modular design allows for easy extension and modification, while the hybrid approach ensures both accuracy and efficiency. The system has been designed with scalability, security, and maintainability in mind, making it suitable for ongoing use in educational settings.
