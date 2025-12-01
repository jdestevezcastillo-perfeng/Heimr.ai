import time
import logging
import argparse
import os
import pandas as pd
from datetime import datetime
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, roc_auc_score
from catboost import CatBoostClassifier

try:
    from .data_loader import load_from_gcs, preprocess_data
    from .feature_engineering import select_features
except ImportError:
    from data_loader import load_from_gcs, preprocess_data
    from feature_engineering import select_features

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

BUCKET_NAME = "heimr-data-tokyo-snow-479722-a2"
CACHE_DIR = "data/gcs_cache"
MODEL_DIR = "model_training/models/live"
MIN_NEW_SAMPLES = 50

def train_iteration(df, iteration_count):
    logging.info(f"--- Starting Training Iteration {iteration_count} ---")
    logging.info(f"Dataset Size: {len(df)} rows")
    
    # 1. Feature Engineering
    try:
        # We need to preprocess again because load_from_gcs returns raw-ish data (concatenated)
        # But wait, load_from_gcs calls load_data which does basic parsing.
        # We need preprocess_data to do the log/trace parsing if it's not done in load_data.
        # Checking data_loader.py... load_data does NOT call parse_logs/parse_traces.
        # preprocess_data DOES.
        
        # Optimization: We could cache processed features, but for <10k rows, re-processing is fast enough.
        df_processed = preprocess_data(CACHE_DIR) 
        
        X, y, feature_names = select_features(df_processed)
        
        # 2. Split
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
        
        # 3. Train
        model = CatBoostClassifier(
            iterations=500, # Reduced for live training speed
            learning_rate=0.1,
            depth=6,
            loss_function='Logloss',
            verbose=False,
            random_seed=42
        )
        
        model.fit(X_train, y_train, eval_set=(X_test, y_test), early_stopping_rounds=20)
        
        # 4. Evaluate
        y_pred = model.predict(X_test)
        y_prob = model.predict_proba(X_test)[:, 1]
        
        roc_auc = roc_auc_score(y_test, y_prob)
        logging.info(f"Iteration {iteration_count} Results - ROC-AUC: {roc_auc:.4f}")
        print(classification_report(y_test, y_pred))
        
        # 5. Save
        timestamp = int(time.time())
        model_path = os.path.join(MODEL_DIR, f"heimr_live_v{iteration_count}_{timestamp}_n{len(df)}.cbm")
        model.save_model(model_path)
        logging.info(f"Model saved to {model_path}")
        
        return len(df)
        
    except Exception as e:
        logging.error(f"Training failed: {e}")
        return 0

def live_training_loop():
    os.makedirs(MODEL_DIR, exist_ok=True)
    last_count = 0
    iteration = 1
    
    logging.info(f"Starting Live Training Loop. Monitoring {BUCKET_NAME}...")
    
    while True:
        try:
            # Download new files and get full dataframe
            df = load_from_gcs(BUCKET_NAME, CACHE_DIR)
            
            current_count = len(df)
            new_samples = current_count - last_count
            
            if new_samples >= MIN_NEW_SAMPLES:
                logging.info(f"Found {new_samples} new samples. Triggering training...")
                if train_iteration(df, iteration):
                    last_count = current_count
                    iteration += 1
            else:
                logging.info(f"Only {new_samples} new samples (Threshold: {MIN_NEW_SAMPLES}). Waiting...")
                
        except Exception as e:
            logging.error(f"Live Loop Error: {e}")
            
        time.sleep(60) # Check every minute

if __name__ == "__main__":
    live_training_loop()
