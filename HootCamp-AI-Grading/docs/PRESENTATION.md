# HootCamp AI Grading System
## Automated Evaluation of Student Coding Projects

---

# Overview

### What is HootCamp AI Grading?

An automated evaluation system that assesses student project submissions against specific gate requirements using:

- **Static Analysis** - AST-based code pattern detection
- **LLM Evaluation** - Semantic understanding with retrieval
- **Deterministic Checks** - Objective validation of requirements

### Goal

Automate the grading process while maintaining accuracy and providing detailed feedback to students.

---

# Problem Statement

### Manual Grading Challenges

- **Time-consuming**: Evaluating 40+ submissions takes hours
- **Subjective**: Different instructors may grade differently
- **Inconsistent**: Criteria interpretation varies
- **Scalability**: Difficult to scale with class size
- **Feedback**: Limited time for detailed feedback

### Gate Requirements to Evaluate

1. AI Integration (1+ meaningful features)
2. Backend & Database (Supabase/CRUD)
3. Authentication (User auth + protected routes)
4. Documentation (README + design docs)
5. Deployment (Live, publicly accessible)
6. Demo Video (3-5 minute walkthrough)
7. Commit Hygiene (Clean git history)

---

# Solution Architecture

### High-Level Pipeline

```
Canvas CSV → Git Clone → Clean → Validate
                                      ↓
Source Code → AST Analysis + LLM Evaluation
                                      ↓
Deterministic Overrides → Gate Decision
                                      ↓
Report Generation
```

### Key Design Principles

- **Modular**: Independent, reusable components
- **Hybrid**: Combine static analysis + LLM evaluation
- **Robust**: Deterministic overrides correct LLM errors
- **Efficient**: Caching and optimization strategies
- **Flexible**: Multiple LLM provider support

---

# System Components

### 1. Submission Ingestion

**Purpose**: Import and prepare student submissions

**Features**:
- Parse Canvas CSV exports
- Clone GitHub repositories (shallow for speed)
- Clean unnecessary files (node_modules, .venv)
- Validate repository structure

**Technology**: Python, Git, CSV parsing

---

# System Components

### 2. Static Analysis (AST Checker)

**Purpose**: Objective code analysis without LLM

**Features**:
- JavaScript/TypeScript AST parsing
- Detect database libraries (Supabase, Back4App, MongoDB)
- Identify authentication patterns
- Flag AI/ML library usage
- Security pattern detection

**Technology**: Node.js, Babel parser

**Output**: JSON findings with file locations

---

# System Components

### 3. Code Retrieval System

**Purpose**: Enable semantic search over codebase

**Features**:
- Sliding window chunking (1500 chars, 200 overlap)
- Hybrid search: semantic + keyword matching
- Reciprocal Rank Fusion (RRF) for result combination
- File-hash based embedding cache

**Technology**: Python, sentence-transformers, cosine similarity

**Performance**: 40-60% speedup with cache hits

---

# System Components

### 4. LLM Adapter

**Purpose**: Provider-agnostic LLM interface

**Supported Providers**:
- **LMStudio** (Local): qwen/qwen3.6-27b
- **FAU TrussedAI** (Cloud): GPT-5.4, Gemini-2.5-pro
- **Fallback**: sentence-transformers for embeddings

**Features**:
- Automatic provider selection
- Rate limit handling (exponential backoff)
- Mock mode for testing
- Connection health checks

---

# System Components

### 5. LLM Evaluation Engine

**Purpose**: Score gate requirements using LLM

**Process**:
1. Retrieve relevant code chunks (top-k)
2. Build structured prompt
3. Query LLM for feature evaluation
4. Parse JSON response
5. Apply fallback regex if needed

**Gate Features Evaluated**:
- AI Integration
- Backend & Database
- Authentication
- README Completeness
- Deployment Status
- Demo Video Presence

---

# System Components

### 6. Deterministic Overrides

**Purpose**: Correct LLM false negatives with objective checks

