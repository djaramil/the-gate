import argparse, json
import subprocess
import time
import sys
from pathlib import Path
from typing import Dict, List
from ingestion import extract_source_code, extract_readme
from retrieval import CodeRetriever
from llm_eval import perform_gate_evaluations

def run_ast_checker(repo_path: str) -> Dict:
    """Run JS/TS AST checker on repo."""
    try:
        result = subprocess.run(
            ['node', 'js_ts_ast_checker.js', repo_path],
            capture_output=True,
            text=True,
            timeout=30
        )
        if result.returncode == 0:
            return json.loads(result.stdout)
        else:
            return {'repo': Path(repo_path).name, 'findings': [], 'error': result.stderr}
    except Exception as e:
        return {'repo': Path(repo_path).name, 'findings': [], 'error': str(e)}

def compute_gate_pass(gate_evaluations: Dict, ast_findings: List) -> Dict:
    """Compute Gate Pass decision based on gate requirements."""
    # Must-have gate requirements
    must_have = [
        'ai_integration',
        'backend_database', 
        'authentication',
        'readme_completeness',
        'deployment_live',
        'demo_video_present'
    ]
    
    # Check if all must-have items are present
    missing_requirements = []
    for requirement in must_have:
        if requirement not in gate_evaluations:
            missing_requirements.append(f"{requirement} (not evaluated)")
        elif not gate_evaluations[requirement].get('present', False):
            missing_requirements.append(requirement)
    
    # Additional checks from AST findings
    has_supabase = any(f['code'] in ['SUPABASE_CLIENT', 'SUPABASE_AUTH', 'SUPABASE_CRUD'] for f in ast_findings)
    has_auth_lib = any(f['code'] in ['AUTH_LIB', 'AUTH_HINT'] for f in ast_findings)
    has_ai_lib = any(f['code'] == 'AI_OR_BACKEND_LIB' for f in ast_findings)
    
    # AST-based validation (only if AST found any findings - indicates JS/TS repo)
    ast_issues = []
    has_js_ts_files = len(ast_findings) > 0 or any(f.get('code') != 'PARSE_ERROR' for f in ast_findings)
    
    if has_js_ts_files:
        # Only apply AST validation if repo has JS/TS files
        if not has_supabase and gate_evaluations.get('backend_database', {}).get('present', False):
            ast_issues.append("No Supabase usage detected in AST")
        if not has_auth_lib and gate_evaluations.get('authentication', {}).get('present', False):
            ast_issues.append("No auth library detected in AST")
        if not has_ai_lib and gate_evaluations.get('ai_integration', {}).get('present', False):
            ast_issues.append("No AI library detected in AST")
    else:
        # No JS/TS files found - skip AST validation, rely on LLM only
        pass
    
    # Final decision
    gate_pass = len(missing_requirements) == 0 and len(ast_issues) == 0
    
    return {
        'gate_pass': gate_pass,
        'missing_requirements': missing_requirements,
        'ast_issues': ast_issues,
        'has_supabase': has_supabase,
        'has_auth_lib': has_auth_lib,
        'has_ai_lib': has_ai_lib,
        'has_js_ts_files': has_js_ts_files
    }

