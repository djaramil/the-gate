# HootCamp AI Grading - Architecture Document

## System Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         HootCamp AI Grading                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐      │
│  │   Canvas     │───▶│  Submission  │───▶│   Git Clone  │      │
│  │   Export     │    │  Ingestion   │    │   Service    │      │
│  └──────────────┘    └──────────────┘    └──────────────┘      │
│                            │                    │                │
│                            ▼                    ▼                │
│                   ┌──────────────┐    ┌──────────────┐          │
│                   │   CSV Parse  │    │   Repo Clean │          │
│                   └──────────────┘    └──────────────┘          │
│                            │                    │                │
│                            └────────┬───────────┘                │
│                                     │                            │
│                                     ▼                            │
│                          ┌──────────────────┐                  │
│                          │  Source Code      │                  │
│                          │  Extraction       │                  │
│                          └──────────────────┘                  │
│                                     │                            │
│                ┌────────────────────┼────────────────────┐      │
│                ▼                    ▼                    ▼      │
│        ┌──────────────┐    ┌──────────────┐    ┌──────────────┐│
│        │  AST Checker │    │   Code       │    │   README     ││
│        │  (Node.js)   │    │   Chunking   │    │   Analysis   ││
│        └──────────────┘    └──────────────┘    └──────────────┘│
│                │                    │                    │      │
│                ▼                    ▼                    ▼      │
│        ┌──────────────┐    ┌──────────────┐    ┌──────────────┐│
│        │  Static      │    │  Embedding   │    │  Determin-   ││
│        │  Analysis    │    │  Generation  │    │  istic       ││
│        └──────────────┘    └──────────────┘    └──────────────┘│
│                │                    │                    │      │
│                └────────┬───────────┴────────┬───────────┘      │
│                         │                    │                  │
│                         ▼                    ▼                  │
│              ┌──────────────────┐  ┌──────────────────┐        │
│              │  Retrieval       │  │  Cache Layer     │        │
│              │  System          │  │  (Embeddings)    │        │
│              └──────────────────┘  └──────────────────┘        │
│                         │                                      │
│                         ▼                                      │
│              ┌──────────────────┐                              │
│              │  LLM Adapter     │                              │
│              │  (Provider Agnostic)                           │
│              └──────────────────┘                              │
│                         │                                      │
│        ┌────────────────┼────────────────┐                    │
│        ▼                ▼                ▼                    │
│ ┌──────────┐    ┌──────────┐    ┌──────────┐                  │
│ │LMStudio  │    │TrussedAI │    │Fallback  │                  │
│ │(Local)   │    │(Cloud)   │    │Mock Mode │                  │
│ └──────────┘    └──────────┘    └──────────┘                  │
│                         │                                      │
│                         ▼                                      │
│              ┌──────────────────┐                              │
│              │  LLM Evaluation   │                              │
│              │  (Gate Scoring)   │                              │
│              └──────────────────┘                              │
│                         │                                      │
│                         ▼                                      │
│              ┌──────────────────┐                              │
│              │  Deterministic   │                              │
│              │  Overrides       │                              │
│              └──────────────────┘                              │
│                         │                                      │
│                         ▼                                      │
│              ┌──────────────────┐                              │
│              │  Gate Pass       │                              │
│              │  Decision Engine │                              │
│              └──────────────────┘                              │
│                         │                                      │
│                         ▼                                      │
│              ┌──────────────────┐                              │
│              │  Report          │                              │
│              │  Generation      │                              │
│              └──────────────────┘                              │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

## Component Architecture

### 1. Ingestion Layer

**Purpose**: Import and prepare student submissions for evaluation

**Components**:
- `submissions_ingestion.py` - Main ingestion orchestrator
- CSV Parser - Extracts GitHub URLs from Canvas exports
- Git Clone Service - Clones repositories
- Repo Cleaner - Removes unnecessary files
- Repo Validator - Ensures minimum quality standards

