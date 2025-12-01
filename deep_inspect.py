import pandas as pd
import sys
import json
import numpy as np

def deep_inspect(file_path):
    print(f"Deep Inspecting {file_path}...")
    try:
        df = pd.read_parquet(file_path)
    except Exception as e:
        print(f"Failed to read parquet file: {e}")
        return

    # 1. LOGS DEEP DIVE
    print("\n=== LOGS DEEP DIVE ===")
    
    # Keywords relevant to CDC-002 (Debezium Memory Fail)
    keywords = ['memory', 'oom', 'heap', 'alloc', 'debezium', 'error', 'exception', 'fail']
    
    found_logs = []
    
    # Check log_context (list of strings)
    if 'log_context' in df.columns:
        print(f"\nScanning {len(df)} rows of log_context...")
        all_logs = []
        import ast
        for logs in df['log_context']:
            if logs is not None:
                if isinstance(logs, str):
                    try:
                        logs = ast.literal_eval(logs)
                    except:
                        pass
                if isinstance(logs, (list, np.ndarray)):
                     all_logs.extend(list(logs))
        
        print(f"\nTotal Log Entries Found: {len(all_logs)}")
        if len(all_logs) > 0:
            print("--- First 5 Log Entries ---")
            for i, log in enumerate(all_logs[:5]):
                print(f"[{i}] {log}")
            print("---------------------------")

        for idx, row in df.iterrows():
            logs = row['log_context']
            if isinstance(logs, (list, np.ndarray)):
                for log_entry in logs:
                    if not isinstance(log_entry, str): continue
                    
                    lower_log = log_entry.lower()
                    if any(k in lower_log for k in keywords):
                        found_logs.append(log_entry)
    
    # Check log_error_samples (list of strings)
    if 'log_error_samples' in df.columns:
        print(f"Scanning {len(df)} rows of log_error_samples...")
        for idx, row in df.iterrows():
            logs = row['log_error_samples']
            if isinstance(logs, (list, np.ndarray)):
                for log_entry in logs:
                    if not isinstance(log_entry, str): continue
                    found_logs.append(f"[ERROR_SAMPLE] {log_entry}")

    if found_logs:
        print(f"\nFound {len(found_logs)} relevant log entries. Showing top 10:")
        for i, log in enumerate(found_logs[:10]):
            print(f"  {i+1}. {log}")
    else:
        print("\n[WARNING] No logs found containing keywords: " + ", ".join(keywords))
        # Print a few random logs just to see what IS there
        if 'log_context' in df.columns:
             print("\nRandom log samples (to verify content exists):")
             sample_row = df.iloc[0]
             if isinstance(sample_row['log_context'], (list, np.ndarray)) and len(sample_row['log_context']) > 0:
                 for i, l in enumerate(sample_row['log_context'][:3]):
                     print(f"  - {l}")

    # 2. TRACES DEEP DIVE
    print("\n=== TRACES DEEP DIVE ===")
    trace_issues = []
    
    # Check trace_slowest_json
    if 'trace_slowest_json' in df.columns:
        for idx, row in df.iterrows():
            raw_json = row['trace_slowest_json']
            if not raw_json: continue
            
            try:
                if isinstance(raw_json, str):
                    trace_data = json.loads(raw_json)
                else:
                    trace_data = raw_json
                
                # Navigate OTLP structure: batches -> scopeSpans -> spans
                if isinstance(trace_data, dict) and 'batches' in trace_data:
                    for batch in trace_data['batches']:
                        if 'scopeSpans' in batch:
                            for scope_span in batch['scopeSpans']:
                                if 'spans' in scope_span:
                                    for span in scope_span['spans']:
                                        # Check for error status (code 2 = Error)
                                        status = span.get('status', {})
                                        if status.get('code') == 2 or status.get('code') == 'STATUS_CODE_ERROR':
                                            trace_issues.append(f"Span Error: {span.get('name')} - {status.get('message', 'No message')}")
                                        
                                        # Check attributes for http.status_code >= 500
                                        attributes = span.get('attributes', [])
                                        for attr in attributes:
                                            if attr['key'] == 'http.status_code':
                                                val = attr['value'].get('intValue')
                                                if val and val >= 500:
                                                    trace_issues.append(f"HTTP Error {val} in span {span.get('name')}")
            except Exception as e:
                pass

    if trace_issues:
        print(f"\nFound {len(trace_issues)} trace issues. Showing top 5:")
        for i, issue in enumerate(trace_issues[:5]):
            print(f"  {i+1}. {issue}")
    else:
        print("\n[WARNING] No explicit errors found in traces (checked status.code and http.status_code).")
        # Print structure of one trace to verify we are parsing correctly
        if 'trace_slowest_json' in df.columns:
             print("\nSample Trace Structure (first span):")
             try:
                 raw = df.iloc[0]['trace_slowest_json']
                 if isinstance(raw, str): raw = json.loads(raw)
                 if 'batches' in raw and len(raw['batches']) > 0:
                     print(json.dumps(raw['batches'][0].get('scopeSpans', [])[0].get('spans', [])[0], indent=2)[:500] + "...")
             except:
                 print("Could not parse sample trace.")

if __name__ == "__main__":
    deep_inspect(sys.argv[1])