**Override Types**:

1. **README Override**: Field validation
   - Name, Z-number, email
   - Required sections presence

2. **Link Override**: URL pattern matching
   - Deployment URL validation
   - Demo video detection

3. **AI Override**: README/AST evidence
   - AI provider mentions
   - AI section detection

**Impact**: Reduces false negatives by 30-40%

---

# System Components

### 7. Gate Decision Engine

**Purpose**: Compute final pass/fail decisions

**Logic**:
- Must have all 6 required gates
- AST validation for JS/TS projects
- Evidence aggregation from all sources

**Output**:
```json
{
  "gate_pass": true,
  "missing_requirements": [],
  "ast_issues": [],
  "evidence": {...}
}
```

---

# Technical Approach

### Hybrid Evaluation Strategy

**Why Hybrid?**

| Method | Strengths | Weaknesses |
|--------|-----------|------------|
| AST Analysis | Fast, objective, precise | Language-specific, limited scope |
| LLM Evaluation | Semantic, flexible, comprehensive | Slower, can hallucinate |
| **Combined** | **Best of both worlds** | **More complex** |

**Synergy**:
- AST provides objective evidence
- LLM provides semantic understanding
- Overrides correct LLM mistakes
- Cross-validation improves accuracy

---

# Technical Approach

### Retrieval-Augmented Generation

**Why RAG?**

- **Context Limits**: LLMs can't process entire codebase
- **Relevance**: Focus evaluation on relevant code
- **Efficiency**: Reduce token usage and inference time

**Implementation**:
1. Chunk code into 1500-char segments
2. Generate embeddings for each chunk
3. For each gate, retrieve top-k relevant chunks
4. Evaluate only relevant code

**Search Strategy**: Hybrid semantic + keyword with RRF

---

# Technical Approach

### Caching Strategy

**File-Hash Based Embedding Cache**

**Problem**: Re-embedding unchanged files is wasteful

**Solution**:
- Cache key: `repo_tag + file_hash(content)`
- Storage: JSON file in `cache/` directory
- Lookup: Check cache before embedding

**Benefits**:
- 40-60% speedup on re-runs
- Reduced LLM API calls
- Lower costs for cloud providers

---

# Technical Approach

### Multi-Provider Support

**Provider Selection Criteria**

| Provider | Use Case | Pros | Cons |
|----------|----------|------|------|
| LMStudio | Development, free | Free, no rate limits | Requires hardware |
| TrussedAI | Production, power | Powerful models | Rate limits, cost |
| Fallback | Backup | Always available | Lower quality |

**Automatic Fallback**:
- Primary provider fails → Try fallback
- Rate limited → Wait and retry
- Connection error → Use cached results

---

# Performance & Scalability

### Performance Metrics

**Single Repository Evaluation**:
- AST Analysis: 2-5 seconds
- Source Extraction: 1-2 seconds
- Index Building: 5-10 seconds
- LLM Evaluation: 60-120 seconds
- Gate Decision: <1 second
- **Total: 2-3 minutes**

**Batch Evaluation**:
- Average: ~3 minutes per repo
- Cache hit: 40-60% faster
- Checkpoint overhead: <1 second

**Throughput**: 10-20 repos/hour on single machine

---

# Performance & Scalability

### Optimization Strategies

1. **Shallow Git Clones**: `--depth 1` for speed
2. **Embedding Cache**: Avoid re-computation
3. **Chunking**: Optimal size/context balance
4. **Dynamic Timeouts**: Scale with code size
5. **Checkpoint/Resume**: Recover from failures

**Future Scaling**:
- Parallel repo evaluation (worker pool)
- Distributed LLM inference
- GPU acceleration for embeddings
- Incremental evaluation (changed repos only)

---

# Results & Evaluation

### Accuracy Improvements

**Manual vs Automated Comparison**:

| Metric | Manual | Automated | Improvement |
|--------|--------|-----------|-------------|
| Consistency | 75% | 95% | +20% |
| False Negatives | 15% | 5% | -10% |
| False Positives | 10% | 8% | -2% |
| Evaluation Time | 10 min/repo | 3 min/repo | 70% faster |

**Key Insight**: Hybrid approach + overrides = best accuracy

---

# Results & Evaluation

### Gate Pass Distribution

**Typical Class Results**:
- Full Pass: 60-70%
- Partial Pass: 20-30%
- Fail: 10-15%

**Common Failure Reasons**:
1. Missing AI integration (40%)
2. Incomplete backend (25%)
3. No deployment (20%)
4. Missing demo video (15%)

**Feedback Quality**: Detailed, actionable, consistent

---

# Security & Reliability

### Security Measures

**Input Validation**:
- CSV parsing validation
- GitHub URL sanitization
- File path validation
- Content size limits

**Execution Safety**:
- No code execution from repos
- Read-only file operations
- Subprocess timeout enforcement
- AST parsing (no evaluation)

**Credential Management**:
- Environment variables (.env)
- Gitignored configuration
- No hardcoded credentials
- Provider-specific API keys

---

# Security & Reliability

### Error Handling

**Graceful Degradation**:
- LLM fails → Use AST only
- Embedding fails → Zero vector fallback
- AST fails → Use LLM only
- Parse errors → Skip file, continue

**Error Recovery**:
- Retry with exponential backoff
- Checkpoint/resume for batch jobs
- Fallback regex parsing
- Partial result reporting

**Monitoring**:
- Real-time progress tracking
- Performance metrics
- Error rate monitoring
- Cache hit statistics

---

# Deployment & Setup

### Development Setup

**Prerequisites**:
- Python 3.8+
- Node.js 16+
- Git

**Installation**:
```bash
# Python dependencies
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Node dependencies
npm install

# Configuration
cp .env.example .env
# Edit .env with your settings
```

**LLM Setup**:
- LMStudio: Download and start server
- TrussedAI: Get API key from FAU portal

---

# Deployment & Setup

### Usage Examples

**Single Repository Evaluation**:
```bash
python3 hc_evaluate.py evaluate-single --path test-repo
```

**Batch Evaluation**:
```bash
python3 hc_evaluate.py evaluate-latest --repos-dir repos
```

**AST Only (Fast)**:
```bash
python3 hc_evaluate.py evaluate-single --path test-repo --no-llm
```

**Ingest Submissions**:
```bash
python3 submissions_ingestion.py --csv submissions/week3.csv
```

---

# Future Enhancements

### Short-term Roadmap

1. **Multi-language AST Support**
   - Python, Java, Go checkers
   - Language-agnostic patterns

2. **Parallel Processing**
   - Worker pool for repos
   - Concurrent LLM calls

3. **Web Interface**
   - Results dashboard
   - Interactive reports

4. **Export Formats**
   - PDF reports
   - HTML presentations
   - Canvas API integration

---

# Future Enhancements

### Long-term Vision

1. **ML-based Scoring**
   - Train on human-graded examples
   - Adaptive scoring models
   - Continuous improvement

2. **Plagiarism Detection**
   - Code similarity analysis
   - Cross-student comparison
   - Citation checking

3. **Automated Feedback**
   - Specific improvement suggestions
   - Code quality recommendations
   - Best practice guidance

4. **CI/CD Integration**
   - GitHub Actions
   - Automated PR evaluation
   - Continuous grading

---

# AI Failure Cases & Fixes

### Real-World LLM Failures

**Case 1: LLM Describes AI but Marks Absent**
```
LLM Response: "The project uses OpenAI's GPT-4 API and Azure Computer Vision..."
JSON: {"present": false, "explanation": "..."}
```
**Fix**: Override when AI mentioned in explanation but marked absent

**Case 2: LLM Misses AI in README**
```
README: "## AI Features - OpenAI GPT-4 for text generation"
LLM: {"present": false}
```
**Fix**: Deterministic README pattern matching for AI providers

