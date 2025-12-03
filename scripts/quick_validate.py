#!/usr/bin/env python3
"""
Quick validation of anomaly detection across all scenarios (no LLM).
"""
import os
import sys
import subprocess
from concurrent.futures import ThreadPoolExecutor

MOCKS_DIR = "data/mocks"
HEIMR_CMD = [sys.executable, "-m", "heimr.cli", "analyze"]

def validate_scenario(scenario_dir):
    """Validate a single scenario without LLM."""
    scenario = os.path.basename(scenario_dir)
    
    # Find load test file
    for filename in ['jmeter_results.csv', 'k6_results.json', 'locust_stats_history.csv']:
        filepath = os.path.join(scenario_dir, filename)
        if os.path.exists(filepath):
            break
    else:
        return (scenario, 'SKIP', 'No load test file found')
    
    # Build command (no --explain, just analysis)
    cmd = HEIMR_CMD + [filepath]
    
    # Add observability files
    prom_file = os.path.join(scenario_dir, "prometheus_metrics.json")
    if os.path.exists(prom_file):
        cmd.extend(["--prometheus-file", prom_file])
    
    loki_file = os.path.join(scenario_dir, "loki_logs.json")
    if os.path.exists(loki_file):
        cmd.extend(["--loki-file", loki_file])
    
    tempo_file = os.path.join(scenario_dir, "tempo_traces.json")
    if os.path.exists(tempo_file):
        cmd.extend(["--tempo-file", tempo_file])
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        
        # Extract status from output
        if '# ✅ PASSED' in result.stdout:
            status = 'PASS'
            reason = 'No anomalies'
        elif '# ❌ FAILED' in result.stdout:
            status = 'FAIL'
            # Extract reason
            for line in result.stdout.split('\n'):
                if '**Reasons**:' in line:
                    reason = line.split('**Reasons**: ')[1].strip()
                    break
            else:
                reason = 'Unknown'
        else:
            status = 'ERROR'
            reason = 'No status found'
        
        return (scenario, status, reason)
        
    except subprocess.TimeoutExpired:
        return (scenario, 'TIMEOUT', 'Command timed out')
    except Exception as e:
        return (scenario, 'ERROR', str(e))

def main():
    # Find all scenario directories
    scenarios = []
    for entry in sorted(os.listdir(MOCKS_DIR)):
        scenario_path = os.path.join(MOCKS_DIR, entry)
        if os.path.isdir(scenario_path):
            scenarios.append(scenario_path)
    
    print(f"Validating {len(scenarios)} scenarios (no LLM)...")
    print("=" * 80)
    
    # Run in parallel
    with ThreadPoolExecutor(max_workers=8) as executor:
        results = list(executor.map(validate_scenario, scenarios))
    
    # Categorize results
    passed = []
    failed = []
    errors = []
    
    for scenario, status, reason in results:
        if status == 'PASS':
            passed.append((scenario, reason))
        elif status == 'FAIL':
            failed.append((scenario, reason))
        else:
            errors.append((scenario, status, reason))
    
    # Print results
    print("\n" + "=" * 80)
    print("RESULTS")
    print("=" * 80)
    
    # Expected: API-001 should PASS, all others should FAIL
    correct = []
    incorrect = []
    
    for scenario, reason in passed:
        if scenario == 'API-001':
            correct.append(f"✓ {scenario}: PASS (correct)")
            print(f"✓ {scenario:15} | PASS | {reason}")
        else:
            incorrect.append(f"✗ {scenario}: PASS (should FAIL)")
            print(f"✗ {scenario:15} | PASS | {reason} (SHOULD FAIL)")
    
    for scenario, reason in failed:
        if scenario == 'API-001':
            incorrect.append(f"✗ {scenario}: FAIL (should PASS)")
            print(f"✗ {scenario:15} | FAIL | {reason} (SHOULD PASS)")
        else:
            correct.append(f"✓ {scenario}: FAIL (correct)")
            print(f"✓ {scenario:15} | FAIL | {reason}")
    
    for scenario, status, reason in errors:
        print(f"? {scenario:15} | {status} | {reason}")
    
    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Total: {len(results)}")
    print(f"✓ Correct: {len(correct)}")
    print(f"✗ Incorrect: {len(incorrect)}")
    print(f"? Errors: {len(errors)}")
    
    if incorrect:
        print("\nIncorrect detections:")
        for item in incorrect:
            print(f"  {item}")
    
    print("=" * 80)
    
    # Exit code
    sys.exit(0 if len(incorrect) == 0 else 1)

if __name__ == "__main__":
    main()
