import subprocess
import pandas as pd
import os
import sys

BUCKET = "gs://heimr-data-tokyo-snow-479722-a2"
TEMP_DIR = "temp_verification"

def run_cmd(cmd):
    try:
        return subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
    except subprocess.TimeoutExpired:
        print(f"❌ TIMEOUT running: {cmd}")
        return subprocess.CompletedProcess(cmd, 1, "", "Timeout")

def get_all_files():
    print("Listing all files in bucket...")
    res = run_cmd(f"gsutil ls {BUCKET}")
    files = [f for f in res.stdout.splitlines() if f.endswith(".parquet")]
    return files

def verify_and_clean():
    files = get_all_files()
    print(f"Found {len(files)} files to check.")
    
    os.makedirs(TEMP_DIR, exist_ok=True)
    
    bad_files = []
    good_count = 0
    
    # Process in chunks to avoid disk fill up if many files
    for i, file_url in enumerate(files):
        filename = os.path.basename(file_url)
        local_path = os.path.join(TEMP_DIR, filename)
        
        # Download
        run_cmd(f"gsutil cp {file_url} {local_path}")
        
        try:
            # Read schema only
            df = pd.read_parquet(local_path)
            cols = df.columns.tolist()
            
            has_logs = any('log_' in c for c in cols)
            has_traces = any('trace_' in c for c in cols)
            
            if not (has_logs and has_traces):
                print(f"❌ BAD FILE (Missing columns): {filename}")
                bad_files.append(file_url)
            else:
                good_count += 1
                print(f"✅ Checked {i+1}/{len(files)}: {filename}")
                    
        except Exception as e:
            print(f"❌ ERROR reading {filename}: {e}")
            bad_files.append(file_url)
        finally:
            # Cleanup local file
            if os.path.exists(local_path):
                os.remove(local_path)

    print(f"\n=== SUMMARY ===")
    print(f"Total Checked: {len(files)}")
    print(f"Good Files: {good_count}")
    print(f"Bad Files: {len(bad_files)}")
    
    if bad_files:
        print(f"\nDeleting {len(bad_files)} bad files...")
        # Batch delete
        batch_size = 100
        for i in range(0, len(bad_files), batch_size):
            batch = bad_files[i:i+batch_size]
            cmd = f"gsutil -m rm {' '.join(batch)}"
            print(f"Deleting batch {i//batch_size + 1}...")
            run_cmd(cmd)
        print("Cleanup complete.")
    else:
        print("All files are valid! ✅")

    os.rmdir(TEMP_DIR)

if __name__ == "__main__":
    verify_and_clean()
