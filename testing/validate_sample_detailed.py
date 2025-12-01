
import pandas as pd
import json
import sys
import numpy as np

def validate_parquet(file_path):
    print(f"Validating {file_path}...")
    try:
        df = pd.read_parquet(file_path)
    except Exception as e:
        print(f"Error reading parquet file: {e}")
        return

    print(f"Shape: {df.shape}")
    print(f"Columns: {list(df.columns)}")

    # Check for required columns
    required_columns = ['timestamp', 'scenario_id', 'label', 'log_total_count', 'trace_count']
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        print(f"[ERROR] Missing columns: {missing_columns}")
    else:
        print("[PASS] All basic required columns present.")

    # Check metrics
    metric_cols = [c for c in df.columns if 'http_requests_total' in c or 'request_rate' in c]
    if metric_cols:
        print(f"[PASS] Found {len(metric_cols)} metric columns.")
        # Check for non-zero values in metrics
        non_zero_metrics = 0
        for col in metric_cols:
            if df[col].sum() > 0:
                non_zero_metrics += 1
        print(f"      {non_zero_metrics} metric columns have non-zero values.")
    else:
        print("[WARNING] No obvious metric columns found (checked 'http_requests_total', 'request_rate').")

    # Check logs
    if 'log_total_count' in df.columns:
        total_logs = df['log_total_count'].sum()
        print(f"Total Logs: {total_logs}")
        if total_logs > 0:
            print("[PASS] Logs are present.")
        else:
            print("[WARNING] Log count is 0.")
            
    if 'log_context' in df.columns:
        # Check if log_context contains strings or lists
        sample = df['log_context'].iloc[0]
        print(f"Log Context Sample Type: {type(sample)}")
        if isinstance(sample, (list, np.ndarray)):
             print(f"Log Context Sample Length: {len(sample)}")
        elif isinstance(sample, str):
             print(f"Log Context Sample (First 50 chars): {sample[:50]}...")

    # Check traces
    if 'trace_count' in df.columns:
        total_traces = df['trace_count'].sum()
        print(f"Total Traces: {total_traces}")
        if total_traces > 0:
            print("[PASS] Traces are present.")
        else:
            print("[WARNING] Trace count is 0.")

    if 'trace_error_rate' in df.columns:
        avg_error_rate = df['trace_error_rate'].mean()
        print(f"Average Trace Error Rate: {avg_error_rate}")

    if 'trace_slowest_json' in df.columns:
        sample_json = df['trace_slowest_json'].iloc[0]
        if sample_json and sample_json != "{}":
             print("[PASS] trace_slowest_json is populated.")
        else:
             print("[WARNING] trace_slowest_json is empty.")

    if 'trace_error_json' in df.columns:
        sample_json = df['trace_error_json'].iloc[0]
        if sample_json and sample_json != "{}":
             print("[PASS] trace_error_json is populated.")
        else:
             print("[INFO] trace_error_json is empty (Expected for healthy scenarios).")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python validate_sample_detailed.py <parquet_file>")
        sys.exit(1)
    
    validate_parquet(sys.argv[1])
