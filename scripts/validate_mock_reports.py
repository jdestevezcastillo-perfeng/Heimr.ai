#!/usr/bin/env python3
"""
Validate that generated mock reports correctly identify injected failures.

This script:
1. Reads FAILURE_SCENARIOS.md to get expected failure patterns
2. Checks each scenario's reports (JMeter, k6, Gatling, Locust)
3. Validates that:
   - Reports detect the intended failure
   - Reports analyze all inputs (metrics, logs, traces)
   - Report findings match the scenario definition
"""

import json
import os
import re
from pathlib import Path
from typing import Dict, List, Tuple
import pandas as pd


# Define what patterns to look for based on scenario types
FAILURE_PATTERNS = {
    # API Failures
    "Latency Spike": ["latency", "p99", "p95", "slow", "response time"],
    "Error Spike": ["error", "5xx", "failure", "failed"],
    "Bimodal Latency": ["bimodal", "p99", "p50", "distribution", "percentile"],
    "Timeout": ["timeout", "timed out", "connection"],
    
    # Database
    "Query Timeout": ["timeout", "query", "database", "db"],
    "Deadlock": ["deadlock", "lock", "contention"],
    "Slow Query": ["slow", "query", "latency"],
    "Connection Pool": ["pool", "connection", "exhausted"],
    
    # Network
    "Packet Loss": ["packet", "loss", "network", "dropped"],
    "DNS": ["dns", "resolution", "lookup"],
    "SSL/TLS": ["ssl", "tls", "certificate", "handshake"],
    "Bandwidth": ["bandwidth", "throttle", "network"],
    
    # Resource
    "CPU": ["cpu", "processor", "utilization"],
    "Memory": ["memory", "oom", "heap", "leak"],
    "Disk": ["disk", "i/o", "storage"],
    "Thread": ["thread", "pool", "exhausted"],
    
    # Cache
    "Cache Miss": ["cache", "miss", "hit ratio"],
    "Cache Eviction": ["cache", "eviction", "expired"],
    "Cache Stampede": ["cache", "stampede", "thundering"],
    
    # Load Balancer
    "Uneven Distribution": ["load", "balance", "distribution", "uneven"],
    "Health Check": ["health", "check", "failure"],
    
    # Message Queue
    "Queue Backlog": ["queue", "backlog", "lag", "delay"],
    "Message Loss": ["message", "loss", "dropped"],
    
    # Service Mesh
    "Circuit Breaker": ["circuit", "breaker", "open"],
    "Retry Storm": ["retry", "storm", "backoff"],
    
    # General
    "GC Pause": ["gc", "garbage", "collection", "pause", "stop-the-world"],
    "Rate Limit": ["rate", "limit", "throttle", "429"],
}


def parse_failure_scenarios(scenarios_file: str) -> Dict[str, Dict]:
    """Parse FAILURE_SCENARIOS.md and extract scenario definitions."""
    scenarios = {}
    
    with open(scenarios_file, 'r') as f:
        content = f.read()
    
    # Find the table with scenario definitions
    # Format: | `SCENARIO-ID` | **Failure Name** | Description | Metrics | Causes |
    pattern = r'\|\s*`([A-Z]+-\d+)`\s*\|\s*\*\*([^*]+)\*\*\s*\|\s*([^|]+)\s*\|\s*([^|]+)\s*\|\s*([^|]+)\s*\|'
    
    for match in re.finditer(pattern, content):
        scenario_id = match.group(1).strip()
        failure_name = match.group(2).strip()
        description = match.group(3).strip()
        metrics = match.group(4).strip()
        causes = match.group(5).strip()
        
        scenarios[scenario_id] = {
            'name': failure_name,
            'description': description,
            'metrics': metrics,
            'causes': causes
        }
    
    return scenarios


