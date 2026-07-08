#!/usr/bin/env python3
"""Unit tests for AST checker"""

import subprocess
import json
import tempfile
import os
from pathlib import Path

def test_supabase_detection():
    """Test AST checker detects Supabase usage"""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = Path(tmpdir) / "test.js"
        test_file.write_text("""
import { createClient } from '@supabase/supabase-js'
const supabase = createClient(url, key)
supabase.from('users').select('*')
""")
        
        result = subprocess.run(
            ['node', 'js_ts_ast_checker.js', tmpdir],
            capture_output=True,
            text=True
        )
        
        findings = json.loads(result.stdout).get('findings', [])
        assert any(f['code'] == 'SUPABASE_CLIENT' for f in findings), "Should detect SUPABASE_CLIENT"
        assert any(f['code'] == 'SUPABASE_CRUD' for f in findings), "Should detect SUPABASE_CRUD"
        print("✓ Supabase detection test passed")

def test_auth_detection():
    """Test AST checker detects auth libraries"""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = Path(tmpdir) / "test.js"
        test_file.write_text("""
import jwt from 'jsonwebtoken'
import passport from 'passport'
function login() { return true }
""")
        
        result = subprocess.run(
            ['node', 'js_ts_ast_checker.js', tmpdir],
            capture_output=True,
            text=True
        )
        
        findings = json.loads(result.stdout).get('findings', [])
        assert any(f['code'] == 'AUTH_LIB' for f in findings), "Should detect AUTH_LIB"
        assert any(f['code'] == 'AUTH_HINT' for f in findings), "Should detect AUTH_HINT"
        print("✓ Auth detection test passed")

def test_ai_library_detection():
    """Test AST checker detects AI libraries"""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = Path(tmpdir) / "test.js"
        test_file.write_text("""
import OpenAI from 'openai'
import axios from 'axios'
""")
        
        result = subprocess.run(
            ['node', 'js_ts_ast_checker.js', tmpdir],
            capture_output=True,
            text=True
        )
        
        findings = json.loads(result.stdout).get('findings', [])
        assert any(f['code'] == 'AI_OR_BACKEND_LIB' for f in findings), "Should detect AI_OR_BACKEND_LIB"
        print("✓ AI library detection test passed")

def test_security_detection():
    """Test AST checker detects security issues"""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = Path(tmpdir) / "test.js"
        test_file.write_text("""
eval('code')
new Function('x', 'return x')
const child_process = require('child_process')
child_process.exec('ls')
""")
        
        result = subprocess.run(
            ['node', 'js_ts_ast_checker.js', tmpdir],
            capture_output=True,
            text=True
        )
        
        findings = json.loads(result.stdout).get('findings', [])
        assert any(f['code'] == 'DANGEROUS_EVAL' for f in findings), "Should detect DANGEROUS_EVAL"
        assert any(f['code'] == 'SHELL_EXEC' for f in findings), "Should detect SHELL_EXEC"
        print("✓ Security detection test passed")

def test_no_findings():
    """Test AST checker returns no findings for clean code"""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = Path(tmpdir) / "test.js"
        test_file.write_text("""
function add(a, b) {
    return a + b
}
""")
        
        result = subprocess.run(
            ['node', 'js_ts_ast_checker.js', tmpdir],
            capture_output=True,
            text=True
        )
        
        findings = json.loads(result.stdout).get('findings', [])
        assert len(findings) == 0, "Should have no findings for clean code"
        print("✓ No findings test passed")

if __name__ == "__main__":
    print("Running AST checker unit tests...")
    test_supabase_detection()
    test_auth_detection()
    test_ai_library_detection()
    test_security_detection()
    test_no_findings()
    print("\n✓ All AST checker tests passed!")