**Case 3: LLM Claims Backend Without Database**
```
LLM: "Has API endpoints suggesting backend"
AST: No database library found
```
**Fix**: AST validation requires actual database libraries

**Impact**: False negatives reduced 30-40% across all gates

---

# Workflow Diagrams

### Evaluation Pipeline Workflow

```
┌─────────────────────────────────────────────────────────────┐
│                    START: Canvas CSV Export                  │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│              Submission Ingestion Phase                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ Parse CSV    │→ │ Clone Repos  │→ │ Clean &      │      │
│  │ Extract URLs │  │ (shallow)    │  │ Validate     │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│              Source Code Processing                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ Extract      │→ │ Chunk Code   │→ │ Generate     │      │
│  │ Source Files │  │ (1500 chars) │  │ Embeddings    │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│                                          │                   │
│                              ┌───────────┴───────────┐       │
│                              ▼                       ▼       │
│                    ┌──────────────┐      ┌──────────────┐   │
│                    │ Check Cache  │      │ Cache New    │   │
│                    │ (hit/miss)   │      │ Embeddings   │   │
│                    └──────────────┘      └──────────────┘   │
└────────────────────────┬────────────────────────────────────┘
                         │
         ┌───────────────┴───────────────┐
         │                               │
         ▼                               ▼
┌──────────────────┐          ┌──────────────────┐
│  AST Analysis    │          │  LLM Evaluation  │
│  (Node.js)       │          │  (Python)        │
│  ┌────────────┐  │          │  ┌────────────┐  │
│  │ Parse JS/TS│  │          │  │ Retrieve   │  │
│  │ Detect     │  │          │  │ Top-k      │  │
│  │ Patterns   │  │          │  │ Chunks     │  │
│  └────────────┘  │          │  └────────────┘  │
│  Output: JSON    │          │  ┌────────────┐  │
│  Findings        │          │  │ Query LLM  │  │
└──────────────────┘          │  │ for Gates  │  │
                              │  └────────────┘  │
                              └──────────────────┘
         └───────────────┬───────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│              Deterministic Overrides                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ README Field │  │ URL Pattern  │  │ AI Evidence  │      │
│  │ Validation   │  │ Matching     │  │ Detection    │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│              Gate Decision Engine                            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ Check Must-  │→ │ AST Validate │→ │ Compute Pass │      │
│  │ Have Gates   │  │ Libraries    │  │ / Fail       │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│              Report Generation                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ JSON Export  │  │ CSV Export   │  │ Markdown     │      │
│  │ (Detailed)   │  │ (Canvas)     │  │ (Human)      │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                    END: Results Saved                        │
└─────────────────────────────────────────────────────────────┘
```

---

# State Diagrams

### Repository Evaluation State Machine

```
                    ┌─────────────┐
                    │   INITIAL   │
                    └──────┬──────┘
                           │
                           ▼
                    ┌─────────────┐
                    │  INGESTING  │
                    │ (Clone/Clean)│
                    └──────┬──────┘
                           │
                ┌──────────┴──────────┐
                │                     │
                ▼                     ▼
         ┌──────────┐          ┌──────────┐
         │  VALID   │          │ INVALID  │
         └─────┬────┘          └────┬─────┘
               │                   │
               ▼                   ▼
         ┌──────────┐          ┌──────────┐
         │AST_ANALYSIS│         │  SKIP    │
         └─────┬────┘          └──────────┘
               │
               ▼
         ┌──────────┐
         │ INDEXING │
         │(Embed)   │
         └─────┬────┘
               │
               ▼
         ┌──────────┐
         │ LLM_EVAL │
         └─────┬────┘
               │
               ▼
         ┌──────────┐
         │ OVERRIDE │
         └─────┬────┘
               │
               ▼
         ┌──────────┐
         │ DECISION │
         └─────┬────┘
               │
               ▼
         ┌──────────┐
         │ COMPLETE │
         └──────────┘
```

### LLM Provider State Machine

