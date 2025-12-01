import pandas as pd
import sys
import os

try:
    file_path = sys.argv[1]
    df = pd.read_parquet(file_path)
    print(f"Loaded {file_path}")
    print(f"Shape: {df.shape}")
    print("Columns:", df.columns.tolist())
    print("\nSample Data:")
    print(df.head(1).T)
    
    # Check for specific columns
    required_cols = ['timestamp', 'scenario_id', 'label', 'log_total_count', 'trace_count']
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        print(f"\nMISSING COLUMNS: {missing}")
    else:
        print("\nAll required columns present.")
        
    # Check for non-zero values
    print(f"\nTotal Logs: {df['log_total_count'].sum()}")
    print(f"Total Traces: {df['trace_count'].sum()}")
    
except Exception as e:
    print(f"Error: {e}")