def evaluate_single_repo(repo_path: str, no_llm: bool = False, verbose: bool = True) -> Dict:
    """Evaluate a single repository."""
    repo_name = Path(repo_path).name
    start_time = time.time()
    
    results = {
        'repo_name': repo_name,
        'repo_path': repo_path,
        'ast_findings': [],
        'gate_evaluations': {},
        'gate_pass': False,
        'gate_decision': {},
        'timing': {}
    }
    
    # Phase 1: AST Analysis
    phase_start = time.time()
    if verbose: 
        print(f"\n🔍 [1/3] AST Analysis...")
        sys.stdout.flush()
    ast_results = run_ast_checker(repo_path)
    results['ast_findings'] = ast_results.get('findings', [])
    phase_time = time.time() - phase_start
    results['timing']['ast_analysis'] = f"{phase_time:.2f}s"
    if verbose: 
        print(f"   ✓ Found {len(results['ast_findings'])} AST findings ({phase_time:.2f}s)")
        sys.stdout.flush()
    
    # Phase 2: LLM Evaluation (skip if --no-llm)
    if not no_llm:
        phase_start = time.time()
        if verbose: 
            print(f"\n📄 [2/3] Source Code Extraction...")
            sys.stdout.flush()
        source_files = extract_source_code(repo_path)
        
        if source_files:
            extract_time = time.time() - phase_start
            if verbose: 
                print(f"   ✓ Found {len(source_files)} source files ({extract_time:.2f}s)")
                sys.stdout.flush()
            if verbose:
                for filepath in sorted(source_files.keys()):
                    print(f"      - {filepath}")
                sys.stdout.flush()
            
            phase_start = time.time()
            if verbose: 
                print(f"\n🔎 [2/3] Building retrieval index...")
                sys.stdout.flush()
            retriever = CodeRetriever(source_files, repo_tag=repo_name, verbose=False)
            index_time = time.time() - phase_start
            results['timing']['index_build'] = f"{index_time:.2f}s"
            if verbose: 
                print(f"   ✓ Index built with {len(retriever.chunks)} chunks ({index_time:.2f}s)")
                sys.stdout.flush()
            
            phase_start = time.time()
            if verbose: 
                print(f"\n🤖 [2/3] Running LLM gate evaluations...")
                sys.stdout.flush()
            gate_results = perform_gate_evaluations(retriever, verbose=verbose, top_k=5)
            eval_time = time.time() - phase_start
            results['timing']['llm_evaluations'] = f"{eval_time:.2f}s"
            results['gate_evaluations'] = gate_results
            
            # Compute Gate Pass decision
            phase_start = time.time()
            if verbose: 
                print(f"\n✅ [3/3] Computing Gate Pass decision...")
                sys.stdout.flush()
            gate_decision = compute_gate_pass(gate_results, results['ast_findings'])
            decision_time = time.time() - phase_start
            results['timing']['gate_decision'] = f"{decision_time:.2f}s"
            results['gate_pass'] = gate_decision['gate_pass']
            results['gate_decision'] = gate_decision
            
            total_time = time.time() - start_time
            results['timing']['total'] = f"{total_time:.2f}s"
            
            if verbose:
                print(f"\n{'='*60}")
                print(f"Gate Pass: {'✓ PASS' if gate_decision['gate_pass'] else '✗ FAIL'}")
                if gate_decision['missing_requirements']:
                    print(f"Missing: {', '.join(gate_decision['missing_requirements'])}")
                if gate_decision['ast_issues']:
                    print(f"AST Issues: {', '.join(gate_decision['ast_issues'])}")
                print(f"Total time: {total_time:.2f}s")
                print(f"{'='*60}")
                sys.stdout.flush()
        else:
            if verbose: 
                print("      No source files found for LLM evaluation")
                sys.stdout.flush()
            total_time = time.time() - start_time
            results['timing']['total'] = f"{total_time:.2f}s"
    else:
        if verbose: 
            print(f"\n[2/3] Skipping LLM evaluation (--no-llm mode)")
            print(f"\n[3/3] Skipping Gate Pass decision (--no-llm mode)")
            sys.stdout.flush()
        total_time = time.time() - start_time
        results['timing']['total'] = f"{total_time:.2f}s"
    
    return results