**Interfaces**:
```python
def ingest_submissions(csv_path: Optional[Path] = None) -> Dict[str, any]
def parse_submission_csv(csv_path: Path) -> List[Dict[str, str]]
def clone_repo(url: str, target_dir: Path) -> bool
def clean_repo(repo_path: Path) -> None
def validate_repo(repo_path: Path) -> Dict[str, any]
```

**Data Flow**:
```
Canvas CSV → Parse URLs → Git Clone → Clean → Validate → Ready for Evaluation
```

### 2. Source Code Processing Layer

**Purpose**: Extract and prepare code for analysis

**Components**:
- `ingestion.py` - Source code extraction
- File Filter - Selects relevant file types
- README Extractor - Separates documentation
- Content Normalizer - Standardizes text format

**Interfaces**:
```python
def extract_source_code(repo_path: str) -> Dict[str, str]
def extract_readme(repo_path: str) -> str
```

**Data Flow**:
```
Repository → File Filter → Content Extraction → Normalized Code
```

### 3. Static Analysis Layer

**Purpose**: Objective code analysis without LLM

**Components**:
- `js_ts_ast_checker.js` - JavaScript/TypeScript AST parser
- Pattern Matcher - Detects specific code patterns
- Security Scanner - Flags dangerous patterns
- Evidence Collector - Gathers objective findings

**Interfaces**:
```javascript
// Node.js subprocess interface
node js_ts_ast_checker.js <repo_path>
// Returns JSON findings
```

**Detection Categories**:
- Database Libraries (Supabase, Back4App, MongoDB, SQL)
- Authentication Patterns
- AI/ML Libraries
- Security Issues
- CRUD Operations

**Data Flow**:
```
Source Code → AST Parser → Pattern Matching → Evidence Collection → JSON Findings
```

### 4. Retrieval Layer

**Purpose**: Enable semantic search over codebase

**Components**:
- `retrieval.py` - Main retrieval system
- `CodeRetriever` - Chunking and indexing
- `embedding_cache.py` - Caching layer
- Search Engine - Hybrid semantic + keyword search

**Interfaces**:
```python
class CodeRetriever:
    def __init__(source_files: dict, chunk_size: int, overlap: int, verbose: bool, repo_tag: str)
    def search(query: str, top_k: int) -> List[str]

class EmbeddingCache:
    def get(repo_tag: str, chunk_hash: str) -> Optional[Dict]
    def set(repo_tag: str, chunk_hash: str, data: Dict)
```

**Search Architecture**:
```
Query → Embed Query → Semantic Search ─┐
                                      ├→ RRF Fusion → Ranked Results
Query → Tokenize → Keyword Search ────┘
```

**Caching Architecture**:
```
Chunk Content → Hash Function → Cache Key
                                     ↓
                            Cache Lookup
                                     ↓
                            Hit? Return Embedding
                            Miss? Generate & Cache
```

### 5. LLM Integration Layer

**Purpose**: Provider-agnostic LLM interface

**Components**:
- `llm_adapter.py` - Unified LLM interface
- Provider Manager - Selects appropriate provider
- Rate Limit Handler - Exponential backoff
- Connection Tester - Health checks

**Interfaces**:
```python
def chat(system: str, prompt: str, model: str, max_tokens: int, temperature: float, timeout: int) -> Dict
def embed(texts: List[str], model: str) -> List[List[float]]
def test_connection() -> bool
```

**Provider Architecture**:
```
LLM Adapter
    ├── LMStudio Provider (HTTP API)
    ├── TrussedAI Provider (HTTP API)
    └── Fallback Provider (sentence-transformers)
```

**Rate Limiting Architecture**:
```
Request → Try API → 429 Response? → Wait (exponential backoff) → Retry
                      ↓
                 Max retries? → Fail
```

### 6. Evaluation Layer

**Purpose**: Score gate requirements using LLM

