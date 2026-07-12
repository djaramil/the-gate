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

MUST_HAVE_GATES = [
    'ai_integration',
    'backend_database',
    'authentication',
    'readme_completeness',
    'deployment_live',
    'demo_video_present',
]


def analyze_readme_completeness(repo_path: str) -> Dict:
    """Deterministic README field check based on gate submission requirements.

    Required in README:
    - name, Z-number, FAU email
    - live/deployed app link
    - demo video link
    - project description / features
    - setup instructions
    - tech stack (or AI explanation)
    """
    import re

    readme = extract_readme(repo_path)
    if not readme or not readme.strip():
        return {
            'present': False,
            'fields': {},
            'missing': ['README.md'],
            'explanation': 'No README.md found in repository root',
        }

    text = readme
    lower = text.lower()
    urls = re.findall(r'https?://[^\s\)\]\}"\'<>`]+', text)

    def has_live_url():
        live_hosts = (
            'vercel.app', 'netlify.app', 'onrender.com', 'railway.app',
            'fly.dev', 'pages.dev', 'web.app', 'firebaseapp.com', 'hosted.app',
            'herokuapp.com', 'github.io',
        )
        skip = (
            'github.com/', 'youtu', 'loom.com', 'drive.google', 'localhost',
            'app.netlify.com', 'vercel.com/', 'netlify.com/', 'supabase.co',
            'fauengtrussed', 'openai.com', 'anthropic.com', 'back4app.com',
            'parseapi.', 'platform.openai', 'apod.nasa.gov', '127.0.0.1',
            'mongodb.com', 'console.anthropic', 'portal.azure',
        )
        vendor_hosts = (
            'mongodb.com', 'anthropic.com', 'openai.com', 'google.com',
            'azure.com', 'github.com', 'npmjs.com', 'supabase.com',
        )
        for url in urls:
            u = url.lower().rstrip('/')
            if any(s in u for s in skip):
                continue
            if any(h in u for h in live_hosts):
                return True
            host = u.split('//', 1)[-1].split('/', 1)[0]
            if host.startswith('www.'):
                host = host[4:]
            path = u.split('//', 1)[-1][len(u.split('//', 1)[-1].split('/', 1)[0]):]
            if host.startswith(('docs.', 'console.', 'api.', 'portal.', 'platform.')):
                continue
            if any(host == v or host.endswith('.' + v) for v in vendor_hosts):
                continue
            # subdomain app hosts
            if host.count('.') >= 2:
                return True
            # apex domain with app path, e.g. mycomicgenius.com/comicbookapp
            if host.count('.') == 1 and path and path not in ('', '/') and host.endswith(
                ('.com', '.app', '.io', '.dev', '.ai', '.net', '.org')
            ):
                return True
        return False

    def has_demo_video():
        video_hosts = ('youtu', 'vimeo', 'loom', 'drive.google', 'dropbox')
        for url in urls:
            if any(h in url.lower() for h in video_hosts):
                return True
        # Local/repo-hosted demo video file referenced in README
        if re.search(r'(?i)(?:demo|walkthrough|screencast).{0,40}\.(mp4|mov|webm|m4v)\b', text):
            return True
        if re.search(r'(?i)\[[^\]]*(?:demo|walkthrough|video)[^\]]*\]\([^)]+\.(mp4|mov|webm|m4v)\)', text):
            return True
        return False

    fields = {
        'name': bool(re.search(r'(?i)(?:\*\*)?name(?:\*\*)?\s*[:\-]', text)) or bool(re.search(r'(?i)student\s+information', text)),
        'z_number': bool(re.search(r'(?i)\bz[-\s]?number\b|\bZ\d{5,}\b', text)),
        'email': bool(re.search(r'(?i)[a-z0-9._%+\-]+@fau\.edu', text)),
        'live_link': has_live_url(),
        'demo_video': has_demo_video(),
        'description': len(text.strip()) >= 400 or any(k in lower for k in ('feature', 'overview', 'description', 'about')),
        'setup': any(k in lower for k in ('setup', 'install', 'getting started', 'npm install', 'yarn', 'pnpm', 'env')),
        'tech_or_ai': any(k in lower for k in (
            'tech stack', 'stack:', 'built with', 'ai integration', 'openai', 'gemini',
            'anthropic', 'supabase', 'mongodb', 'next.js', 'react', 'express'
        )),
    }

    # Core identity + links are hard requirements; description/setup/tech are soft but expected
    hard = ['name', 'z_number', 'email', 'live_link', 'demo_video']
    soft = ['description', 'setup', 'tech_or_ai']
    missing_hard = [f for f in hard if not fields[f]]
    missing_soft = [f for f in soft if not fields[f]]

    # Pass if all hard fields present and at least 2/3 soft fields present
    present = len(missing_hard) == 0 and len(missing_soft) <= 1
    missing = missing_hard + missing_soft

    if present:
        explanation = (
            f"README field check passed. Found: "
            + ', '.join(k for k, v in fields.items() if v)
        )
    else:
        explanation = f"README missing required fields: {', '.join(missing)}"

    return {
        'present': present,
        'fields': fields,
        'missing': missing,
        'explanation': explanation,
    }


