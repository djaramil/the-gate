#!/bin/bash

# Script to monitor batch evaluation progress with auto-refresh

TOTAL_REPOS=40

while true; do
    clear
    echo "=== Batch Evaluation Progress Monitor ==="
    echo ""

    # Check if process is running
    echo "📊 Process Status:"
    if pgrep -f "hc_evaluate.py evaluate-latest" > /dev/null; then
        echo "  ✓ Evaluation process is running"
        PID=$(pgrep -f "hc_evaluate.py evaluate-latest")
        echo "  Process ID: $PID"
        echo "  Runtime: $(ps -p $PID -o etime= | tr -d ' ')"
        
        # Try to get current repo from status file
        echo ""
        echo "📦 Current Activity:"
        STATUS_FILE="results/.evaluation_status"
        if [ -f "$STATUS_FILE" ]; then
            STATUS=$(cat "$STATUS_FILE")
            IFS='|' read -r PROGRESS REPO_NAME PERCENT <<< "$STATUS"
            echo "  [$PROGRESS] $REPO_NAME ($PERCENT)"
        else
            echo "  (Status file not found - first repo starting...)"
        fi
    else
        echo "  ✗ Evaluation process is not running"
        echo ""
        echo "Evaluation has completed or was stopped."
        echo "Showing final results..."
    fi

    echo ""

    # Check if results file exists
    RESULTS_FILE="results/evaluation_results.json"
    if [ -f "$RESULTS_FILE" ]; then
        echo "📁 Results File: $RESULTS_FILE"
        echo "  Size: $(du -h $RESULTS_FILE | cut -f1)"
        echo "  Last modified: $(stat -f "%Sm" -t "%Y-%m-%d %H:%M:%S" $RESULTS_FILE)"
        
        # Count repos in results
        REPO_COUNT=$(python3 -c "import json; f=open('$RESULTS_FILE'); r=json.load(f); print(len(r))" 2>/dev/null || echo "0")
        PERCENT=$(echo "scale=1; $REPO_COUNT * 100 / $TOTAL_REPOS" | bc)
        echo ""
        echo "📈 Progress: $REPO_COUNT / $TOTAL_REPOS ($PERCENT%)"
        
        # Show pass/fail summary
        PASS_COUNT=$(python3 -c "import json; f=open('$RESULTS_FILE'); r=json.load(f); print(sum(1 for x in r if x.get('gate_pass', False)))" 2>/dev/null || echo "0")
        FAIL_COUNT=$((REPO_COUNT - PASS_COUNT))
        echo "  Results: $PASS_COUNT ✓ PASS, $FAIL_COUNT ✗ FAIL"
        
        # Show recent results
        echo ""
        echo "📋 Recent Results (last 5):"
        echo "  ------------------------"
        python3 -c "
import json
try:
    with open('$RESULTS_FILE', 'r') as f:
        results = json.load(f)
    
    for result in results[-5:]:
        repo_name = result.get('repo_name', 'Unknown')
        gate_pass = '✓ PASS' if result.get('gate_pass', False) else '✗ FAIL'
        total_time = result.get('timing', {}).get('total', 'N/A')
        print(f'  {repo_name}: {gate_pass} ({total_time})')
except Exception as e:
    print(f'  Error reading results: {e}')
"
    else
        echo "📁 Results file not found yet"
        echo "  Progress: 0 / $TOTAL_REPOS (0.0%)"
        echo "  (Normal - first repo still processing)"
    fi

    echo ""
    echo "================================"
    
    # Exit if process is not running
    if ! pgrep -f "hc_evaluate.py evaluate-latest" > /dev/null; then
        echo ""
        echo "✓ Evaluation process has completed."
        echo "Monitoring complete."
        exit 0
    fi
    
    echo "⏱️  Next check in 10 seconds..."
    
    sleep 10
done
