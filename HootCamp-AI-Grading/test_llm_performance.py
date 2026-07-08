#!/usr/bin/env python3
"""LLM Performance Comparison Test - LMStudio vs TrussedAI"""

import os
import time
import sys
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from llm_adapter import chat

# Test prompts for gate evaluation
TEST_PROMPTS = {
    'ai_integration': {
        'system': 'You are an expert code reviewer. Analyze the provided code snippets and determine if the project implements AI/ML features. Return JSON: {"present": boolean, "explanation": string}',
        'prompt': 'Code contains: ai_routes.py with OpenAI API integration, predict_helpers.py with ML inference, app.py imports AI blueprints. Does this project have AI integration?'
    },
    'backend_database': {
        'system': 'You are an expert code reviewer. Analyze the provided code snippets and determine if the project has a backend database with CRUD operations. Return JSON: {"present": boolean, "explanation": string}',
        'prompt': 'Code contains: models.py with SQLAlchemy schemas, instance/coreai.db SQLite database, Flask routes with db.session.commit() and db.session.delete(). Does this project have backend database with CRUD?'
    },
    'authentication': {
        'system': 'You are an expert code reviewer. Analyze the provided code snippets and determine if the project implements user authentication. Return JSON: {"present": boolean, "explanation": string}',
        'prompt': 'Code contains: flask_login.LoginManager, @login_manager.user_loader, auth.py blueprint with registration/login endpoints, SECRET_KEY for session security. Does this project have authentication?'
    }
}

def test_provider(provider_name, env_vars):
    """Test a single LLM provider"""
    print(f"\n{'='*60}")
    print(f"Testing: {provider_name}")
    print(f"{'='*60}")
    
    # Set environment variables for this provider
    for key, value in env_vars.items():
        os.environ[key] = value
    
    # Re-import to get new config
    import importlib
    import llm_adapter
    importlib.reload(llm_adapter)
    from llm_adapter import chat, test_connection
    
    # Test connection
    if not test_connection():
        print(f"✗ {provider_name} connection failed")
        return None
    
    print(f"✓ {provider_name} connected")
    
    results = {}
    total_time = 0
    total_tokens = 0
    
    for feature, prompts in TEST_PROMPTS.items():
        print(f"\nTesting {feature}...")
        start = time.time()
        
        try:
            response = chat(
                system=prompts['system'],
                prompt=prompts['prompt'],
                max_tokens=512
            )
            
            elapsed = time.time() - start
            usage = response.get('usage', {})
            tokens_in = usage.get('prompt_tokens', 0)
            tokens_out = usage.get('completion_tokens', 0)
            tokens_total = usage.get('total_tokens', 0)
            
            content = response.get('choices', [{}])[0].get('message', {}).get('content', '')
            
            results[feature] = {
                'time': elapsed,
                'tokens_in': tokens_in,
                'tokens_out': tokens_out,
                'tokens_total': tokens_total,
                'response': content[:100] + '...' if len(content) > 100 else content
            }
            
            total_time += elapsed
            total_tokens += tokens_total
            
            print(f"  Time: {elapsed:.2f}s | Tokens: {tokens_in} in, {tokens_out} out, {tokens_total} total")
        except Exception as e:
            print(f"  ✗ Error: {e}")
            results[feature] = {'error': str(e)}
    
    # Summary
    print(f"\n{'='*60}")
    print(f"{provider_name} Summary:")
    print(f"  Total time: {total_time:.2f}s")
    print(f"  Total tokens: {total_tokens}")
    print(f"  Avg time per request: {total_time/len(TEST_PROMPTS):.2f}s")
    print(f"  Tokens per second: {total_tokens/total_time:.1f}")
    print(f"{'='*60}")
    
    return {
        'provider': provider_name,
        'total_time': total_time,
        'total_tokens': total_tokens,
        'avg_time': total_time/len(TEST_PROMPTS),
        'tokens_per_sec': total_tokens/total_time,
        'results': results
    }

def main():
    print("LLM Performance Comparison Test")
    print("="*60)
    
    # Test LMStudio
    lmstudio_config = {
        'LLM_PROVIDER': 'lmstudio',
        'LMSTUDIO_HOST': 'http://localhost:1234',
        'LMSTUDIO_MODEL': 'qwen/qwen3.6-27b',
        'MOCK_MODE': 'false'
    }
    
    lmstudio_results = test_provider('LMStudio (Local)', lmstudio_config)
    
    # Test TrussedAI (if API key available)
    trussedai_key = os.getenv('TRUSSEDAI_API_KEY', '')
    if trussedai_key:
        trussedai_config = {
            'LLM_PROVIDER': 'trussedai',
            'TRUSSEDAI_API_KEY': trussedai_key,
            'TRUSSEDAI_HOST': 'https://api.trussed.ai',
            'TRUSSEDAI_MODEL': 'gpt-4o-mini',
            'MOCK_MODE': 'false'
        }
        
        trussedai_results = test_provider('TrussedAI (Cloud)', trussedai_config)
    else:
        print("\nSkipping TrussedAI - no API key configured")
        print("Set TRUSSEDAI_API_KEY environment variable to test")
        trussedai_results = None
    
    # Comparison
    if lmstudio_results and trussedai_results:
        print(f"\n{'='*60}")
        print("PERFORMANCE COMPARISON")
        print(f"{'='*60}")
        
        print(f"\nTime Comparison:")
        print(f"  LMStudio: {lmstudio_results['total_time']:.2f}s")
        print(f"  TrussedAI: {trussedai_results['total_time']:.2f}s")
        speedup = lmstudio_results['total_time'] / trussedai_results['total_time']
        print(f"  Speedup: {speedup:.2f}x {'(LMStudio faster)' if speedup > 1 else '(TrussedAI faster)'}")
        
        print(f"\nToken Throughput:")
        print(f"  LMStudio: {lmstudio_results['tokens_per_sec']:.1f} tokens/sec")
        print(f"  TrussedAI: {trussedai_results['tokens_per_sec']:.1f} tokens/sec")
        
        print(f"\nCost Estimate (TrussedAI only):")
        # gpt-4o-mini pricing: $0.15/1M input, $0.60/1M output
        trussedai_cost = (trussedai_results['total_tokens'] * 0.15 / 1_000_000)  # rough estimate
        print(f"  Estimated cost: ${trussedai_cost:.4f}")
        print(f"  LMStudio: Free (local)")

if __name__ == "__main__":
    main()
