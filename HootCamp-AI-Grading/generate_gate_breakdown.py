#!/usr/bin/env python3
"""
Generate a breakdown report showing pass/fail counts for each gate category.
"""

import json
from collections import defaultdict

def load_evaluation_results(json_path):
    """Load evaluation results from JSON."""
    with open(json_path, 'r') as f:
        return json.load(f)

def generate_gate_breakdown(results):
    """Generate breakdown of pass/fail for each gate."""
    gates = ['ai_integration', 'backend_database', 'authentication', 'readme_completeness', 'deployment_live', 'demo_video_present']
    
    breakdown = {
        'total_repos': len(results),
        'overall_pass': 0,
        'overall_fail': 0,
        'gates': {}
    }
    
    for gate in gates:
        breakdown['gates'][gate] = {
            'pass': 0,
            'fail': 0,
            'failed_students': []
        }
    
    for result in results:
        # Overall pass/fail
        if result['gate_pass']:
            breakdown['overall_pass'] += 1
        else:
            breakdown['overall_fail'] += 1
        
        # Individual gates
        for gate in gates:
            if 'gate_evaluations' in result and gate in result['gate_evaluations']:
                present = result['gate_evaluations'][gate].get('present', False)
                if present:
                    breakdown['gates'][gate]['pass'] += 1
                else:
                    breakdown['gates'][gate]['fail'] += 1
                    # Extract student name from repo path
                    repo_name = result['repo_path'].split('/')[-1]
                    breakdown['gates'][gate]['failed_students'].append(repo_name)
    
    return breakdown

def print_breakdown(breakdown):
    """Print the breakdown report."""
    print("=" * 80)
    print("GATE EVALUATION BREAKDOWN REPORT")
    print("=" * 80)
    print()
    print(f"Total Repositories Evaluated: {breakdown['total_repos']}")
    print(f"Overall Pass: {breakdown['overall_pass']} ({breakdown['overall_pass']/breakdown['total_repos']*100:.1f}%)")
    print(f"Overall Fail: {breakdown['overall_fail']} ({breakdown['overall_fail']/breakdown['total_repos']*100:.1f}%)")
    print()
    print("-" * 80)
    print("INDIVIDUAL GATE BREAKDOWN")
    print("-" * 80)
    print()
    
    for gate, stats in breakdown['gates'].items():
        total = stats['pass'] + stats['fail']
        pass_rate = stats['pass'] / total * 100 if total > 0 else 0
        print(f"{gate.replace('_', ' ').title()}:")
        print(f"  Pass: {stats['pass']} ({pass_rate:.1f}%)")
        print(f"  Fail: {stats['fail']} ({100-pass_rate:.1f}%)")
        if stats['failed_students']:
            print(f"  Failed repos: {', '.join(stats['failed_students'][:5])}")
            if len(stats['failed_students']) > 5:
                print(f"  ... and {len(stats['failed_students']) - 5} more")
        print()

def save_breakdown_to_csv(breakdown, output_path):
    """Save breakdown to CSV."""
    import csv
    
    with open(output_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['Gate', 'Pass', 'Fail', 'Pass Rate %'])
        
        for gate, stats in breakdown['gates'].items():
            total = stats['pass'] + stats['fail']
            pass_rate = stats['pass'] / total * 100 if total > 0 else 0
            writer.writerow([gate, stats['pass'], stats['fail'], f"{pass_rate:.1f}"])
        
        writer.writerow([])
        writer.writerow(['Overall', breakdown['overall_pass'], breakdown['overall_fail'], f"{breakdown['overall_pass']/breakdown['total_repos']*100:.1f}"])
    
    print(f"Breakdown CSV saved to {output_path}")

def main():
    # Load results
    results = load_evaluation_results('results/evaluation_results.json')
    
    # Generate breakdown
    breakdown = generate_gate_breakdown(results)
    
    # Print report
    print_breakdown(breakdown)
    
    # Save to CSV
    save_breakdown_to_csv(breakdown, 'results/gate_breakdown.csv')

if __name__ == '__main__':
    main()
