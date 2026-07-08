import os
from pathlib import Path

IGNORE_DIRS = {'node_modules', 'venv', '.venv', '__pycache__', '.git', 'dist', 'build', '.next'}
IGNORE_EXTS = {'.lock', '.png', '.jpg', '.jpeg', '.gif', '.svg', '.ico', '.pyc', '.map'}
RELEVANT_EXTS = {'.js', '.jsx', '.ts', '.tsx', '.py', '.html', '.css', '.md'}

def get_dependencies(repo_path: str) -> dict:
    """Finds package.json, requirements.txt, or Pipfile and returns their content."""
    deps = {}
    for filename in ['package.json', 'requirements.txt', 'Pipfile']:
        filepath = os.path.join(repo_path, filename)
        if os.path.exists(filepath):
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    deps[filename] = f.read()
            except Exception as e:
                deps[filename] = f"Error reading {filename}: {e}"
    return deps

def extract_source_code(repo_path: str) -> dict:
    """
    Traverses the repository and extracts relevant source code.
    Returns a dictionary mapping file paths (relative to repo root) to their content.
    """
    source_files = {}
    base_path = Path(repo_path)
    
    for root, dirs, files in os.walk(base_path):
        # Mutate dirs in place to skip ignored directories
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS and not d.startswith('.')]
        
        for file in files:
            ext = os.path.splitext(file)[1].lower()
            if ext in RELEVANT_EXTS:
                filepath = Path(root) / file
                rel_path = filepath.relative_to(base_path)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        source_files[str(rel_path)] = f.read()
                except Exception:
                    pass  # Ignore files that can't be read as utf-8
                    
    return source_files

def get_code_chunks(source_files: dict, max_chunk_size: int = 40000) -> list:
    """
    Naively chunks the extracted source files into blocks to fit within typical LLM context limits.
    Returns a list of strings, each containing multiple file contents.
    """
    chunks = []
    current_chunk = ""
    
    for filepath, content in source_files.items():
        file_text = f"\n--- File: {filepath} ---\n{content}\n"
        
        if len(current_chunk) + len(file_text) > max_chunk_size and current_chunk:
            chunks.append(current_chunk)
            current_chunk = file_text
        else:
            current_chunk += file_text
            
    if current_chunk:
        chunks.append(current_chunk)
        
    return chunks

def extract_readme(repo_path: str) -> str:
    """Extract README content if present."""
    base_path = Path(repo_path)
    for readme_name in ['README.md', 'readme.md', 'README.txt', 'readme.txt']:
        readme_path = base_path / readme_name
        if readme_path.exists():
            try:
                with open(readme_path, 'r', encoding='utf-8') as f:
                    return f.read()
            except Exception:
                pass
    return ""
