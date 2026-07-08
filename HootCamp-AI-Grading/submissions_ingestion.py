#!/usr/bin/env python3
"""
Submission Ingestion Workflow for HootCamp AI Grading

This script:
1. Parses the latest CSV from submissions/ folder to get repo URLs
2. Clones GitHub repos to repos/ folder
3. Cleans extracted repos (removes node_modules, .venv, etc.)
4. Validates repo structure and skips invalid submissions
"""

import csv
import os
import subprocess
import shutil
from pathlib import Path
from typing import List, Dict, Optional
import re

# Configuration
SUBMISSIONS_DIR = Path("submissions")
REPOS_DIR = Path("repos")
IGNORE_DIRS = {'node_modules', 'venv', '.venv', '__pycache__', '.git', 'dist', 'build', '.next', '.vscode', 'idea'}
MIN_FILE_COUNT = 3  # Minimum files to consider a repo valid


def find_latest_csv() -> Optional[Path]:
    """Find the most recent CSV file in submissions/ directory."""
    csv_files = list(SUBMISSIONS_DIR.glob("*.csv"))
    if not csv_files:
        print(f"No CSV files found in {SUBMISSIONS_DIR}")
        return None
    
    # Sort by modification time, most recent first
    csv_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
    latest = csv_files[0]
    print(f"Using latest CSV: {latest}")
    return latest


def parse_submission_csv(csv_path: Path) -> List[Dict[str, str]]:
    """Parse submission CSV and extract GitHub URLs."""
    submissions = []
    
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            url = row.get('submission_url', '').strip()
            # Filter for GitHub URLs only
            if url and 'github.com' in url:
                submissions.append({
                    'student_name': row.get('student_name', ''),
                    'email': row.get('email', ''),
                    'url': url,
                    'html_file': row.get('html_file', '')
                })
    
    print(f"Parsed {len(submissions)} GitHub URLs from CSV")
    return submissions


def extract_repo_name(url: str) -> str:
    """Extract repo name from GitHub URL."""
    # Handle various GitHub URL formats:
    # https://github.com/org/repo
    # https://github.com/org/repo.git
    # https://github.com/org/repo/tree/main
    
    # Remove /tree/branch suffix if present
    url = re.sub(r'/tree/[^/]+$', '', url)
    
    match = re.search(r'github\.com/([^/]+)/([^/\.]+)', url)
    if match:
        org, repo = match.groups()
        return f"{org}_{repo}"
    
    # Fallback: use last part of URL
    return url.rstrip('/').split('/')[-1].replace('.git', '')


def clone_repo(url: str, target_dir: Path) -> bool:
    """Clone a GitHub repo to target directory."""
    try:
        # Remove existing directory if present
        if target_dir.exists():
            shutil.rmtree(target_dir)
        
        # Clone with depth 1 for speed (latest commit only)
        subprocess.run(
            ['git', 'clone', '--depth', '1', url, str(target_dir)],
            check=True,
            capture_output=True,
            text=True,
            timeout=60
        )
        print(f"Cloned {url} to {target_dir}")
        return True
    except subprocess.TimeoutExpired:
        print(f"Timeout cloning {url}")
        return False
    except subprocess.CalledProcessError as e:
        print(f"Failed to clone {url}: {e.stderr}")
        return False
    except Exception as e:
        print(f"Error cloning {url}: {e}")
        return False


def clean_repo(repo_path: Path) -> None:
    """Remove unnecessary directories from repo."""
    if not repo_path.exists():
        return
    
    # First, remove top-level ignored directories
    for dir_name in os.listdir(repo_path):
        dir_path = repo_path / dir_name
        if (dir_name in IGNORE_DIRS or dir_name.startswith('.')) and dir_path.is_dir():
            try:
                shutil.rmtree(dir_path)
                print(f"Removed {dir_path}")
            except Exception as e:
                print(f"Failed to remove {dir_path}: {e}")
    
    # Then walk subdirectories to clean nested ignored dirs
    for root, dirs, files in os.walk(repo_path, topdown=True):
        # Modify dirs in place to skip ignored directories
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS and not d.startswith('.')]
        
        # Remove ignored directories in subdirectories
        for dir_name in list(dirs):
            dir_path = Path(root) / dir_name
            if dir_name in IGNORE_DIRS or dir_name.startswith('.'):
                try:
                    shutil.rmtree(dir_path)
                    print(f"Removed {dir_path}")
                except Exception as e:
                    print(f"Failed to remove {dir_path}: {e}")