def apply_readme_override(gate_evaluations: Dict, repo_path: str) -> Dict:
    """Override false-negative LLM readme_completeness using deterministic checks."""
    analysis = analyze_readme_completeness(repo_path)
    current = gate_evaluations.get('readme_completeness', {})

    # Only upgrade false -> true (don't downgrade a true LLM pass unless README is missing)
    if analysis['present']:
        if not current.get('present', False):
            gate_evaluations['readme_completeness'] = {
                'present': True,
                'explanation': analysis['explanation'],
                'fields': analysis['fields'],
                'override': 'deterministic_readme_check',
            }
    elif not current.get('present', False):
        # Keep false, but attach structured missing fields for reporting
        gate_evaluations['readme_completeness'] = {
            'present': False,
            'explanation': analysis['explanation'],
            'fields': analysis['fields'],
            'missing': analysis['missing'],
            'override': 'deterministic_readme_check',
        }

    return gate_evaluations


def apply_link_overrides(gate_evaluations: Dict, repo_path: str) -> Dict:
    """Sync deployment_live / demo_video_present with real README URLs.

    - Upgrade false negatives when a real URL exists
    - Downgrade deployment_live when LLM said PASS but no live URL can be found
    """
    analysis = analyze_readme_completeness(repo_path)
    fields = analysis.get('fields', {})

    if fields.get('live_link') and not gate_evaluations.get('deployment_live', {}).get('present', False):
        gate_evaluations['deployment_live'] = {
            'present': True,
            'explanation': 'Live/deployed app URL found in README (deterministic override)',
            'override': 'deterministic_readme_link_check',
        }
    elif gate_evaluations.get('deployment_live', {}).get('present', False) and not fields.get('live_link'):
        # LLM claimed deployment without an actual URL — treat as fail
        gate_evaluations['deployment_live'] = {
            'present': False,
            'explanation': 'Deployment marked present by LLM but no live URL found in README',
            'override': 'deterministic_missing_live_url',
        }

    if fields.get('demo_video') and not gate_evaluations.get('demo_video_present', {}).get('present', False):
        gate_evaluations['demo_video_present'] = {
            'present': True,
            'explanation': 'Demo video URL found in README (deterministic override)',
            'override': 'deterministic_readme_link_check',
        }

    return gate_evaluations


def analyze_ai_integration(repo_path: str, ast_findings: List = None) -> Dict:
    """Deterministic AI integration check from README + AST evidence."""
    import re

    ast_findings = ast_findings or []
    has_ast_ai = any(
        f.get('code') in ('AI_OR_BACKEND_LIB', 'AI_HINT', 'AI_ENDPOINT')
        for f in ast_findings
    )

    readme = extract_readme(repo_path).lower()
    evidence = []

    patterns = [
        ('openai', r'openai|gpt-|chatgpt'),
        ('anthropic', r'anthropic|claude'),
        ('gemini', r'gemini|@google/generative|generativelanguage'),
        ('azure_vision', r'azure computer vision|cognitiveservices\.azure|vision/v3|visualfeatures'),
        ('ai_sdk', r'@ai-sdk|vercel ai sdk|streamtext|generateobject'),
        ('ollama', r'\bollama\b'),
        ('groq', r'\bgroq\b'),
        ('yolo_ml', r'yolov\d|ultralytics'),
    ]
    for label, pattern in patterns:
        if re.search(pattern, readme, re.I):
            evidence.append(label)

    # README "AI Features" section is strong signal when paired with a provider
    has_ai_section = bool(re.search(r'(?i)##\s*ai features|ai class suggestions|ai auto-annotate|ai integration', readme))

    present = has_ast_ai or (has_ai_section and len(evidence) > 0) or len(evidence) >= 2
    return {
        'present': present,
        'has_ast_ai': has_ast_ai,
        'has_ai_section': has_ai_section,
        'evidence': evidence,
        'explanation': (
            f"AI integration found via deterministic check "
            f"(ast={has_ast_ai}, section={has_ai_section}, evidence={evidence})"
            if present else
            f"No deterministic AI evidence (ast={has_ast_ai}, section={has_ai_section}, evidence={evidence})"
        ),
    }


def apply_ai_override(gate_evaluations: Dict, repo_path: str, ast_findings: List = None) -> Dict:
    """Upgrade false-negative LLM ai_integration when README/AST show real AI."""
    analysis = analyze_ai_integration(repo_path, ast_findings)
    current = gate_evaluations.get('ai_integration', {})

    # Also catch LLM saying Azure/OpenAI exists but present=false
    explanation = str(current.get('explanation', '')).lower()
    llm_mentions_ai = any(token in explanation for token in (
        'azure computer vision', 'openai', 'anthropic', 'gemini', 'ollama',
        'ai-sdk', 'llm', 'yolo', 'computer vision'
    ))

    if not current.get('present', False) and (analysis['present'] or llm_mentions_ai):
        gate_evaluations['ai_integration'] = {
            'present': True,
            'explanation': analysis['explanation'] if analysis['present'] else (
                f"LLM described AI features but marked absent; overridden. Raw: {current.get('explanation')}"
            ),
            'override': 'deterministic_ai_check',
            'evidence': analysis.get('evidence', []),
        }
    return gate_evaluations