def check_report_content(report_path: str, scenario_info: Dict, scenario_id: str) -> Dict:
    """Check if report correctly identifies the failure scenario."""
    
    if not os.path.exists(report_path):
        return {
            'exists': False,
            'failure_detected': False,
            'keywords_found': [],
            'has_metrics': False,
            'has_logs': False,
            'has_traces': False,
            'issues': ['Report file not found']
        }
    
    with open(report_path, 'r') as f:
        report_content = f.read().lower()
    
    # Check if report marked as FAILED or PASSED
    failure_detected = '# ❌ failed' in report_content or 'failed' in report_content[:500]
    passed_detected = '# ✅ passed' in report_content or 'passed' in report_content[:500]
    
    # Find relevant keywords based on failure type
    failure_name = scenario_info['name']
    keywords_found = []
    
    # Special case: Healthy Baseline should NOT be marked as failed
    is_healthy_baseline = 'healthy' in failure_name.lower() or 'baseline' in failure_name.lower()
    
    # Get expected patterns for this failure type
    for pattern_type, keywords in FAILURE_PATTERNS.items():
        if pattern_type.lower() in failure_name.lower():
            for keyword in keywords:
                if keyword in report_content:
                    keywords_found.append(keyword)
    
    # Also check for keywords from the scenario metrics/causes
    scenario_keywords = (scenario_info['metrics'] + ' ' + scenario_info['causes']).lower()
    for word in scenario_keywords.split():
        if len(word) > 3 and word in report_content:
            keywords_found.append(word)
    
    # Check if observability data was analyzed
    has_metrics = 'prometheus' in report_content or 'cpu' in report_content or 'memory' in report_content
    has_logs = 'log' in report_content or 'loki' in report_content
    has_traces = 'trace' in report_content or 'tempo' in report_content or 'span' in report_content
    
    # Identify issues based on scenario type
    issues = []
    
    if is_healthy_baseline:
        # For healthy baselines, we expect PASSED status
        if failure_detected:
            issues.append('Healthy baseline incorrectly marked as FAILED')
        # Don't require keywords for healthy baselines
        # Observability check is optional for baselines
    else:
        # For failure scenarios, we expect FAILED status
        if not failure_detected:
            issues.append('Report did not mark test as FAILED')
        if not keywords_found:
            issues.append(f'No relevant keywords found for {failure_name}')
        # Make observability a warning, not an error
        if not has_metrics and not has_logs and not has_traces:
            issues.append('No observability data analysis found')
    
    return {
        'exists': True,
        'failure_detected': failure_detected,
        'keywords_found': list(set(keywords_found)),
        'has_metrics': has_metrics,
        'has_logs': has_logs,
        'has_traces': has_traces,
        'issues': issues
    }


def validate_all_scenarios(data_dir: str, scenarios: Dict) -> pd.DataFrame:
    """Validate all scenario reports."""
    
    results = []
    formats = ['jmeter_results.csv', 'k6_results.json', 'simulation.log', 'locust_stats_history.csv']
    
    for scenario_id, scenario_info in sorted(scenarios.items()):
        scenario_path = Path(data_dir) / scenario_id
        
        if not scenario_path.exists():
            print(f"⚠️  Scenario {scenario_id} directory not found")
            continue
        
        for format_file in formats:
            report_path = scenario_path / f"{format_file}_report.md"
            
            validation = check_report_content(str(report_path), scenario_info, scenario_id)
            
            results.append({
                'scenario_id': scenario_id,
                'failure_name': scenario_info['name'],
                'format': format_file.split('_')[0] if '_' in format_file else format_file.split('.')[0],
                'report_exists': validation['exists'],
                'failure_detected': validation['failure_detected'],
                'keywords_found': len(validation['keywords_found']),
                'keywords': ', '.join(validation['keywords_found'][:5]),  # First 5
                'has_metrics': validation['has_metrics'],
                'has_logs': validation['has_logs'],
                'has_traces': validation['has_traces'],
                'issues': '; '.join(validation['issues']) if validation['issues'] else 'None',
                'status': '✅ PASS' if not validation['issues'] else '⚠️  ISSUES'
            })
    
    return pd.DataFrame(results)


def dataframe_to_markdown(df: pd.DataFrame) -> str:
    """Convert DataFrame to markdown table manually."""
    # Get column names
    cols = df.columns.tolist()
    
    # Build header
    header = "| " + " | ".join(str(c) for c in cols) + " |"
    separator = "| " + " | ".join(["-" * max(8, len(str(c))) for c in cols]) + " |"
    
    # Build rows
    rows = []
    for _, row in df.iterrows():
        row_str = "| " + " | ".join(str(v) for v in row.values) + " |"
        rows.append(row_str)
    
    return "\n".join([header, separator] + rows)


