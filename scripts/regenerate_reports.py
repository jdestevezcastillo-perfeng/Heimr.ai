# Copyright (c) 2025 Juan Estevez Castillo
# Licensed under AGPL v3. Commercial licenses available.
# See LICENSE or https://www.gnu.org/licenses/agpl-3.0.html

#!/usr/bin/env python3
"""
Regenerate all mock data reports using the fixed CLI.

This script:
1. Finds all mock data scenarios
2. For each scenario, runs heimr analyze on all 4 formats
3. Generates reports with the fixed multi-signal failure detection
"""

import os
import subprocess
from pathlib import Path

def main():
    base_dir = Path(__file__).parent.parent
    data_dir = base_dir / "data" / "mocks"
    
    # Get all scenario directories
    scenarios = sorted([d for d in data_dir.iterdir() if d.is_dir()])
    
    print(f"🔄 Regenerating reports for {len(scenarios)} scenarios\\n")
    
    total = len(scenarios) * 4  # 4 formats per scenario
    current = 0
    
    for scenario_dir in scenarios:
        scenario_id = scenario_dir.name
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
            
            # Build command
            cmd = [
                "python3", "-m", "heimr.cli",
                "analyze",
                str(data_path),
                "--format", format_type,
                "--output", str(report_path),
                "--explain",
                "--prometheus-file", str(scenario_dir / "prometheus_metrics.json"),
                "--loki-file", str(scenario_dir / "loki_logs.json"),
                "--tempo-file", str(scenario_dir / "tempo_traces.json"),
                "--llm-url", "http://localhost:11434/v1",
                "--llm-model", "llama3.1:8b"
            ]
            
            try:
                print(f"  [{current}/{total}] Generating {format_type} report...", end=" ", flush=True)
                result = subprocess.run(
                    cmd,
                    cwd=str(base_dir),
                    capture_output=True,
                    text=True,
                    timeout=60
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
    print(f"✅ Report regeneration complete!")
    print(f"{'='*60}")
    print(f"\\nNext step: Run validation to check improvements:")
    print(f"  python3 scripts/validate_mock_reports.py")

if __name__ == "__main__":
    main()
