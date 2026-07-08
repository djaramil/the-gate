# HootCamp AI Grading — Test Plan

## Overview
This test plan defines how we will validate each component of the HootCamp AI Grading system end-to-end, from submission ingestion through Gate Pass decision.

## Test Strategy
- **Incremental testing**: Test each phase independently before integration
- **Sample repo approach**: Use one real submission from `submissions/` as primary test case
- **Regression testing**: Ensure changes don't break previously working components
- **Edge case testing**: Test with invalid/incomplete submissions

## Test Setup

### Test Repository
- **Source**: Copy one repo from `submissions/submissions-1/` or `submissions/submissions-2/`
- **Location**: `test-repo/` (in HootCamp-AI-Grading root)
- **Selection criteria**: Choose a repo that appears complete (has README, multiple files, etc.)
- **Purpose**: Primary test case for all components

### Test Data
- **CSV files**: Use existing CSVs in `submissions/` for ingestion testing
- **Invalid samples**: Keep at least one incomplete/broken submission for edge case testing

## Phase 0: Submission Ingestion Tests

### Test 0.1: CSV Parsing
- **Input**: `submissions/week3_submissions_updated.csv`
- **Expected**: Successfully parse repo URLs/names
- **Validation**: Count matches expected number of submissions

### Test 0.2: Repo Extraction
- **Input**: One zip file from `submissions/` (e.g., `submissions-1.zip`)
- **Expected**: Extract to `repos/` folder with correct structure
- **Validation**: Check that repo folder exists and contains expected files

### Test 0.3: Directory Cleaning
- **Input**: Extracted repo with `node_modules/` present
- **Expected**: `node_modules/` removed, other ignored dirs removed
- **Validation**: `node_modules/` not present in cleaned repo
- **Test**: Also test `.venv/`, `__pycache__/`, `dist/`, `build/`, `.next/` removal

### Test 0.4: Repo Validation
- **Input**: Various repo states (complete, incomplete, empty)
- **Expected**: Valid repos pass, invalid repos are flagged/skipped
- **Validation**: Check for README.md, package.json, or minimum file count

### Test 0.5: Full Ingestion Workflow
- **Input**: Run `submissions_ingestion.py` on latest CSV
- **Expected**: All valid repos extracted to `repos/`, cleaned, and validated
- **Validation**: Count repos in `repos/` matches valid entries in CSV

## Phase 1: Core Integration Tests

### Test 1.1: LLM Adapter - Chat
- **Input**: Simple test prompt to `llm_adapter.chat()`
- **Expected**: Valid response from LMStudio (qwen-3.6)
- **Validation**: Response contains expected content, no errors

### Test 1.2: LLM Adapter - Embed (LMStudio)
- **Input**: List of test strings to `llm_adapter.embed()`
- **Expected**: Return embedding vectors
- **Validation**: Vector dimensions match expected (e.g., 768 or 1536)

### Test 1.3: LLM Adapter - Embed (Fallback)
- **Input**: Set `LMSTUDIO_EMBED_MODEL=""`, test with sentence-transformers
- **Expected**: Fallback to sentence-transformers/all-mpnet-base-v2
- **Validation**: Vectors generated successfully

### Test 1.4: Embedding Cache
- **Input**: Embed same text twice
- **Expected**: Second call uses cache (faster, no API call)
- **Validation**: Cache file created, subsequent hits use cached value

### Test 1.5: Retrieval with Adapter
- **Input**: Test repo from `test-repo/`
- **Expected**: `CodeRetriever` chunks files and generates embeddings via adapter
- **Validation**: Chunks created, embeddings generated, search works

### Test 1.6: Ingestion Adaptation
- **Input**: Test repo from `test-repo/`
- **Expected**: `extract_source_code()` works with local repo
- **Validation**: Returns dict of relevant files, ignores node_modules

## Phase 2: Gate-Specific Checks Tests

### Test 2.1: AST Checker - Supabase Detection
- **Input**: Test repo with Supabase imports
- **Expected**: Detects `createClient`, `supabase.auth`, `supabase.from`
- **Validation**: JSON output includes Supabase findings

### Test 2.2: AST Checker - CRUD Detection
- **Input**: Test repo with CRUD operations
- **Expected**: Detects insert, select, update, delete patterns
- **Validation**: JSON output includes CRUD findings

### Test 2.3: AST Checker - Auth Detection
- **Input**: Test repo with auth code
- **Expected**: Detects `signInWithPassword`, `signUp`, `signOut`
- **Validation**: JSON output includes auth findings

