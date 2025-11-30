import subprocess
from datetime import datetime
import os

BUCKET = "gs://heimr-data-tokyo-snow-479722-a2"
# Timestamp when the new generator was deployed (approx)
CUTOFF_TIME = datetime.strptime("2025-11-30T15:58:00Z", "%Y-%m-%dT%H:%M:%SZ")

def get_files():
    cmd = f"gsutil ls -l {BUCKET}"
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    files = []
    for line in result.stdout.splitlines():
        parts = line.split()
        if len(parts) < 3: continue
        if not parts[-1].endswith(".parquet"): continue
        
        # Format: 850891  2025-11-30T15:58:29Z  gs://...
        try:
            size = parts[0]
            time_str = parts[1]
            path = parts[2]
            file_time = datetime.strptime(time_str, "%Y-%m-%dT%H:%M:%SZ")
            files.append((path, file_time))
        except ValueError:
            continue
    return files

def clean_legacy_files():
    files = get_files()
    to_delete = []
    
    print(f"Found {len(files)} total files.")
    
    for path, file_time in files:
        if file_time < CUTOFF_TIME:
            to_delete.append(path)
            
    print(f"Identified {len(to_delete)} legacy files to delete (older than {CUTOFF_TIME}).")
    
    if not to_delete:
        print("No legacy files found.")
        return

    # Batch delete
    batch_size = 100
    for i in range(0, len(to_delete), batch_size):
        batch = to_delete[i:i+batch_size]
        cmd = f"gsutil -m rm {' '.join(batch)}"
        print(f"Deleting batch {i//batch_size + 1}...")
        subprocess.run(cmd, shell=True)
        
    print("Cleanup complete.")

if __name__ == "__main__":
    clean_legacy_files()
