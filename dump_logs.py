import pandas as pd
import sys
import numpy as np

def dump_logs(file_path):
    print(f"Dumping logs from {file_path}...")
    try:
        df = pd.read_parquet(file_path)
    except Exception as e:
        print(f"Failed to read parquet file: {e}")
        return

    if 'log_context' in df.columns:
        print(f"Scanning {len(df)} rows of log_context...")
        count = 0
        for idx, row in df.iterrows():
            logs = row['log_context']
            if isinstance(logs, (list, np.ndarray)):
                for log_entry in logs:
                    if isinstance(log_entry, str) and len(log_entry.strip()) > 0:
                        print(f"Log: {log_entry}")
                        count += 1
                        if count >= 20: return
    else:
        print("No log_context column.")

if __name__ == "__main__":
    dump_logs(sys.argv[1])
