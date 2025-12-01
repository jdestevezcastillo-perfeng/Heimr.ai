import time
import logging
import argparse
import pandas as pd
from model_training.data_loader import load_from_gcs, preprocess_data
from model_training.feature_engineering import select_features

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

BUCKET_NAME = "heimr-data-tokyo-snow-479722-a2"
CACHE_DIR = "data/gcs_cache"

def validate_data(df):
    if df.empty:
        logging.warning("No data to validate.")
        return

    logging.info(f"--- Validation Report ---")
    logging.info(f"Total Rows: {len(df)}")
    logging.info(f"Class Distribution:\n{df['is_failure'].value_counts()}")
    
    # Check for missing values in critical columns
    missing_logs = df['log_context'].isnull().sum()
    missing_traces = df['trace_slowest_json'].isnull().sum()
    logging.info(f"Missing Logs: {missing_logs} | Missing Traces: {missing_traces}")
    
    # Feature Engineering Check
    try:
        X, y, features = select_features(df)
        logging.info(f"Feature Engineering Successful. Features: {len(features)}")
        logging.info(f"Sample Features:\n{X.head(1)}")
    except Exception as e:
        logging.error(f"Feature Engineering Failed: {e}")

def watch_loop(interval=60):
    logging.info(f"Starting GCS Watcher for bucket: {BUCKET_NAME}")
    logging.info(f"Polling interval: {interval} seconds")
    
    while True:
        try:
            logging.info("Checking for new files...")
            # load_from_gcs handles downloading new files and loading everything
            # We might want to optimize to only load new files for validation, 
            # but for now loading everything ensures we see the growing dataset stats.
            df = load_from_gcs(BUCKET_NAME, CACHE_DIR)
            
            if not df.empty:
                # Preprocess (parse logs/traces)
                df = preprocess_data(CACHE_DIR) # preprocess_data calls load_data internally, so we point it to cache
                validate_data(df)
            
        except Exception as e:
            logging.error(f"Watch Loop Error: {e}")
            
        time.sleep(interval)

if __name__ == "__main__":
    watch_loop()