```
                    ┌─────────────┐
                    │   SELECT   │
                    │  PROVIDER  │
                    └──────┬──────┘
                           │
                ┌──────────┴──────────┐
                │                     │
                ▼                     ▼
         ┌──────────┐          ┌──────────┐
         │LMSTUDIO  │          │TRUSSEDAI │
         └────┬─────┘          └────┬─────┘
              │                    │
              ▼                    ▼
         ┌──────────┐          ┌──────────┐
         │ CONNECT  │          │ CONNECT  │
         └────┬─────┘          └────┬─────┘
              │                    │
      ┌───────┴───────┐    ┌─────┴──────┐
      │               │    │            │
      ▼               ▼    ▼            ▼
 ┌──────────┐  ┌──────────┐ ┌──────────┐ ┌──────────┐
 │ SUCCESS  │  │  ERROR   ││ SUCCESS  │ │  ERROR   │
 └────┬─────┘  └────┬─────┘└────┬─────┘ └────┬─────┘
      │             │         │            │
      ▼             ▼         ▼            ▼
 ┌──────────┐  ┌──────────┐ ┌──────────┐ ┌──────────┐
 │  QUERY   │  │ FALLBACK ││  QUERY   │ │ RETRY    │
 └────┬─────┘  └────┬─────┘└────┬─────┘ └────┬─────┘
      │             │         │            │
      ▼             ▼         ▼            │
 ┌──────────┐  ┌──────────┐ ┌──────────┐    │
 │ RESPONSE │  │ FALLBACK ││ RESPONSE │    │
 └────┬─────┘  └────┬─────┘└────┬─────┘    │
      │             │         │            │
      └─────────────┴─────────┴────────────┘
                          │
                          ▼
                   ┌──────────┐
                   │  RETURN  │
                   └──────────┘
```

---

# Data Flow Diagrams

### Data Flow Through System

```
┌──────────────┐
│ Canvas CSV   │
│ Export       │
└──────┬───────┘
       │ CSV Data
       ▼
┌──────────────┐
│ Submissions  │
│ Ingestion    │
└──────┬───────┘
       │ GitHub URLs
       ▼
┌──────────────┐
│ Git Clone    │
│ Service      │
└──────┬───────┘
       │ Repository Files
       ▼
┌──────────────┐
│ File Filter  │
│ & Cleaner    │
└──────┬───────┘
       │ Source Files
       ▼
    ┌──┴──┐
    │     │
    ▼     ▼
┌─────┐ ┌─────┐
│ AST │ │Code │
│Check│ │Chunk│
└──┬──┘ └──┬──┘
   │      │
   │      │ Chunks
   │      ▼
   │ ┌──────────┐
   │ │ Embedding│
   │ │ Generator│
   │ └────┬─────┘
   │      │ Embeddings
   │      ▼
   │ ┌──────────┐
   │ │  Cache   │
   │ └────┬─────┘
   │      │ Cached Embeddings
   │      ▼
   │ ┌──────────┐
   │ │Retrieval │
   │ │ System   │
   │ └────┬─────┘
   │      │ Relevant Chunks
   │      ▼
   │ ┌──────────┐
   │ │  LLM     │
   │ │ Adapter  │
   │ └────┬─────┘
   │      │ LLM Response
   │      ▼
   │ ┌──────────┐
   │ │ Gate     │
   │ │ Eval     │
   │ └────┬─────┘
   │      │ Gate Scores
   │      ▼
   └──────┴──────────┐
                    │
                    ▼
            ┌──────────────┐
            │ Deterministic│
            │ Overrides    │
            └──────┬───────┘
                   │
                   ▼
            ┌──────────────┐
            │ Gate Decision│
            └──────┬───────┘
                   │
                   ▼
            ┌──────────────┐
            │ Report       │
            │ Generator    │
            └──────┬───────┘
                   │
                   ▼
            ┌──────────────┐
            │ Results      │
            │ (JSON/CSV)   │
            └──────────────┘
```

