# Copyright (c) 2025 Juan Estevez Castillo
# Licensed under AGPL v3. Commercial licenses available.
# See LICENSE or https://www.gnu.org/licenses/agpl-3.0.html

#!/usr/bin/env python3
"""
Regenerate reports for a sample of scenarios to test the fixes.

This script regenerates reports for 10 diverse scenarios across different
failure types to validate that the multi-signal detection is working correctly.
"""

import os
import subprocess
from pathlib import Path

# Sample scenarios covering different failure types
SAMPLE_SCENARIOS = [
    "API-001",  # Healthy Baseline (should PASS)
    "API-002",  # Latency Spike (Tail)
    "API-004",  # Error Spike (5xx)
    "API-006",  # Bimodal Latency
    "API-007",  # Memory Leak
    "DB-001",   # Slow Query
    "CSH-001",  # Cache Stampede
    "NET-004",  # TCP Retransmission
    "INF-001",  # OOMKill
    "MSG-001",  # Consumer Lag
]

def main():
    base_dir = Path(__file__).parent.parent
    data_dir = base_dir / "data" / "mocks"
    
    # Check if model is available
    print("🔍 Checking if Ministral model is available...")
    result = subprocess.run(
        ["ollama", "list"],
        capture_output=True,
        text=True
    )
    
    if "ministral" not in result.stdout.lower():
        print("⚠️  Ministral model not found. Trying to pull it...")
        print("   This may take a few minutes...")
        subprocess.run(["ollama", "pull", "nchapman/ministral-8b-instruct-2410:8b"])
    
    print(f"\\n🔄 Regenerating reports for {len(SAMPLE_SCENARIOS)} sample scenarios\\n")
    
    total = len(SAMPLE_SCENARIOS) * 4  # 4 formats per scenario
    current = 0
    
    for scenario_id in SAMPLE_SCENARIOS:
        scenario_dir = data_dir / scenario_id
        
        if not scenario_dir.exists():
            print(f"⚠️  Scenario {scenario_id} not found, skipping...")
            continue
        
        print(f"\\n📝 Processing {scenario_id}...")
        
        # Define file formats and their paths
        formats = [
            ("jmeter_results.csv", "jtl"),
            ("k6_results.json", "k6"),
            ("simulation.log", "gatling"),
            ("locust_stats_history.csv", "locust")
        ]
        
        for data_file, format_type in formats:
            current += 1
            data_path = scenario_dir / data_file
            report_path = scenario_dir / f"{data_file}_report.md"
            
            if not data_path.exists():
                print(f"  ⚠️  Skipping {data_file} (not found)")
                continue
            
            # Build command - try Ministral first, fall back to llama3.1
            # Use venv python if available
            python_cmd = str(base_dir / ".venv" / "bin" / "python3")
            if not Path(python_cmd).exists():
                python_cmd = "python3"
            
            cmd = [
                python_cmd, "-m", "heimr.cli",
                "analyze",
                str(data_path),
                "--format", format_type,
                "--output", str(report_path),
                "--explain",
                "--prometheus-file", str(scenario_dir / "prometheus_metrics.json"),
                "--loki-file", str(scenario_dir / "loki_logs.json"),
                "--tempo-file", str(scenario_dir / "tempo_traces.json"),
                "--llm-url", "http://localhost:11434/v1",
                "--llm-model", "nchapman/ministral-8b-instruct-2410:8b"
            ]
            
            try:
                print(f"  [{current}/{total}] Generating {format_type} report with Ministral...", end=" ", flush=True)
                result = subprocess.run(
                    cmd,
                    cwd=str(base_dir),
                    capture_output=True,
                    text=True,
                    timeout=120
                )
                
                if result.returncode == 0:
                    print("✅")
                else:
                    # Try fallback to llama3.1
                    print("⚠️  Trying llama3.1...", end=" ", flush=True)
                    cmd[-1] = "llama3.1:8b"
                    result = subprocess.run(
                        cmd,
                        cwd=str(base_dir),
                        capture_output=True,
                        text=True,
                        timeout=120
                    )
                    if result.returncode == 0:
                        print("✅")
                    else:
                        print(f"❌ Error: {result.stderr[:100]}")
                    
            except subprocess.TimeoutExpired:
                print("⏱️  Timeout (skipping)")
            except Exception as e:
                print(f"❌ Exception: {str(e)[:100]}")
    
    print(f"\\n{'='*60}")
    print(f"✅ Sample report regeneration complete!")
    print(f"{'='*60}")
    print(f"\\nNext step: Run validation to check improvements:")
    print(f"  python3 scripts/validate_mock_reports.py")
    print(f"\\nTo check a specific report:")
    print(f"  head -n 20 data/mocks/API-004/jmeter_results.csv_report.md")

if __name__ == "__main__":
    main()
