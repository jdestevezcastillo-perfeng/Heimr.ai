import subprocess
import time
from datetime import datetime
import sys

BUCKET = "gs://heimr-data-tokyo-snow-479722-a2"

def get_bucket_stats():
    try:
        # Get count
        # We use gsutil ls and count lines. Note: this lists all objects.
        res_count = subprocess.run(f"gsutil ls {BUCKET} | wc -l", shell=True, capture_output=True, text=True)
        if res_count.returncode != 0:
            return 0, 0.0
        count = int(res_count.stdout.strip())
        
        # Get size
        # gsutil du -s returns total size in bytes
        res_size = subprocess.run(f"gsutil du -s {BUCKET}", shell=True, capture_output=True, text=True)
        if res_size.returncode != 0:
            return count, 0.0
            
        output = res_size.stdout.strip()
        if not output:
            return count, 0.0
            
        size_bytes = int(output.split()[0])
        size_mb = size_bytes / (1024 * 1024)
        
        return count, size_mb
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 0, 0.0

def main():
    print(f"📊 Monitoring growth of {BUCKET}...")
    print(f"{'Time':<10} | {'Files':<6} | {'Size (MB)':<10} | {'Growth':<10}")
    print("-" * 45)

    last_count = 0
    
    try:
        while True:
            count, size_mb = get_bucket_stats()
            timestamp = datetime.now().strftime("%H:%M:%S")
            
            growth = f"+{count - last_count}" if last_count > 0 else "-"
            if last_count == 0: 
                last_count = count # Initialize
            
            print(f"{timestamp:<10} | {count:<6d} | {size_mb:<10.2f} | {growth:<10}")
            
            last_count = count
            time.sleep(30) # Check every 30 seconds
    except KeyboardInterrupt:
        print("\nStopped.")

if __name__ == "__main__":
    main()
