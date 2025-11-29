"""Train a bottleneck detection model."""
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import joblib
from pathlib import Path
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score

# Configuration
DATA_DIR = Path("data-pipeline/datasets/training")
MODEL_DIR = Path("model-training/models")
MODEL_DIR.mkdir(parents=True, exist_ok=True)

def load_data():
    """Load training data."""
    print("📦 Loading data...")
    try:
        df = pd.read_parquet(DATA_DIR / "train.parquet")
        print(f"   Loaded {len(df)} examples")
        return df
    except Exception as e:
        print(f"❌ Failed to load data: {e}")
        return None

def preprocess_data(df):
    """Preprocess data for training."""
    print("⚙️ Preprocessing data...")
    
    # Select features (metric_*)
    feature_cols = [c for c in df.columns if c.startswith("metric_")]
    
    # Select target
    target_col = "label_bottleneck_type"
    
    X = df[feature_cols].copy()
    y = df[target_col].copy()
    
    # Handle missing values (fill with 0 for now)
    X = X.fillna(0)
    
    # Scale features
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    
    # Encode labels
    le = LabelEncoder()
    y_encoded = le.fit_transform(y)
    
    print(f"   Features: {len(feature_cols)}")
    print(f"   Classes: {len(le.classes_)} ({le.classes_})")
    
    # Check for all-zero features
    print("\n   Feature Statistics (Mean):")
    means = X.mean()
    for col, mean_val in means.items():
        if mean_val > 0:
            print(f"   - {col}: {mean_val:.4f}")
        else:
             # Only print a few zero ones to avoid clutter if all are zero
             pass
    
    if means.sum() == 0:
        print("⚠️ WARNING: All features are zero! Model will not learn anything.")
    
    return X_scaled, y_encoded, scaler, le, feature_cols

def train_model(X, y):
    """Train Random Forest model."""
    print("🧠 Training model...")
    
    clf = RandomForestClassifier(
        n_estimators=100,
        max_depth=10,
        random_state=42
    )
    clf.fit(X, y)
    
    return clf

def evaluate_model(clf, X, y, le):
    """Evaluate model performance."""
    print("📊 Evaluating model...")
    
    y_pred = clf.predict(X)
    y_true_names = le.inverse_transform(y)
    y_pred_names = le.inverse_transform(y_pred)
    
    acc = accuracy_score(y, y_pred)
    print(f"   Accuracy: {acc:.4f}")
    
    print("\n   Classification Report:")
    print(classification_report(y_true_names, y_pred_names))
    
    # Feature Importance
    print("\n   Feature Importance:")
    importances = clf.feature_importances_
    indices = np.argsort(importances)[::-1]
    
    # Print top 10 features
    # We need feature names, passed as argument or stored
    # For now, we'll just skip printing names if not passed, but let's fix signature
    pass

def save_artifacts(clf, scaler, le):
    """Save model artifacts."""
    print("💾 Saving artifacts...")
    
    joblib.dump(clf, MODEL_DIR / "bottleneck_detector.pkl")
    joblib.dump(scaler, MODEL_DIR / "scaler.pkl")
    joblib.dump(le, MODEL_DIR / "label_encoder.pkl")
    
    print(f"   Saved to {MODEL_DIR}")

def main():
    """Main training pipeline."""
    # 1. Load Data
    df = load_data()
    if df is None:
        return
    
    # 2. Preprocess
    X, y, scaler, le, feature_names = preprocess_data(df)
    
    # 3. Train
    clf = train_model(X, y)
    
    # 4. Evaluate on Test Set
    print("\n🧪 Loading test data...")
    test_df = pd.read_parquet(DATA_DIR / "test.parquet")
    X_test, y_test, _, _, _ = preprocess_data(test_df)
    
    print("\n📊 Evaluating on TEST set...")
    evaluate_model(clf, X_test, y_test, le)
    
    # Print Feature Importance with names
    print("\n   Top 10 Features:")
    importances = clf.feature_importances_
    indices = np.argsort(importances)[::-1]
    for i in range(min(10, len(feature_names))):
        print(f"   {i+1}. {feature_names[indices[i]]}: {importances[indices[i]]:.4f}")
    
    # 5. Save
    save_artifacts(clf, scaler, le)
    
    print("\n✅ Training complete!")

if __name__ == "__main__":
    main()