**Components**:
- `llm_eval.py` - Gate evaluation engine
- Feature Evaluator - Individual gate scoring
- Prompt Builder - Constructs evaluation prompts
- Response Parser - Extracts structured results

**Interfaces**:
```python
def evaluate_feature(retriever: CodeRetriever, feature_key: str, query: str, verbose: bool, top_k: int) -> FeatureEvaluation
def perform_gate_evaluations(retriever: CodeRetriever, verbose: bool, top_k: int) -> Dict
```

**Evaluation Architecture**:
```
Gate Feature → Query Construction → Retrieval (top-k chunks) → 
Prompt Building → LLM Inference → Response Parsing → Feature Score
```

**Gate Features**:
- `ai_integration` - AI-powered features
- `backend_database` - Database and CRUD
- `authentication` - User authentication
- `readme_completeness` - Documentation quality
- `deployment_live` - Live deployment
- `demo_video_present` - Demo video

### 7. Decision Layer

**Purpose**: Compute final gate pass/fail decisions

**Components**:
- `hc_evaluate.py` - Main orchestrator
- Deterministic Override Engine - Corrects LLM errors
- Gate Decision Engine - Computes pass/fail
- Evidence Aggregator - Combines all evidence

**Interfaces**:
```python
def apply_deterministic_overrides(gate_evaluations: Dict, repo_path: str, ast_findings: List) -> Dict
def compute_gate_pass(gate_evaluations: Dict, ast_findings: List) -> Dict
def evaluate_single_repo(repo_path: str, no_llm: bool, verbose: bool) -> Dict
def evaluate_all_repos(repos_dir: str, no_llm: bool, verbose: bool, resume: bool) -> List[Dict]
```

**Decision Architecture**:
```
LLM Results → Deterministic Overrides → AST Validation → 
Gate Requirements Check → Final Decision
```

**Override Categories**:
- README Field Override - Objective field validation
- Link Override - URL pattern matching
- AI Integration Override - README/AST evidence

### 8. Reporting Layer

**Purpose**: Generate evaluation reports

**Components**:
- `generate_grading_report.py` - Report generator
- CSV Export - Canvas-compatible format
- JSON Export - Detailed results
- Markdown Export - Human-readable reports

**Report Structure**:
```json
{
  "repo_name": "student_repo",
  "repo_path": "/path/to/repo",
  "ast_findings": [...],
  "gate_evaluations": {
    "ai_integration": {"present": true, "explanation": "..."},
    ...
  },
  "gate_pass": true,
  "gate_decision": {
    "gate_pass": true,
    "missing_requirements": [],
    "ast_issues": []
  },
  "timing": {...}
}
```

## Data Architecture

### File System Structure

```
HootCamp-AI-Grading/
├── submissions/              # Canvas CSV exports
│   ├── week3_submissions.csv
│   └── submissions-1.zip
├── repos/                    # Cloned repositories
│   ├── student1_repo1/
│   ├── student2_repo2/
│   └── ...
├── cache/                    # Embedding cache
│   └── embeddings.json
├── results/                  # Evaluation results
│   ├── evaluation_results.json
│   ├── grading_report.csv
│   └── .evaluation_status
├── docs/                     # Documentation
├── tools/                    # Utility scripts
└── *.py                      # Core modules
```

### Data Models

#### Submission Model
```python
{
    "student_name": str,
    "email": str,
    "url": str,  # GitHub URL
    "html_file": str,
    "repo_name": str  # Derived
}
```

#### AST Finding Model
```python
{
    "code": str,  # Finding type
    "message": str,
    "file": str,
    "line": int
}
```

#### Gate Evaluation Model
```python
{
    "present": bool,
    "explanation": str,
    "override": str,  # Optional override source
    "evidence": List[str]  # Optional evidence list
}
```