### Test 2.4: AST Checker - Security Flags
- **Input**: Test repo with eval/child_process
- **Expected**: Flags dangerous patterns
- **Validation**: JSON output includes security warnings

### Test 2.5: README Analysis - Required Fields
- **Input**: README with name, Z-number, email, deployment link, demo link
- **Expected**: Extracts all required fields
- **Validation**: Parsed values match expected

### Test 2.6: README Analysis - Missing Fields
- **Input**: README missing some required fields
- **Expected**: Flags missing fields
- **Validation**: Output indicates which fields are missing

### Test 2.7: Deployment Link Validation
- **Input**: Valid deployment URL
- **Expected**: URL is accessible (HTTP 200)
- **Validation**: HEAD request succeeds

### Test 2.8: Deployment Link Validation - Invalid
- **Input**: Invalid or dead URL
- **Expected**: Flagged as invalid
- **Validation**: Error handling works

## Phase 3: Orchestrator & Reporting Tests

### Test 3.1: Single Repo Evaluation
- **Input**: `hc_evaluate.py evaluate-single --path test-repo/`
- **Expected**: Full evaluation runs end-to-end
- **Validation**: Report generated, all phases executed

### Test 3.2: Dry Run Mode
- **Input**: `hc_evaluate.py evaluate-single --path test-repo/ --no-llm`
- **Expected**: Static analysis only (AST + README), no LLM calls
- **Validation**: Faster execution, no LLM errors

### Test 3.3: Batch Evaluation
- **Input**: `hc_evaluate.py evaluate-latest`
- **Expected**: Evaluates all repos in `repos/`
- **Validation**: All repos processed, reports generated

### Test 3.4: Gate Pass Logic
- **Input**: Test repo with all gate requirements met
- **Expected**: Gate Pass = True
- **Validation**: Boolean decision correct

### Test 3.5: Gate Pass Logic - Fail
- **Input**: Test repo missing one or more requirements
- **Expected**: Gate Pass = False
- **Validation**: Boolean decision correct, reason provided

### Test 3.6: Report Generation
- **Input**: Completed evaluation results
- **Expected**: Markdown report with all sections
- **Validation**: Report includes: static analysis, LLM scores, gate decision

## Phase 4: Documentation Tests

### Test 4.1: README Instructions
- **Input**: Follow README setup instructions from scratch
- **Expected**: New user can set up environment successfully
- **Validation**: All steps work, no missing dependencies

### Test 4.2: Example Commands
- **Input**: Run example commands from README
- **Expected**: All commands execute successfully
- **Validation**: No errors, expected output

## Integration Tests

### Test I.1: Full Workflow End-to-End
- **Input**: Fresh start, run ingestion → evaluation → reporting
- **Expected**: Complete pipeline works
- **Validation**: From CSV to final Gate Pass decision

### Test I.2: Error Recovery
- **Input**: Simulate failures (LMStudio down, bad repo, etc.)
- **Expected**: Graceful error handling, clear error messages
- **Validation**: No crashes, informative errors

### Test I.3: Performance
- **Input**: Batch evaluation of 10+ repos
- **Expected**: Completes in reasonable time
- **Validation**: Time per repo acceptable, caching works

## Regression Tests

### Test R.1: AST Checker Regression
- **Input**: Re-run AST checker on previously analyzed repos
- **Expected**: Same results as before
- **Validation**: No changes in findings

### Test R.2: LLM Evaluation Regression
- **Input**: Re-run LLM eval with same prompts
- **Expected**: Consistent scoring (within tolerance)
- **Validation**: Scores don't vary wildly

## Test Execution Order

1. **Setup**: Copy test repo, install dependencies
2. **Phase 0**: Ingestion tests (0.1 → 0.5)
3. **Phase 1**: Core integration tests (1.1 → 1.6)
4. **Phase 2**: Gate-specific tests (2.1 → 2.8)
5. **Phase 3**: Orchestrator tests (3.1 → 3.6)
6. **Integration**: Full workflow tests (I.1 → I.3)
7. **Phase 4**: Documentation tests (4.1 → 4.2)
8. **Regression**: Periodic regression checks

## Success Criteria

- All unit tests pass for each component
- Integration test completes end-to-end without errors
- Gate Pass decisions match manual evaluation on test cases
- Documentation is accurate and complete
- Performance is acceptable for batch processing

## Test Automation

Eventually, we should automate these tests:
- Unit tests for Python modules (pytest)
- Integration test script that runs full workflow
- Regression test suite for periodic validation
