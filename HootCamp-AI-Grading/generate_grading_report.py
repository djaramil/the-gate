#!/usr/bin/env python3
"""
Generate grading report CSV for Canvas upload.
Matches evaluation results with student information from submissions CSV.
"""

import json
import csv
from pathlib import Path

def load_submissions(csv_path):
    """Load student submissions from CSV."""
    students = []
    with open(csv_path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            url = row['submission_url']
            # Extract repo name from GitHub URL
            if 'github.com' in url:
                # Handle URLs like: https://github.com/FAU-AI-HootCamp-Summer-2026/week3-jaltamirano6933
                # or: https://github.com/abarahonacab2025-code/week3-abarahonacab2025-code.git
                parts = url.split('/')
                repo_name = parts[-1].replace('.git', '')
                full_path = '/'.join(parts[-2:])
                students.append({
                    'name': row['student_name'],
                    'email': row['email'],
                    'url': url,
                    'repo_name': repo_name,
                    'full_path': full_path,
                    'is_direct_url': False
                })
            else:
                # Handle non-GitHub URLs (Vercel, etc.)
                students.append({
                    'name': row['student_name'],
                    'email': row['email'],
                    'url': url,
                    'repo_name': None,
                    'full_path': None,
                    'is_direct_url': True
                })
    return students

def load_evaluation_results(json_path):
    """Load evaluation results from JSON."""
    with open(json_path, 'r') as f:
        return json.load(f)

def extract_repo_name(repo_path):
    """Extract repo name from repo path, removing organization prefix."""
    full_name = repo_path.split('/')[-1]
    # Remove organization prefix if present (e.g., FAU-AI-HootCamp-Summer-2026_week3-xxx -> week3-xxx)
    if '_' in full_name:
        parts = full_name.split('_')
        # Find the part that starts with 'week' (week2, week3, etc.)
        for i, part in enumerate(parts):
            if part.startswith('week'):
                return '_'.join(parts[i:])
    return full_name

def generate_grading_report(evaluation_results, students):
    """Generate grading report matching repos to students."""
    report = []
    matched_students = set()
    
    # Create a mapping from repo names to students
    repo_to_student = {}
    for student in students:
        if student['repo_name']:
            repo_to_student[student['repo_name']] = student
        if student['full_path']:
            repo_to_student[student['full_path']] = student
    
    # Manual mappings for special cases
    manual_mappings = {
        'leonfallett10-netizen_studyflow': {'name': 'Leon Fallett', 'email': 'lfallett2021@fau.edu', 'url': 'https://github.com/leonfallett10-netizen/studyflow'},
        'week3-olmard-guillaume': {'name': 'Bianca Guillaume', 'email': 'bguillaume2024@fau.edu', 'url': 'https://github.com/FAU-AI-HootCamp-Summer-2026/week3-Illianca01'},
        'week3-CruzIsaiah': {'name': 'Isaiah Cruz', 'email': 'icruz2020@fau.edu', 'url': 'https://th-five-bice.vercel.app/'},
        'week3-gissellapam': {'name': 'Gissella Palomino', 'email': 'grodri32@fau.edu', 'url': 'https://employee-tracker-six-omega.vercel.app/login'},
        'week2-Anthonyhage99': {'name': 'Anthony Hage', 'email': 'ahage2024@fau.edu', 'url': 'https://github.com/FAU-AI-HootCamp-Summer-2026/week2-Anthonyhage99.git'},
        'week3-Yaswanth-Kotipalli': {'name': 'Yaswanth Durga Kiran Kotipalli', 'email': 'ykotipalli2024@fau.edu', 'url': 'https://github.com/FAU-AI-HootCamp-Summer-2026/week3-Yaswanth-Kotipalli/tree/main'}
    }
    
    for result in evaluation_results:
        repo_name = extract_repo_name(result['repo_path'])
        student = None
        
        # Check manual mappings first
        if repo_name in manual_mappings:
            student = manual_mappings[repo_name]
        # Try exact match
        elif repo_name in repo_to_student:
            student = repo_to_student[repo_name]
        else:
            # Try matching with organization prefix
            for key, value in repo_to_student.items():
                if repo_name == key.split('/')[-1]:
                    student = value
                    break
                if repo_name.lower() in key.lower():
                    student = value
                    break
        
        if student:
            # Skip if this student was already matched (avoid duplicates)
            if student['name'] in matched_students:
                continue
            matched_students.add(student['name'])
            
            # Determine pass/fail and reason
            if result['gate_pass']:
                status = 'PASS'
                reason = 'All gate requirements met'
            else:
                status = 'FAIL'
                missing = result['gate_decision'].get('missing_requirements', [])
                ast_issues = result['gate_decision'].get('ast_issues', [])
                reasons = []
                if missing:
                    reasons.append(f"Missing: {', '.join(missing)}")
                if ast_issues:
                    reasons.append(f"AST: {', '.join(ast_issues)}")
                reason = '; '.join(reasons) if reasons else 'Failed gate evaluation'
            
            # Extract individual gate statuses
            gate_evaluations = result.get('gate_evaluations', {})
            gates = {
                'AI Integration': gate_evaluations.get('ai_integration', {}).get('present', False),
                'Backend Database': gate_evaluations.get('backend_database', {}).get('present', False),
                'Authentication': gate_evaluations.get('authentication', {}).get('present', False),
                'Readme Completeness': gate_evaluations.get('readme_completeness', {}).get('present', False),
                'Deployment Live': gate_evaluations.get('deployment_live', {}).get('present', False),
                'Demo Video Present': gate_evaluations.get('demo_video_present', {}).get('present', False)
            }
            
            report.append({
                'Student Name': student['name'],
                'Email': student['email'],
                'Repository': repo_name,
                'Status': status,
                'Reason': reason,
                'Submission URL': student['url'],
                **{k: 'PASS' if v else 'FAIL' for k, v in gates.items()}
            })
        else:
            # No matching student found
            report.append({
                'Student Name': 'UNKNOWN',
                'Email': 'unknown@fau.edu',
                'Repository': repo_name,
                'Status': 'FAIL' if not result['gate_pass'] else 'PASS',
                'Reason': 'No matching student in submissions CSV',
                'Submission URL': result['repo_path'],
                'AI Integration': 'N/A',
                'Backend Database': 'N/A',
                'Authentication': 'N/A',
                'Readme Completeness': 'N/A',
                'Deployment Live': 'N/A',
                'Demo Video Present': 'N/A'
            })
    
    return report

def save_grading_report(report, output_path):
    """Save grading report to XLSX."""
    try:
        import pandas as pd
    except ImportError:
        print("Error: pandas not installed. Install with: pip install pandas openpyxl")
        return
    
    # Convert to DataFrame
    fieldnames = [
        'Student Name', 'Email', 'Repository', 'Status', 'Reason', 'Submission URL',
        'AI Integration', 'Backend Database', 'Authentication',
        'Readme Completeness', 'Deployment Live', 'Demo Video Present'
    ]
    df = pd.DataFrame(report, columns=fieldnames)
    
    # Save to XLSX
    df.to_excel(output_path, index=False, engine='openpyxl')
    
    print(f"Grading report saved to {output_path}")
    print(f"Total entries: {len(report)}")
    
    # Print summary
    passed = sum(1 for r in report if r['Status'] == 'PASS')
    failed = sum(1 for r in report if r['Status'] == 'FAIL')
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")

def main():
    # Paths
    submissions_csv = 'submissions/week3_submissions_updated.csv'
    evaluation_json = 'results/evaluation_results.json'
    output_file = 'results/hootcamp_grading_report.xlsx'
    
    # Load data
    print("Loading submissions...")
    students = load_submissions(submissions_csv)
    print(f"Found {len(students)} students")
    
    print("Loading evaluation results...")
    results = load_evaluation_results(evaluation_json)
    print(f"Found {len(results)} evaluation results")
    
    # Generate report
    print("Generating grading report...")
    report = generate_grading_report(results, students)
    
    # Save report
    save_grading_report(report, output_file)

if __name__ == '__main__':
    main()
