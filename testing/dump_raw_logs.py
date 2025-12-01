
import pandas as pd
import sys

def dump_raw(file_path):
    df = pd.read_parquet(file_path)
    if 'log_context' not in df.columns:
        print("No log_context column")
        return
    
    print(f"Rows: {len(df)}")
    for i, row in df.iterrows():
        raw = row['log_context']
        print(f"Row {i} Type: {type(raw)}")
        if isinstance(raw, str):
            print(f"Row {i} Length: {len(raw)}")
            print(f"Row {i} Content (first 500 chars): {raw[:500]}")
        elif isinstance(raw, list):
            print(f"Row {i} List Length: {len(raw)}")
            print(f"Row {i} First item: {raw[0] if raw else 'EMPTY'}")

if __name__ == "__main__":
    dump_raw(sys.argv[1])