def validate_repo(repo_path: Path) -> Dict[str, any]:
    """Validate repo structure and return validation results."""
    if not repo_path.exists():
        return {'valid': False, 'reason': 'Repo directory does not exist'}
    
    # Count relevant files
    relevant_exts = {'.js', '.jsx', '.ts', '.tsx', '.py', '.html', '.css', '.md'}
    file_count = 0
    has_readme = False
    has_package_json = False
    has_requirements = False
    
    for root, dirs, files in os.walk(repo_path):
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS and not d.startswith('.')]
        
        for file in files:
            ext = Path(file).suffix.lower()
            if ext in relevant_exts:
                file_count += 1
            
            if file.lower() == 'readme.md':
                has_readme = True
            if file == 'package.json':
                has_package_json = True
            if file == 'requirements.txt':
                has_requirements = True
    
    is_valid = file_count >= MIN_FILE_COUNT
    reason = f"File count: {file_count}" if not is_valid else "Valid"
    
    return {
        'valid': is_valid,
        'reason': reason,
        'file_count': file_count,
        'has_readme': has_readme,
        'has_package_json': has_package_json,
        'has_requirements': has_requirements
    }


def ingest_submissions(csv_path: Optional[Path] = None) -> Dict[str, any]:
    """Main ingestion workflow."""
    # Create repos directory
    REPOS_DIR.mkdir(exist_ok=True)
    
    # Find and parse CSV
    csv_path = csv_path or find_latest_csv()
    if not csv_path:
        return {'success': False, 'error': 'No CSV file found'}
    
    submissions = parse_submission_csv(csv_path)
    if not submissions:
        return {'success': False, 'error': 'No GitHub URLs found in CSV'}
    
    # Process each submission
    results = {
        'total': len(submissions),
        'cloned': 0,
        'valid': 0,
        'invalid': 0,
        'failed': 0,
        'repos': []
    }
    
    for sub in submissions:
        repo_name = extract_repo_name(sub['url'])
        repo_path = REPOS_DIR / repo_name
        
        print(f"\nProcessing: {sub['student_name']} - {repo_name}")
        
        # Clone repo
        if clone_repo(sub['url'], repo_path):
            results['cloned'] += 1
            
            # Clean repo
            clean_repo(repo_path)
            
            # Validate repo
            validation = validate_repo(repo_path)
            
            if validation['valid']:
                results['valid'] += 1
                print(f"✓ Valid repo: {validation['reason']}")
            else:
                results['invalid'] += 1
                print(f"✗ Invalid repo: {validation['reason']}")
                # Remove invalid repos
                shutil.rmtree(repo_path, ignore_errors=True)
            
            results['repos'].append({
                'student': sub['student_name'],
                'email': sub['email'],
                'repo_name': repo_name,
                'url': sub['url'],
                'valid': validation['valid'],
                'validation': validation
            })
        else:
            results['failed'] += 1
            results['repos'].append({
                'student': sub['student_name'],
                'email': sub['email'],
                'repo_name': repo_name,
                'url': sub['url'],
                'valid': False,
                'validation': {'reason': 'Clone failed'}
            })
    
    print(f"\n=== Ingestion Summary ===")
    print(f"Total submissions: {results['total']}")
    print(f"Successfully cloned: {results['cloned']}")
    print(f"Valid repos: {results['valid']}")
    print(f"Invalid repos: {results['invalid']}")
    print(f"Failed to clone: {results['failed']}")
    
    return results


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Ingest HootCamp submissions from CSV")
    parser.add_argument('--csv', type=str, help='Path to CSV file (default: latest in submissions/)')
    parser.add_argument('--dry-run', action='store_true', help='Parse CSV but do not clone')
    
    args = parser.parse_args()
    
    csv_path = Path(args.csv) if args.csv else None
    
    if args.dry_run:
        csv_path = csv_path or find_latest_csv()
        if csv_path:
            submissions = parse_submission_csv(csv_path)
            print(f"\nDry run: Found {len(submissions)} GitHub URLs")
            for sub in submissions[:5]:  # Show first 5
                print(f"  - {sub['student_name']}: {sub['url']}")
            if len(submissions) > 5:
                print(f"  ... and {len(submissions) - 5} more")
    else:
        results = ingest_submissions(csv_path)
