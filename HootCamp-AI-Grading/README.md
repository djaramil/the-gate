# HootCamp-AI-Grading scaffold

Quick start

1. Python deps:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. Node deps:

```bash
npm install
```

3. Run JS/TS static checks:

```bash
python hc_evaluate.py evaluate-local --path submissions/sample-student
```

4. Embedding test (if using fallback):

```bash
python -c "from sentence_transformers import SentenceTransformer; m=SentenceTransformer('all-mpnet-base-v2'); print(m.encode(['a','b']).shape)"
```