#### Gate Decision Model
```python
{
    "gate_pass": bool,
    "missing_requirements": List[str],
    "ast_issues": List[str],
    "has_supabase": bool,
    "has_back4app": bool,
    "has_mongodb": bool,
    "has_sql_db": bool,
    "has_auth_lib": bool,
    "has_ai_lib": bool,
    "has_js_ts_files": bool
}
```

#### Evaluation Result Model
```python
{
    "repo_name": str,
    "repo_path": str,
    "ast_findings": List[ASTFinding],
    "gate_evaluations": Dict[str, GateEvaluation],
    "gate_pass": bool,
    "gate_decision": GateDecision,
    "readme_analysis": Dict,
    "timing": Dict[str, str]
}
```

## Communication Patterns

### Synchronous Communication

**Python → Node.js (AST Checker)**
- Mechanism: Subprocess with JSON stdout
- Protocol: Single request-response
- Timeout: 30 seconds
- Error Handling: JSON parsing with fallback

**Python → LLM Providers**
- Mechanism: HTTP REST API
- Protocol: OpenAI-compatible API
- Timeout: Dynamic (90-300 seconds based on code size)
- Retry: Exponential backoff (max 5 retries)

### Asynchronous Communication

**Batch Evaluation**
- Mechanism: Sequential processing with checkpointing
- Protocol: File-based checkpoint (JSON)
- Resume: Load checkpoint, skip completed repos
- Progress: Real-time status file updates

## Configuration Architecture

### Configuration Hierarchy

```
1. Environment Variables (.env) - Highest priority
2. Configuration Template (config.template.json)
3. Default Values in Code - Lowest priority
```

### Configuration Categories

**LLM Provider Configuration**
- Provider selection (lmstudio/trussedai)
- Model selection
- API endpoints
- Authentication keys

**Evaluation Configuration**
- Chunk size and overlap
- Top-k retrieval count
- Timeout values
- Gate requirements

**Cache Configuration**
- Cache directory
- Cache expiration
- Cache key strategy

## Error Handling Architecture

### Error Categories

**Ingestion Errors**
- Git clone failures
- Invalid repository structure
- CSV parsing errors
- File system errors

**LLM Errors**
- Connection failures
- Rate limiting
- Timeout errors
- Malformed responses

**AST Errors**
- Parse errors
- Unsupported language
- File access errors

### Error Handling Strategy

**Graceful Degradation**
- LLM failures → Fallback to AST only
- Embedding failures → Zero vector fallback
- AST failures → Rely on LLM only
- Parse errors → Skip file, continue

**Error Recovery**
- Retry with exponential backoff (LLM)
- Checkpoint/resume (batch evaluation)
- Fallback regex parsing (LLM responses)
- Partial results reporting

**Error Reporting**
- Structured error messages
- Error context preservation
- User-friendly error summaries
- Detailed error logs

## Performance Architecture

### Performance Optimization

**Caching Strategy**
- File-hash based embedding cache
- Avoids re-embedding unchanged files
- Significant speedup for re-runs

**Chunking Strategy**
- Optimal chunk size: 1500 characters
- Overlap: 200 characters
- Balances context and granularity

**Search Optimization**
- Hybrid search (semantic + keyword)
- Reciprocal Rank Fusion
- Top-k retrieval limits

**Batch Processing**
- Shallow git clones (--depth 1)
- Parallel processing (future enhancement)
- Checkpoint/resume for long runs

### Performance Metrics

**Single Repo Evaluation**
- AST Analysis: 2-5 seconds
- Source Extraction: 1-2 seconds
- Index Building: 5-10 seconds
- LLM Evaluation: 60-120 seconds
- Gate Decision: <1 second
- **Total: 2-3 minutes**

**Batch Evaluation**
- Average per repo: ~3 minutes
- Cache hit speedup: 40-60%
- Checkpoint overhead: <1 second

## Security Architecture

### Security Layers