def evaluate_all_repos(repos_dir: str, no_llm: bool = False, verbose: bool = True, resume: bool = False) -> List[Dict]:
    """Evaluate all repos in the repos directory with checkpoint support."""
    repos_path = Path(repos_dir)
    if not repos_path.exists():
        print(f"Error: Repos directory {repos_dir} does not exist")
        return []
    
    repo_dirs = [d for d in repos_path.iterdir() if d.is_dir() and not d.name.startswith('.')]
    if verbose: 
        print(f"\nFound {len(repo_dirs)} repos to evaluate")
        sys.stdout.flush()
    
    # Load existing results if resuming
    checkpoint_file = Path('results/evaluation_results.json')
    existing_results = {}
    failed_repos = set()
    if resume and checkpoint_file.exists():
        try:
            with open(checkpoint_file, 'r') as f:
                existing_data = json.load(f)
                for r in existing_data:
                    repo_name = r['repo_name']
                    # Check if repo had errors (missing gate evaluations or error in findings)
                    has_errors = False
                    if 'error' in r:
                        has_errors = True
                    elif 'gate_evaluations' in r:
                        # Check if any gate evaluations failed
                        for gate_name, gate_result in r['gate_evaluations'].items():
                            if 'error' in str(gate_result.get('explanation', '')).lower():
                                has_errors = True
                                break
                    
                    if has_errors:
                        failed_repos.add(repo_name)
                        if verbose:
                            print(f"Marking {repo_name} for re-evaluation (had errors)")
                            sys.stdout.flush()
                    else:
                        existing_results[repo_name] = r
                
                if verbose:
                    print(f"Resuming from checkpoint: {len(existing_results)} repos OK, {len(failed_repos)} repos need re-evaluation")
                    sys.stdout.flush()
        except Exception as e:
            if verbose:
                print(f"Warning: Could not load checkpoint file: {e}")
                sys.stdout.flush()
    
    all_results = []
    start_time = time.time()
    
    for i, repo_dir in enumerate(repo_dirs, 1):
        repo_name = repo_dir.name
        
        # Skip if already evaluated and resuming (but re-evaluate failed repos)
        if resume and repo_name in existing_results and repo_name not in failed_repos:
            if verbose:
                print(f"\nSkipping {repo_name} (already evaluated)")
                sys.stdout.flush()
            all_results.append(existing_results[repo_name])
            continue
        
        progress_pct = (i / len(repo_dirs)) * 100
        elapsed = time.time() - start_time
        if i > 1:
            avg_time = elapsed / (i - 1)
            remaining = avg_time * (len(repo_dirs) - i)
            if verbose: 
                print(f"\n{'='*70}")
                print(f"📦 [{i}/{len(repo_dirs)}] {repo_name} ({progress_pct:.1f}%) | ETA: {remaining:.0f}s")
                print(f"{'='*70}")
                sys.stdout.flush()
        else:
            if verbose: 
                print(f"\n{'='*70}")
                print(f"📦 [{i}/{len(repo_dirs)}] {repo_name} ({progress_pct:.1f}%)")
                print(f"{'='*70}")
                sys.stdout.flush()
        
        # Write current status to file for monitoring
        try:
            with open('results/.evaluation_status', 'w') as f:
                f.write(f"{i}/{len(repo_dirs)}|{repo_name}|{progress_pct:.1f}%")
        except:
            pass
        
        result = evaluate_single_repo(str(repo_dir), no_llm=no_llm, verbose=verbose)
        all_results.append(result)
        
        # Save checkpoint after each repo
        if verbose:
            print(f"Saving checkpoint...")
            sys.stdout.flush()
        try:
            with open(checkpoint_file, 'w') as f:
                json.dump(all_results, f, indent=2)
            if verbose:
                print(f"Checkpoint saved ({len(all_results)}/{len(repo_dirs)} repos)")
                sys.stdout.flush()
        except Exception as e:
            if verbose:
                print(f"Warning: Could not save checkpoint: {e}")
                sys.stdout.flush()
    
    total_time = time.time() - start_time
    if verbose: 
        print(f"\n{'='*60}")
        print(f"Completed {len(repo_dirs)} repos in {total_time:.2f}s ({total_time/len(repo_dirs):.2f}s avg)")
        print(f"{'='*60}")
        sys.stdout.flush()
    
    return all_results

def main():
    p = argparse.ArgumentParser(description="HootCamp AI Grading Orchestrator")
    subparsers = p.add_subparsers(dest='cmd', required=True)
    
    # evaluate-single command
    single_parser = subparsers.add_parser('evaluate-single', help='Evaluate a single repository')
    single_parser.add_argument('--path', required=True, help='Path to repository')
    single_parser.add_argument('--no-llm', action='store_true', help='Skip LLM evaluation (AST only)')
    
    # evaluate-latest command
    latest_parser = subparsers.add_parser('evaluate-latest', help='Evaluate all repos in repos/ directory')
    latest_parser.add_argument('--repos-dir', default='repos', help='Path to repos directory')
    latest_parser.add_argument('--no-llm', action='store_true', help='Skip LLM evaluation (AST only)')
    latest_parser.add_argument('--resume', action='store_true', help='Resume from existing checkpoint file')
    
    args = p.parse_args()
    
    if args.cmd == 'evaluate-single':
        result = evaluate_single_repo(args.path, no_llm=args.no_llm)
        print(json.dumps(result, indent=2))
    
    elif args.cmd == 'evaluate-latest':
        results = evaluate_all_repos(args.repos_dir, no_llm=args.no_llm, resume=args.resume)
        print(f"\n=== Evaluated {len(results)} repos ===")
        for result in results:
            print(f"\n{result['repo_name']}:")
            print(f"  AST findings: {len(result['ast_findings'])}")
            if result['gate_evaluations']:
                print(f"  Gate evaluations: {len(result['gate_evaluations'])}")
            else:
                print(f"  Gate evaluations: skipped (--no-llm)")
        
        # Save full results
        output_file = Path('results/evaluation_results.json')
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"\nFull results saved to {output_file}")

if __name__=="__main__":
    main()
