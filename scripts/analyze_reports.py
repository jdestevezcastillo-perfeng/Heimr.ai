# Copyright (c) 2025 Juan Estevez Castillo
# Licensed under AGPL v3. Commercial licenses available.
# See LICENSE or https://www.gnu.org/licenses/agpl-3.0.html

#!/usr/bin/env python3
"""
Analyze generated Heimr reports to validate correctness.
Cross-references with FAILURE_SCENARIOS.md to check if failures are detected.
"""
import os
import re
import json

MOCKS_DIR = "data/mocks"
SCENARIOS_FILE = "FAILURE_SCENARIOS.md"

def parse_scenarios():
    """Parse FAILURE_SCENARIOS.md to get expected behavior."""
    scenarios = {}
    with open(SCENARIOS_FILE, 'r') as f:
        lines = f.readlines()
    
    row_pattern = re.compile(r'\|\s*`([^`]+)`\s*\|\s*\*\*([^*]+)\*\*\s*\|')
    
    for line in lines:
        match = row_pattern.search(line)
        if match:
            sid = match.group(1).strip()
            name = match.group(2).strip()
            # API-001 is "Healthy Baseline" - should PASS
            # All others are failures - should FAIL
            should_pass = (sid == "API-001")
            scenarios[sid] = {
                'name': name,
                'should_pass': should_pass
            }
    
    return scenarios

def analyze_report(report_path):
    """Analyze a single report file."""
    if not os.path.exists(report_path):
        return None
    
    with open(report_path, 'r') as f:
        content = f.read()
    
    # Check if passed or failed
    if '# ✅ PASSED' in content:
        detected_as = 'PASS'
        anomaly_count = 0
    elif '# ❌ FAILED' in content:
        detected_as = 'FAIL'
        # Extract anomaly count
        match = re.search(r'Anomalies: (\d+)', content)
        anomaly_count = int(match.group(1)) if match else 0
    else:
        detected_as = 'UNKNOWN'
        anomaly_count = 0
    
    return {
        'detected_as': detected_as,
        'anomaly_count': anomaly_count
    }

def main():
    scenarios = parse_scenarios()
    
    results = {
        'correct': [],
        'incorrect': [],
        'missing': []
    }
    
    print("="*80)
    print("HEIMR REPORT VALIDATION")
    print("="*80)
    print()
    
    for sid, info in sorted(scenarios.items()):
        scenario_dir = os.path.join(MOCKS_DIR, sid)
        if not os.path.exists(scenario_dir):
            continue
        
        # Check JMeter report (representative)
        report_path = os.path.join(scenario_dir, "jmeter_results.csv_report.md")
        analysis = analyze_report(report_path)
        
        if analysis is None:
            results['missing'].append(sid)
            continue
        
        expected = 'PASS' if info['should_pass'] else 'FAIL'
        actual = analysis['detected_as']
        is_correct = (expected == actual)
        
        status_icon = "✓" if is_correct else "✗"
        
        if is_correct:
            results['correct'].append(sid)
        else:
            results['incorrect'].append({
                'sid': sid,
                'name': info['name'],
                'expected': expected,
                'actual': actual,
                'anomalies': analysis['anomaly_count']
            })
        
        print(f"[{status_icon}] {sid:12} | Expected: {expected:4} | Actual: {actual:7} | Anomalies: {analysis['anomaly_count']:2} | {info['name']}")
    
    print()
    print("="*80)
    print("SUMMARY")
    print("="*80)
    print(f"Total Scenarios: {len(scenarios)}")
    print(f"✓ Correct: {len(results['correct'])}")
    print(f"✗ Incorrect: {len(results['incorrect'])}")
    print(f"? Missing Reports: {len(results['missing'])}")
    
    if results['incorrect']:
        print()
        print("INCORRECT DETECTIONS:")
        print("-"*80)
        for item in results['incorrect']:
            print(f"  {item['sid']}: {item['name']}")
            print(f"    Expected {item['expected']} but got {item['actual']} ({item['anomalies']} anomalies)")
    
    print("="*80)

if __name__ == "__main__":
    main()
