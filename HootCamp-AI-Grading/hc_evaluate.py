import argparse, json
from pathlib import Path
import hc_check_js_ts as checker

def evaluate_local(path):
    print("Running static JS/TS checks on", path)
    res = checker.run_checker(path)
    print(json.dumps(res, indent=2))

def main():
    p = argparse.ArgumentParser()
    p.add_argument("cmd", choices=["evaluate-local","dry-run"])
    p.add_argument("--path", default="submissions")
    args = p.parse_args()
    if args.cmd == "evaluate-local":
        evaluate_local(args.path)
    else:
        print("Dry run: would evaluate", args.path)

if __name__=="__main__":
    main()
