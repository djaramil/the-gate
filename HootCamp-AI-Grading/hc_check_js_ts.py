import subprocess, json, sys
from pathlib import Path

def run_checker(target_path):
    p = Path(target_path)
    if not p.exists():
        raise FileNotFoundError(target_path)
    cmd = ["node", "js_ts_ast_checker.js", str(target_path)]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        print("checker error:", res.stderr, file=sys.stderr)
        raise RuntimeError("Node checker failed")
    return json.loads(res.stdout)

if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "."
    out = run_checker(target)
    print(json.dumps(out, indent=2))
