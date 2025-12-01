import pandas as pd
import sys
import json
import numpy as np

def inspect_content(file_path):
    try:
        df = pd.read_parquet(file_path)
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return

    print(f"--- Inspecting {file_path} ---")
    if df.empty:
        print("File is empty.")
        return

    # General Info
    scenario = df['scenario_id'].iloc[0] if 'scenario_id' in df.columns else "Unknown"
    print(f"Scenario: {scenario}")
    
    # Metrics Analysis
    if 'trace_p95_duration_ms' in df.columns:
        p95_mean = df['trace_p95_duration_ms'].mean()
        p95_max = df['trace_p95_duration_ms'].max()
        print(f"Trace p95 Duration (ms) - Mean: {p95_mean:.2f}, Max: {p95_max:.2f}")

    # Log Content
    print("\n[Logs Analysis]")
    if 'log_error_samples' in df.columns:
        # Flatten list of lists and get unique non-empty samples
        all_samples = []
        for samples in df['log_error_samples']:
            if isinstance(samples, (list, np.ndarray)):
                 all_samples.extend(samples)
        
        unique_samples = list(set(all_samples))
        if unique_samples:
            print(f"Found {len(unique_samples)} unique error log samples. Showing top 5:")
            for i, sample in enumerate(unique_samples[:5]):
                print(f"  {i+1}. {sample}")
        else:
            print("No error log samples found.")
    
    if 'log_context' in df.columns:
        # Search for application specific keywords
        keywords = ["uvicorn", "fastapi", "sim-service", "python"]
        found_app_logs = []
        
        for samples in df['log_context']:
            for log in samples:
                if any(k in log.lower() for k in keywords):
                    found_app_logs.append(log)
                    if len(found_app_logs) >= 5: break
            if len(found_app_logs) >= 5: break
            
        if found_app_logs:
            print(f"\n[Application Logs Found] (keywords: {keywords})")
            for log in found_app_logs:
                print(f"  - {log}")
        else:
            print(f"\n[Application Logs] No logs found containing keywords: {keywords}")

        # Just grab some random non-empty contexts
        contexts = df[df['log_context'].apply(lambda x: len(x) > 0)]['log_context'].head(3)
        if not contexts.empty:
             print("\nSample Log Contexts:")
             for ctx in contexts:
                 print(f"  - {ctx}")

    # Trace Content
    print("\n[Trace Analysis]")
    if 'trace_slowest_json' in df.columns:
        # Find the row with the highest trace_max_duration_ms
        if 'trace_max_duration_ms' in df.columns:
            slowest_row = df.loc[df['trace_max_duration_ms'].idxmax()]
            print(f"Slowest Trace Duration: {slowest_row['trace_max_duration_ms']} ms")
            slow_json = slowest_row['trace_slowest_json']
            if slow_json:
                # It might be a string or dict depending on how it was saved
                if isinstance(slow_json, str):
                    try:
                        slow_json = json.loads(slow_json)
                    except:
                        pass
                print(f"Slowest Trace Structure (truncated): {str(slow_json)[:500]}...")
    
    if 'trace_error_json' in df.columns:
        error_rows = df[df['trace_error_rate'] > 0]
        if not error_rows.empty:
            print(f"Found {len(error_rows)} rows with trace errors.")
            sample_error = error_rows.iloc[0]['trace_error_json']
            print(f"Sample Trace Error: {sample_error}")
        else:
            print("No trace errors found.")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 inspect_content.py <parquet_file>")
        sys.exit(1)
    
    inspect_content(sys.argv[1])
