"""
Quick model training validation script.
Tests the full pipeline: data loading → preprocessing → training → evaluation.
"""
import pandas as pd
import numpy as np
from pathlib import Path
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, confusion_matrix
import glob

print("=" * 60)
print("MODEL TRAINING VALIDATION")
print("=" * 60)

# Load all sample Parquet files
data_dir = Path("model-training/sample_data")
parquet_files = list(data_dir.glob("*.parquet"))

print(f"\n✓ Found {len(parquet_files)} Parquet files")

# Load and combine data
dfs = []
for file in parquet_files:
    df = pd.read_parquet(file)
    dfs.append(df)

combined_df = pd.concat(dfs, ignore_index=True)
print(f"✓ Loaded {len(combined_df)} total rows")
print(f"✓ Total features: {len(combined_df.columns)} columns")

# Create binary classification labels: Healthy vs Failure
combined_df['is_healthy'] = combined_df['scenario_id'] == 'API-001'

print(f"\n--- CLASS DISTRIBUTION ---")
print(f"Healthy samples: {combined_df['is_healthy'].sum()}")
print(f"Failure samples: {(~combined_df['is_healthy']).sum()}")

# Prepare features and labels
# Drop non-feature columns
feature_cols = [col for col in combined_df.columns 
                if col not in ['timestamp', 'scenario_id', 'label', 'is_healthy']]

X = combined_df[feature_cols]
y = combined_df['is_healthy'].astype(int)

# Handle any remaining NaNs (replace with 0)
X = X.fillna(0)

print(f"\n✓ Feature matrix shape: {X.shape}")
print(f"✓ Target vector shape: {y.shape}")

# Split data
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.3, random_state=42, stratify=y
)

print(f"\n--- TRAIN/TEST SPLIT ---")
print(f"Training samples: {len(X_train)}")
print(f"Test samples: {len(X_test)}")

# Train a simple Random Forest classifier
print(f"\n--- TRAINING MODEL ---")
clf = RandomForestClassifier(
    n_estimators=50,
    max_depth=10,
    random_state=42,
    n_jobs=-1
)

clf.fit(X_train, y_train)
print("✓ Model training complete")

# Evaluate
train_score = clf.score(X_train, y_train)
test_score = clf.score(X_test, y_test)

print(f"\n--- MODEL PERFORMANCE ---")
print(f"Training Accuracy: {train_score:.2%}")
print(f"Test Accuracy: {test_score:.2%}")

# Detailed metrics
y_pred = clf.predict(X_test)
print(f"\n--- CLASSIFICATION REPORT ---")
print(classification_report(y_test, y_pred, target_names=['Failure', 'Healthy']))

print(f"\n--- CONFUSION MATRIX ---")
cm = confusion_matrix(y_test, y_pred)
print(f"              Predicted")
print(f"              Failure  Healthy")
print(f"Actual Failure  {cm[0][0]:3d}      {cm[0][1]:3d}")
print(f"       Healthy  {cm[1][0]:3d}      {cm[1][1]:3d}")

# Feature importance (top 10)
importances = clf.feature_importances_
indices = np.argsort(importances)[::-1][:10]

print(f"\n--- TOP 10 IMPORTANT FEATURES ---")
for i, idx in enumerate(indices, 1):
    feature_name = feature_cols[idx]
    # Truncate long feature names
    if len(feature_name) > 50:
        feature_name = feature_name[:47] + "..."
    print(f"{i:2d}. {feature_name:50s} {importances[idx]:.4f}")

print(f"\n{'=' * 60}")
print("VALIDATION COMPLETE ✓")
print("=" * 60)
