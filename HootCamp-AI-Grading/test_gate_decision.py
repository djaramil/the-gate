#!/usr/bin/env python3
"""Unit tests for gate decision logic"""

import sys
sys.path.insert(0, '.')
from hc_evaluate import compute_gate_pass

def test_all_requirements_pass():
    """Test gate pass when all requirements are met"""
    gate_evaluations = {
        'ai_integration': {'present': True},
        'backend_database': {'present': True},
        'authentication': {'present': True},
        'readme_completeness': {'present': True},
        'deployment_live': {'present': True},
        'demo_video_present': {'present': True}
    }
    ast_findings = [
        {'code': 'SUPABASE_CLIENT'},
        {'code': 'AUTH_LIB'},
        {'code': 'AI_OR_BACKEND_LIB'}
    ]
    
    result = compute_gate_pass(gate_evaluations, ast_findings)
    assert result['gate_pass'] == True, "Should pass when all requirements met"
    assert len(result['missing_requirements']) == 0, "Should have no missing requirements"
    assert len(result['ast_issues']) == 0, "Should have no AST issues"
    print("✓ All requirements pass test passed")

def test_missing_requirement():
    """Test gate fail when requirement is missing"""
    gate_evaluations = {
        'ai_integration': {'present': True},
        'backend_database': {'present': False},  # Missing
        'authentication': {'present': True},
        'readme_completeness': {'present': True},
        'deployment_live': {'present': True},
        'demo_video_present': {'present': True}
    }
    ast_findings = [
        {'code': 'SUPABASE_CLIENT'},
        {'code': 'AUTH_LIB'},
        {'code': 'AI_OR_BACKEND_LIB'}
    ]
    
    result = compute_gate_pass(gate_evaluations, ast_findings)
    assert result['gate_pass'] == False, "Should fail when requirement missing"
    assert 'backend_database' in result['missing_requirements'], "Should list missing requirement"
    print("✓ Missing requirement test passed")

def test_ast_validation_js_ts_repo():
    """Test AST validation applies to JS/TS repos"""
    gate_evaluations = {
        'ai_integration': {'present': True},
        'backend_database': {'present': True},
        'authentication': {'present': True},
        'readme_completeness': {'present': True},
        'deployment_live': {'present': True},
        'demo_video_present': {'present': True}
    }
    # JS/TS repo with findings but missing Supabase
    ast_findings = [
        {'code': 'AUTH_LIB'},
        {'code': 'AI_OR_BACKEND_LIB'}
    ]
    
    result = compute_gate_pass(gate_evaluations, ast_findings)
    assert result['gate_pass'] == False, "Should fail when AST validation fails"
    assert 'No Supabase usage detected in AST' in result['ast_issues'], "Should report AST issue"
    assert result['has_js_ts_files'] == True, "Should detect JS/TS files"
    print("✓ AST validation JS/TS repo test passed")

def test_ast_validation_skipped_python_repo():
    """Test AST validation skipped for Python repos"""
    gate_evaluations = {
        'ai_integration': {'present': True},
        'backend_database': {'present': True},
        'authentication': {'present': True},
        'readme_completeness': {'present': True},
        'deployment_live': {'present': True},
        'demo_video_present': {'present': True}
    }
    # Python repo - no JS/TS findings
    ast_findings = []
    
    result = compute_gate_pass(gate_evaluations, ast_findings)
    assert result['gate_pass'] == True, "Should pass when AST validation skipped"
    assert len(result['ast_issues']) == 0, "Should have no AST issues"
    assert result['has_js_ts_files'] == False, "Should detect no JS/TS files"
    print("✓ AST validation skipped Python repo test passed")

def test_multiple_missing_requirements():
    """Test gate fail with multiple missing requirements"""
    gate_evaluations = {
        'ai_integration': {'present': False},
        'backend_database': {'present': False},
        'authentication': {'present': True},
        'readme_completeness': {'present': True},
        'deployment_live': {'present': True},
        'demo_video_present': {'present': True}
    }
    ast_findings = []
    
    result = compute_gate_pass(gate_evaluations, ast_findings)
    assert result['gate_pass'] == False, "Should fail with multiple missing"
    assert 'ai_integration' in result['missing_requirements'], "Should list ai_integration"
    assert 'backend_database' in result['missing_requirements'], "Should list backend_database"
    print("✓ Multiple missing requirements test passed")

def test_commit_hygiene_optional():
    """Test commit_hygiene is optional (not in must-have list)"""
    gate_evaluations = {
        'ai_integration': {'present': True},
        'backend_database': {'present': True},
        'authentication': {'present': True},
        'readme_completeness': {'present': True},
        'deployment_live': {'present': True},
        'demo_video_present': {'present': True},
        'commit_hygiene': {'present': False}  # Optional, should not affect pass
    }
    ast_findings = []
    
    result = compute_gate_pass(gate_evaluations, ast_findings)
    assert result['gate_pass'] == True, "Should pass even without commit_hygiene"
    print("✓ Commit hygiene optional test passed")

if __name__ == "__main__":
    print("Running gate decision unit tests...")
    test_all_requirements_pass()
    test_missing_requirement()
    test_ast_validation_js_ts_repo()
    test_ast_validation_skipped_python_repo()
    test_multiple_missing_requirements()
    test_commit_hygiene_optional()
    print("\n✓ All gate decision tests passed!")
