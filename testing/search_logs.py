
import pandas as pd
import sys
import ast

def search_logs(file_path, keyword):
    print(f"Searching for '{keyword}' in {file_path}...")
    df = pd.read_parquet(file_path)
    
    found_count = 0
    for i, row in df.iterrows():
        logs_str = row['log_context']
        if not logs_str:
            continue
            
        try:
            logs = ast.literal_eval(logs_str)
        except:
            print(f"Row {i}: Failed to parse logs")
            continue
            
        for log in logs:
            if keyword in log:
                print(f"FOUND in Row {i}: {log}")
                found_count += 1
                
    print(f"Total matches: {found_count}")

if __name__ == "__main__":
    search_logs(sys.argv[1], sys.argv[2])