def generate_summary_report(df: pd.DataFrame, output_file: str):
    """Generate a summary validation report."""
    
    total_reports = len(df)
    passed = len(df[df['status'] == '✅ PASS'])
    failed = total_reports - passed
    
    # Group by scenario
    scenario_summary = df.groupby('scenario_id').agg({
        'failure_detected': 'sum',
        'report_exists': 'sum',
        'status': lambda x: '✅ ALL PASS' if all(s == '✅ PASS' for s in x) else '⚠️  SOME ISSUES'
    }).reset_index()
    
    # Group by format
    format_summary = df.groupby('format').agg({
        'failure_detected': 'sum',
        'report_exists': 'sum',
        'status': lambda x: sum(s == '✅ PASS' for s in x)
    }).reset_index()
    format_summary.columns = ['format', 'failures_detected', 'reports_exist', 'passed_count']
    
    with open(output_file, 'w') as f:
        f.write("# Mock Data Validation Report\n\n")
        f.write(f"**Generated**: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        f.write("## Overall Summary\n\n")
        f.write(f"- **Total Reports Validated**: {total_reports}\n")
        f.write(f"- **✅ Passed**: {passed} ({passed/total_reports*100:.1f}%)\n")
        f.write(f"- **⚠️  Issues Found**: {failed} ({failed/total_reports*100:.1f}%)\n\n")
        
        f.write("## Summary by Format\n\n")
        f.write(dataframe_to_markdown(format_summary))
        f.write("\n\n")
        
        f.write("## Summary by Scenario\n\n")
        f.write(f"- **Total Scenarios**: {len(scenario_summary)}\n")
        f.write(f"- **All Reports Pass**: {len(scenario_summary[scenario_summary['status'] == '✅ ALL PASS'])}\n")
        f.write(f"- **Some Issues**: {len(scenario_summary[scenario_summary['status'] == '⚠️  SOME ISSUES'])}\n\n")
        
        # Show scenarios with issues
        issues_df = df[df['status'] == '⚠️  ISSUES'][['scenario_id', 'failure_name', 'format', 'issues']]
        if len(issues_df) > 0:
            f.write("## Reports with Issues\n\n")
            f.write(dataframe_to_markdown(issues_df))
            f.write("\n\n")
        
        f.write("## Detailed Results\n\n")
        f.write(dataframe_to_markdown(df))
    
    print(f"\n📊 Summary report written to: {output_file}")


def main():
    # Paths
    base_dir = Path(__file__).parent.parent
    scenarios_file = base_dir / "FAILURE_SCENARIOS.md"
    data_dir = base_dir / "data" / "mocks"
    output_file = base_dir / "data" / "mocks" / "validation_report.md"
    
    print("🔍 Validating Mock Data Reports\n")
    print(f"Reading scenarios from: {scenarios_file}")
    
    # Parse scenarios
    scenarios = parse_failure_scenarios(str(scenarios_file))
    print(f"Found {len(scenarios)} scenarios\n")
    
    # Validate all reports
    print("Validating reports...")
    results_df = validate_all_scenarios(str(data_dir), scenarios)
    
    # Generate summary
    generate_summary_report(results_df, str(output_file))
    
    # Print summary to console
    total = len(results_df)
    passed = len(results_df[results_df['status'] == '✅ PASS'])
    
    print(f"\n{'='*60}")
    print(f"VALIDATION COMPLETE")
    print(f"{'='*60}")
    print(f"✅ Passed: {passed}/{total} ({passed/total*100:.1f}%)")
    print(f"⚠️  Issues: {total-passed}/{total} ({(total-passed)/total*100:.1f}%)")
    print(f"\nDetailed report: {output_file}")
    
    # Show some example issues
    issues_df = results_df[results_df['status'] == '⚠️  ISSUES'].head(5)
    if len(issues_df) > 0:
        print(f"\nExample issues found:")
        for _, row in issues_df.iterrows():
            print(f"  - {row['scenario_id']} ({row['format']}): {row['issues']}")


if __name__ == "__main__":
    main()
