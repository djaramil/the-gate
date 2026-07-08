import json
import re
import sys
import time
from typing import Dict, List
from llm_adapter import chat
from retrieval import CodeRetriever

# Define the gate-specific features and their IR queries
# Optional gates (not required for gate pass) are commented out to speed up evaluation
GATE_FEATURES = {
    'ai_integration': "AI features, OpenAI API, language model, LLM, machine learning, AI-powered functionality, intelligent features",
    'backend_database': "Supabase, database, PostgreSQL, data persistence, backend API, CRUD operations",
    'authentication': "auth, login, signup, signIn, signUp, signOut, user authentication, protected routes, session management",
    'readme_completeness': "README, documentation, setup instructions, project description, deployment link, demo video",
    'deployment_live': "deployment, Vercel, Netlify, Render, live URL, production build, hosting",
    'demo_video_present': "demo video, walkthrough, screencast, video demonstration, loom, youtube, watch video",
    # 'commit_hygiene': "git history, commit messages, version control, branches, pull requests"  # Optional - skipped for speed
}

class FeatureEvaluation:
    def __init__(self, present: bool, explanation: str):
        self.present = present
        self.explanation = explanation
    
    def model_dump(self):
        return {"present": self.present, "explanation": self.explanation}

def evaluate_feature(retriever: CodeRetriever, feature_key: str, query: str, verbose: bool = True, top_k: int = 7) -> FeatureEvaluation:
    if verbose: 
        print(f"  [{feature_key}] Evaluating...")
        sys.stdout.flush()
    
    feature_start = time.time()
    
    # Phase 1: Retrieve the top k most relevant chunks
    if verbose:
        print(f"  [{feature_key}] Retrieving relevant code chunks (top_k={top_k})...")
        sys.stdout.flush()
    
    relevant_chunks = retriever.search(query, top_k=top_k)
    combined_code = "\n\n".join(relevant_chunks)
    
    # Calculate dynamic timeout based on code size
    code_size = len(combined_code)
    base_timeout = 120  # base timeout in seconds (increased for LMStudio)
    size_factor = code_size / 5000  # 5k chars = 1 extra second (more aggressive scaling)
    dynamic_timeout = int(base_timeout + size_factor)
    dynamic_timeout = min(dynamic_timeout, 300)  # cap at 5 minutes
    
    if verbose:
        print(f"  [{feature_key}] Found {len(relevant_chunks)} relevant chunks ({time.time() - feature_start:.2f}s, {code_size} chars, timeout: {dynamic_timeout}s)")
        sys.stdout.flush()
    
    # Phase 2: Build the strict prompt for fact extraction
    prompt = (
        f"You are a strict code analysis bot.\n"
        f"Your task is to determine if the following feature is implemented in the provided code snippets: '{query}'\n\n"
        f"Analyze the code and provide:\n"
        f"1. A boolean 'present' (true/false) indicating if the feature is implemented\n"
        f"2. An 'explanation' with specific evidence from the code (file names, function names, patterns)\n\n"
        f"Respond in JSON format with keys 'present' and 'explanation'.\n\n"
        f"Code Snippets:\n{combined_code}"
    )

    content = ""
    try:
        if verbose:
            print(f"  [{feature_key}] Querying LLM...")
            sys.stdout.flush()
        
        llm_start = time.time()
        response = chat(
            system="You are a code analysis expert. Always respond with valid JSON.",
            prompt=prompt,
            max_tokens=1024,
            temperature=0.0,
            timeout=dynamic_timeout
        )
        llm_time = time.time() - llm_start
        
        if verbose:
            print(f"  [{feature_key}] LLM response received ({llm_time:.2f}s)")
            sys.stdout.flush()
        
        content = response.get('choices', [{}])[0].get('message', {}).get('content', '').strip()
        
        # Cleanup potential markdown
        if content.startswith('```json'):
            content = content[7:]
        elif content.startswith('```'):
            content = content[3:]
        if content.endswith('```'):
            content = content[:-3]
        
        start_idx = content.find('{')
        end_idx = content.rfind('}')
        if start_idx != -1 and end_idx != -1:
            content = content[start_idx:end_idx+1]

        parsed_json = json.loads(content)
        result = FeatureEvaluation(
            present=parsed_json.get('present', False),
            explanation=parsed_json.get('explanation', 'No explanation provided')
        )
        
        if verbose:
            status = "✓ PRESENT" if result.present else "✗ ABSENT"
            print(f"  [{feature_key}] {status} (total: {time.time() - feature_start:.2f}s)")
            sys.stdout.flush()
        
        return result
        
    except Exception as e:
        if verbose: 
            print(f"  [{feature_key}] ✗ ERROR: {e}")
            sys.stdout.flush()
        
        # Fallback: simple string matching
        content_lower = content.lower()
        if re.search(r'"present"\s*:\s*true', content_lower):
            if verbose: 
                print(f"  [{feature_key}] ✓ PRESENT (fallback regex)")
                sys.stdout.flush()
            return FeatureEvaluation(present=True, explanation=f"Extracted via fallback regex. Raw response: {content}")
        elif re.search(r'"present"\s*:\s*false', content_lower):
            if verbose: 
                print(f"  [{feature_key}] ✗ ABSENT (fallback regex)")
                sys.stdout.flush()
            return FeatureEvaluation(present=False, explanation=f"Extracted via fallback regex. Raw response: {content}")
            
        if verbose:
            print(f"  [{feature_key}] ✗ ERROR (total: {time.time() - feature_start:.2f}s)")
            sys.stdout.flush()
        return FeatureEvaluation(present=False, explanation=f"Error parsing LLM response: {e}; Raw response: {content}")

def perform_gate_evaluations(retriever: CodeRetriever, verbose: bool = True, top_k: int = 7) -> Dict:
    """Iterates through all gate features and returns a dictionary of results."""
    results = {}
    
    for feature_key, query in GATE_FEATURES.items():
        eval_result = evaluate_feature(retriever, feature_key, query, verbose=verbose, top_k=top_k)
        results[feature_key] = eval_result.model_dump()
        
    return results