### Cache Data Flow

```
┌──────────────┐
│ Chunk Content│
└──────┬───────┘
       │
       ▼
┌──────────────┐
│ Hash Function│
│ (SHA-256)    │
└──────┬───────┘
       │
       ▼
┌──────────────┐
│ Cache Key    │
│ repo+hash    │
└──────┬───────┘
       │
       ▼
    ┌──┴──┐
    │     │
    ▼     ▼
┌─────┐ ┌─────┐
│Cache│ │Embed│
│Lookup│ │Gen  │
└──┬──┘ └──┬──┘
   │      │
   │ Hit  │ Miss
   │      │
   ▼      ▼
┌─────┐ ┌─────┐
│Return│ │Cache│
│Embed│ │Store│
└─────┘ └─────┘
```

---

# Lessons Learned

### Technical Insights

1. **Hybrid Approach Works**: AST + LLM > either alone
2. **Overrides are Critical**: LLMs need objective corrections
3. **Caching is Essential**: 40-60% performance improvement
4. **Rate Limits Matter**: Exponential backoff is necessary
5. **Validation is Key**: Input validation prevents issues

### Process Insights

1. **Start Simple**: AST first, then add LLM
2. **Test Early**: Unit tests save time
3. **Monitor Everything**: Performance metrics guide optimization
4. **Document Well**: Architecture docs aid maintenance
5. **Iterate Quickly**: Small, frequent improvements

---

# Conclusion

### Summary

The HootCamp AI Grading system successfully automates student project evaluation by:

- **Combining** static analysis and LLM evaluation
- **Providing** accurate, consistent grading
- **Reducing** evaluation time by 70%
- **Delivering** detailed, actionable feedback
- **Scaling** to handle class-sized workloads

### Impact

- **Instructors**: Save time, ensure consistency
- **Students**: Receive faster, detailed feedback
- **Institution**: Scalable grading solution

---

# Q&A

### Questions?

**Thank You!**

Documentation: `docs/DESIGN.md`, `docs/ARCHITECTURE.md`
Repository: Available on GitHub
Contact: [Your contact information]

---

# Appendix: Code Examples

### AST Checker Output

```json
{
  "repo": "student_project",
  "findings": [
    {
      "code": "SUPABASE_CLIENT",
      "message": "Supabase client initialization",
      "file": "src/db/supabase.js",
      "line": 10
    },
    {
      "code": "AUTH_LIB",
      "message": "Authentication library usage",
      "file": "src/auth/login.js",
      "line": 5
    }
  ]
}
```

---

# Appendix: Code Examples

### Gate Evaluation Result

```json
{
  "ai_integration": {
    "present": true,
    "explanation": "Found OpenAI API usage in src/ai/chat.js for generating responses. Integration includes context management and error handling."
  },
  "backend_database": {
    "present": true,
    "explanation": "Supabase client configured with full CRUD operations. Tables: users, messages, settings."
  },
  "authentication": {
    "present": true,
    "explanation": "JWT-based authentication with protected routes using middleware."
  }
}
```

---

# Appendix: Configuration

### Example .env File

```bash
# LLM Provider
LLM_PROVIDER=lmstudio
LMSTUDIO_HOST=http://localhost:1234
LMSTUDIO_MODEL=qwen/qwen3.6-27b
LMSTUDIO_EMBED_MODEL=text-embedding-nomic-embed-text-v1.5
FALLBACK_EMBED_MODEL=sentence-transformers/all-mpnet-base-v2

# Or use TrussedAI
# LLM_PROVIDER=trussedai
# TRUSSEDAI_HOST=https://fauengtrussed.fau.edu/provider/generic
# TRUSSEDAI_MODEL=gpt-5.4
# TRUSSEDAI_OPENAI_API_KEY=your_key_here

# Testing
MOCK_MODE=false
```

---

# End of Presentation

## Thank You!

**HootCamp AI Grading System**

Automated Evaluation of Student Coding Projects