**Input Validation**
- CSV parsing validation
- GitHub URL validation
- File path sanitization
- Content size limits

**Execution Safety**
- No code execution from repos
- Read-only file operations
- Subprocess timeout enforcement
- AST parsing (no evaluation)

**Credential Management**
- Environment variable storage
- Gitignored .env file
- No hardcoded credentials
- Provider-specific API keys

**Dependency Security**
- Pinned dependency versions
- Regular security updates
- Trusted package registries
- Vulnerability scanning

## Scalability Architecture

### Current Scalability

**Single Machine**
- 10-20 repos per hour
- Limited by LLM inference speed
- Memory efficient (embedding cache)

**Bottlenecks**
- LLM inference time
- Sequential processing
- Network latency (git clone)

### Future Scalability

**Horizontal Scaling**
- Worker pool for parallel repo evaluation
- Distributed LLM inference
- Shared cache storage (Redis)

**Vertical Scaling**
- GPU acceleration for embeddings
- More powerful LLM models
- Increased memory for larger caches

**Process Optimization**
- Incremental evaluation (changed repos only)
- Pre-computed embeddings for common patterns
- Streaming evaluation (real-time updates)

## Monitoring Architecture

### Progress Monitoring

**Real-time Status**
- `.evaluation_status` file updates
- Progress percentage
- Current repo being processed
- ETA calculation

**Performance Metrics**
- Per-phase timing
- Token usage tracking
- Cache hit rates
- Error rates

### Logging Strategy

**Log Levels**
- INFO: Normal operations
- WARNING: Non-critical issues
- ERROR: Failures requiring attention
- DEBUG: Detailed troubleshooting

**Log Categories**
- Ingestion logs
- LLM interaction logs
- Cache performance logs
- Error logs

## Deployment Architecture

### Development Environment

**Local Development**
- LMStudio for local LLM
- Virtual environment for Python
- npm for Node.js dependencies
- Git for version control

**Configuration**
- `.env` for local settings
- Mock mode for testing
- Test repository for validation

### Production Environment

**Deployment Options**
- Local machine (current)
- Cloud VM (future)
- Containerized deployment (future)

**Requirements**
- Python 3.8+
- Node.js 16+
- LLM provider access
- Sufficient disk space for repos

## Integration Architecture

### External System Integration

**Canvas LMS**
- Input: CSV exports
- Output: Grade CSV uploads
- Format: Standard Canvas grade format

**GitHub**
- Git clone operations
- Repository access
- Rate limit handling

**LLM Providers**
- LMStudio (local)
- FAU TrussedAI (cloud)
- OpenAI API (compatible)

### Future Integrations

**Canvas API**
- Direct grade submission
- Real-time submission retrieval
- Automated feedback posting

**CI/CD Integration**
- GitHub Actions integration
- Automated evaluation on PR
- Continuous grading

**Learning Management Systems**
- Other LMS platforms
- Standard grade export formats
- API-based integration

## Technology Stack

### Core Technologies

**Python**
- Version: 3.8+
- Key Libraries: requests, python-dotenv, sentence-transformers

**Node.js**
- Version: 16+
- Key Libraries: @babel/parser, @babel/traverse

**LLM Providers**
- LMStudio (local inference)
- FAU TrussedAI (cloud)
- sentence-transformers (fallback)

### Supporting Technologies

**Git**
- Repository cloning
- Version control
- Shallow clone optimization

**Data Processing**
- CSV parsing
- JSON serialization
- Text processing

**Caching**
- File-based JSON cache
- Hash-based keys
- Lazy loading

## Conclusion

The HootCamp AI Grading system architecture is designed for modularity, scalability, and maintainability. The layered approach separates concerns and allows for independent component evolution. The hybrid evaluation strategy combines the strengths of static analysis and LLM evaluation while mitigating their individual weaknesses. The architecture supports both current operational needs and future enhancements, making it a robust foundation for automated code evaluation in educational settings.
