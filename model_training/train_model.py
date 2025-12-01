import argparse
import os
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, roc_auc_score
from catboost import CatBoostClassifier

# Use relative imports when running as a module, or adjust path if running as script
try:
    from .data_loader import load_from_gcs, preprocess_data
    from .feature_engineering import select_features
except ImportError:
    from data_loader import load_from_gcs, preprocess_data
    from feature_engineering import select_features

# Configure logging
import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

BUCKET_NAME = "heimr-data-tokyo-snow-479722-a2"
# Adjust paths to be relative to the project root or current directory
# Assuming run from project root: data/gcs_cache
CACHE_DIR = "data/gcs_cache" 
# Model dir is now inside model_training/models
MODEL_DIR = "model_training/models"

def train(data_dir, output_dir, epochs=1000):
    # 1. Load and Preprocess Data
    logging.info(f"Loading data from {data_dir}...")
    df = preprocess_data(data_dir)
    
    if df.empty:
        logging.error("No data loaded. Exiting.")
        return

    logging.info(f"Data loaded. Shape: {df.shape}")
    logging.info(f"Class distribution:\n{df['is_failure'].value_counts()}")

    # 2. Feature Engineering
    X, y, feature_names = select_features(df)
    
    # 3. Split Data
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
    
    # 4. Train Model
    logging.info("Initializing CatBoostClassifier...")
    model = CatBoostClassifier(
        iterations=epochs,
        learning_rate=0.1,
        depth=6,
        loss_function='Logloss',
        verbose=100,
        random_seed=42
    )
    
    logging.info("Starting training...")
    model.fit(X_train, y_train, eval_set=(X_test, y_test), early_stopping_rounds=50)
    
    # 5. Evaluate
    logging.info("Evaluating model...")
    y_pred = model.predict(X_test)
    y_prob = model.predict_proba(X_test)[:, 1]
    
    print("\nClassification Report:")
    print(classification_report(y_test, y_pred))
    
    roc_auc = roc_auc_score(y_test, y_prob)
    print(f"ROC-AUC Score: {roc_auc:.4f}")
    
    # 6. Save Model
    os.makedirs(output_dir, exist_ok=True)
    model_path = os.path.join(output_dir, "heimr_catboost_v1.cbm")
    model.save_model(model_path)
    logging.info(f"Model saved to {model_path}")
    
    # 7. Feature Importance Plot
    feature_importance = model.get_feature_importance()
    sorted_idx = feature_importance.argsort()[-20:] # Top 20
    
    plt.figure(figsize=(10, 8))
    plt.barh(range(len(sorted_idx)), feature_importance[sorted_idx], align='center')
    plt.yticks(range(len(sorted_idx)), [feature_names[i] for i in sorted_idx])
    plt.xlabel("Feature Importance")
    plt.title("CatBoost Feature Importance")
    plt.tight_layout()
    plot_path = os.path.join(output_dir, "feature_importance.png")
    plt.savefig(plot_path)
    logging.info(f"Feature importance plot saved to {plot_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train Heimr.ai Failure Detection Model")
    parser.add_argument("--data_dir", type=str, default="data/training_data", help="Path to training data")
    parser.add_argument("--output_dir", type=str, default="models", help="Path to save model")
    parser.add_argument("--epochs", type=int, default=500, help="Number of training iterations")
    
    args = parser.parse_args()
    
    train(args.data_dir, args.output_dir, args.epochs)