def apply_deterministic_overrides(gate_evaluations: Dict, repo_path: str, ast_findings: List = None) -> Dict:
    """Apply all deterministic README/AST-based overrides after LLM evaluation."""
    gate_evaluations = apply_readme_override(gate_evaluations, repo_path)
    gate_evaluations = apply_link_overrides(gate_evaluations, repo_path)
    gate_evaluations = apply_ai_override(gate_evaluations, repo_path, ast_findings)
    return gate_evaluations


def is_evaluation_complete(result: Dict) -> bool:
    """True when a checkpoint entry has full gate evaluation data."""
    if result.get('error'):
        return False

    gate_evaluations = result.get('gate_evaluations')
    if not gate_evaluations:
        return False

    for gate in MUST_HAVE_GATES:
        if gate not in gate_evaluations:
            return False
        explanation = gate_evaluations[gate].get('explanation', '')
        if 'error' in str(explanation).lower():
            return False

    return True


def compute_gate_pass(gate_evaluations: Dict, ast_findings: List) -> Dict:
    """Compute Gate Pass decision based on gate requirements."""
    must_have = MUST_HAVE_GATES
    
    # Check if all must-have items are present
    missing_requirements = []
    for requirement in must_have:
        if requirement not in gate_evaluations:
            missing_requirements.append(f"{requirement} (not evaluated)")
        elif not gate_evaluations[requirement].get('present', False):
            missing_requirements.append(requirement)
    
    # Additional checks from AST findings
    has_supabase = any(f['code'] in ['SUPABASE_CLIENT', 'SUPABASE_AUTH', 'SUPABASE_CRUD', 'SUPABASE_HINT'] for f in ast_findings)
    has_back4app = any(f['code'] in ['BACK4APP_PARSE', 'BACK4APP_HINT'] for f in ast_findings)
    has_mongodb = any(f['code'] in ['MONGODB_LIB', 'MONGODB_HINT'] for f in ast_findings)
    has_sql_db = any(f['code'] in ['SQL_DB_LIB', 'SQL_DB_HINT'] for f in ast_findings)
    has_auth_lib = any(f['code'] in ['AUTH_LIB', 'AUTH_HINT'] for f in ast_findings)
    has_ai_lib = any(f['code'] in ['AI_OR_BACKEND_LIB', 'AI_HINT', 'AI_ENDPOINT'] for f in ast_findings)
    
    # AST-based validation (only if AST found any findings - indicates JS/TS repo)
    ast_issues = []
    has_js_ts_files = len(ast_findings) > 0 or any(f.get('code') != 'PARSE_ERROR' for f in ast_findings)
    
    if has_js_ts_files:
        # Accept Supabase, Back4App, MongoDB, or SQL/ORM (Neon/Drizzle/Prisma/pg)
        if (
            not has_supabase
            and not has_back4app
            and not has_mongodb
            and not has_sql_db
            and gate_evaluations.get('backend_database', {}).get('present', False)
        ):
            ast_issues.append("No database library (Supabase, Back4App, MongoDB, or SQL/ORM) detected in AST")
        if not has_auth_lib and gate_evaluations.get('authentication', {}).get('present', False):
            ast_issues.append("No auth library detected in AST")
        # Only flag missing AI lib when LLM also didn't find AI integration
        if (
            not has_ai_lib
            and gate_evaluations.get('ai_integration', {}).get('present', False)
            and not _has_ai_evidence_in_repo(gate_evaluations)
        ):
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
        'has_back4app': has_back4app,
        'has_mongodb': has_mongodb,
        'has_sql_db': has_sql_db,
        'has_auth_lib': has_auth_lib,
        'has_ai_lib': has_ai_lib,
        'has_js_ts_files': has_js_ts_files
    }


def _has_ai_evidence_in_repo(gate_evaluations: Dict) -> bool:
    """True when LLM AI gate already found concrete provider evidence."""
    ai = gate_evaluations.get('ai_integration', {})
    if not ai.get('present', False):
        return False
    explanation = str(ai.get('explanation', '')).lower()
    return any(token in explanation for token in (
        'openai', 'anthropic', 'gemini', 'claude', 'llm', 'gpt',
        'generative', 'ai-sdk', 'trussed', 'groq', 'nvidia', 'ollama'
    ))

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
            gate_results = apply_deterministic_overrides(gate_results, repo_path, results['ast_findings'])
            eval_time = time.time() - phase_start
            results['timing']['llm_evaluations'] = f"{eval_time:.2f}s"
            results['gate_evaluations'] = gate_results
            results['readme_analysis'] = analyze_readme_completeness(repo_path)
            
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
                    if is_evaluation_complete(r):
                        existing_results[repo_name] = r
                    else:
                        failed_repos.add(repo_name)
                        if verbose:
                            print(f"Marking {repo_name} for re-evaluation (incomplete or errored)")
                            sys.stdout.flush()
                
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
