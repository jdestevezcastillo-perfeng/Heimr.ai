from google.cloud import storage
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

BUCKET_NAME = "heimr-data-tokyo-snow-479722-a2"
THRESHOLD_BYTES = 100 * 1024 # 100KB (User said empty are ~10-20KB, valid ~800KB)

def clean_bucket():
    try:
        client = storage.Client()
        bucket = client.bucket(BUCKET_NAME)
        blobs = bucket.list_blobs()

        deleted_count = 0
        checked_count = 0
        
        logging.info(f"Scanning bucket {BUCKET_NAME} for files smaller than {THRESHOLD_BYTES/1024:.2f} KB...")

        for blob in blobs:
            checked_count += 1
            if blob.size < THRESHOLD_BYTES:
                logging.info(f"Deleting {blob.name} (Size: {blob.size} bytes)")
                try:
                    blob.delete()
                    deleted_count += 1
                except Exception as e:
                    logging.error(f"Failed to delete {blob.name}: {e}")
        
        logging.info(f"Cleanup complete. Scanned {checked_count} files. Deleted {deleted_count} small files.")
        
    except Exception as e:
        logging.error(f"Error accessing bucket: {e}")

if __name__ == "__main__":
    clean_bucket()
