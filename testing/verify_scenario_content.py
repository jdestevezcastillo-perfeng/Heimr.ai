
import pandas as pd
import json
import sys
import glob
import os
import ast

def inspect_scenario(file_pattern, scenario_id):
    files = glob.glob(file_pattern)
    if not files:
        print(f"[{scenario_id}] No files found for pattern {file_pattern}")
        return
    
    # Get latest file
    latest_file = max(files, key=os.path.getctime)
    print(f"\n=== Analyzing {scenario_id} from {os.path.basename(latest_file)} ===")
    
    try:
        df = pd.read_parquet(latest_file)
    except Exception as e:
        print(f"Error reading file: {e}")
        return

    # 1. Trace Duration (for Latency scenarios)
    if 'trace_slowest_json' in df.columns:
        durations = []
        for _, row in df.iterrows():
            trace_json = row['trace_slowest_json']
            if trace_json and len(trace_json) > 2: # Check for non-empty, non-"{}"
                try:
                    trace = json.loads(trace_json)
                    # OTLP format: batches -> scopeSpans -> spans
                    spans = []
                    for batch in trace.get("batches", []):
                        for scope_span in batch.get("scopeSpans", []):
                            spans.extend(scope_span.get("spans", []))
                    
                    if spans:
                        # Find root span (usually the one with no parentSpanId, or just take the longest/first)
                        # For simplicity, let's take the max duration found in the trace
                        max_duration = 0
                        for span in spans:
                            start = int(span.get("startTimeUnixNano", 0))
                            end = int(span.get("endTimeUnixNano", 0))
                            duration_ms = (end - start) / 1e6
                            if duration_ms > max_duration:
                                max_duration = duration_ms
                        durations.append(max_duration)
                except Exception as e:
                    # print(f"Trace parsing error: {e}") 
                    pass
        
        if durations:
            print(f"Trace Durations (ms): Max={max(durations):.2f}, Avg={sum(durations)/len(durations):.2f}")
        else:
            print("No valid trace durations found.")
            if len(df) > 0:
                 print(f"Sample Trace JSON (Row 0): {df['trace_slowest_json'].iloc[0][:100]}")

    # 2. Log Status Codes (for Error scenarios)
    status_counts = {}
    if 'log_context' in df.columns:
        for _, row in df.iterrows():
            logs_str = row['log_context']
            if logs_str and len(logs_str) > 2:
                try:
                    logs = ast.literal_eval(logs_str)
                    for log in logs:
                        # Simple heuristic for status codes
                        if " 200 " in log: key = "200"
                        elif " 500 " in log: key = "500"
                        elif " 503 " in log: key = "503"
                        elif " 404 " in log: key = "404"
                        elif " 429 " in log: key = "429"
                        else: key = "other"
                        status_counts[key] = status_counts.get(key, 0) + 1
                except:
                    pass
    print(f"Log Status Codes: {status_counts}")

    # 3. Memory Metrics (for Memory scenarios)
    # Look for go_memstats_alloc_bytes
    mem_cols = [c for c in df.columns if 'go_memstats_alloc_bytes' in c]
    if mem_cols:
        print(f"Found {len(mem_cols)} memory metric columns.")
        # Check trend
        for col in mem_cols[:3]: # Check first few
            try:
                start_val = df[col].iloc[0]
                end_val = df[col].iloc[-1]
                diff = end_val - start_val
                print(f"Metric {col[-50:]}: Start={start_val:.0f}, End={end_val:.0f}, Diff={diff:.0f}")
            except:
                pass
    else:
        print("No specific memory columns found. Searching for any 'bytes' columns:")
        bytes_cols = [c for c in df.columns if 'bytes' in c]
        print(bytes_cols[:10]) # Print first 10 matches

if __name__ == "__main__":
    inspect_scenario("data/training_data/*API-002*.parquet", "API-002 (Latency)")
    inspect_scenario("data/training_data/*API-003*.parquet", "API-003 (Memory)")
    inspect_scenario("data/training_data/*API-004*.parquet", "API-004 (Error)")
