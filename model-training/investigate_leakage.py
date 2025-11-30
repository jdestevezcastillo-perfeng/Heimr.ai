"""
Data leakage investigation script.
Checks for features that perfectly or near-perfectly predict the label.
"""
import pandas as pd
import numpy as np
from pathlib import Path
from sklearn.metrics import mutual_info_score

print("=" * 60)
print("DATA LEAKAGE INVESTIGATION")
print("=" * 60)

# Load data
data_dir = Path("model-training/sample_data")
parquet_files = list(data_dir.glob("*.parquet"))

dfs = []
for file in parquet_files:
    df = pd.read_parquet(file)
    dfs.append(df)

combined_df = pd.concat(dfs, ignore_index=True)
combined_df['is_healthy'] = (combined_df['scenario_id'] == 'API-001').astype(int)

print(f"\n✓ Loaded {len(combined_df)} rows")

# Drop non-feature columns
feature_cols = [col for col in combined_df.columns 
                if col not in ['timestamp', 'scenario_id', 'label', 'is_healthy']]

X = combined_df[feature_cols].fillna(0)
y = combined_df['is_healthy']

print(f"✓ Analyzing {len(feature_cols)} features")

# Check 1: Perfect separators (features with 100% correlation)
print(f"\n{'=' * 60}")
print("CHECK 1: Looking for perfect predictors...")
print("=" * 60)

perfect_features = []
for col in feature_cols:
    # For each unique value of the feature, check if it always maps to same label
    col_values = X[col]
    unique_vals = col_values.unique()
    
    is_perfect = True
    for val in unique_vals:
        mask = col_values == val
        labels_for_val = y[mask].unique()
        if len(labels_for_val) > 1:
            is_perfect = False
            break
    
    if is_perfect and len(unique_vals) > 1:
        perfect_features.append(col)

if perfect_features:
    print(f"⚠️  Found {len(perfect_features)} features that perfectly separate classes:")
    for feat in perfect_features[:10]:
        print(f"  - {feat}")
    if len(perfect_features) > 10:
        print(f"  ... and {len(perfect_features) - 10} more")
else:
    print("✅ No perfect separators found")

# Check 2: Near-perfect features (mutual information)
print(f"\n{'=' * 60}")
print("CHECK 2: Computing mutual information scores...")
print("=" * 60)

mi_scores = {}
for col in feature_cols[:100]:  # Sample first 100 to save time
    try:
        mi = mutual_info_score(y, X[col])
        if mi > 0.01:  # Only store non-zero scores
            mi_scores[col] = mi
    except:
        pass

if mi_scores:
    sorted_mi = sorted(mi_scores.items(), key=lambda x: x[1], reverse=True)
    print(f"\nTop 10 features by mutual information:")
    for feat, score in sorted_mi[:10]:
        # Truncate long names
        feat_display = feat[:50] + "..." if len(feat) > 50 else feat
        print(f"  {score:.4f} - {feat_display}")

# Check 3: Variance analysis
print(f"\n{'=' * 60}")
print("CHECK 3: Checking for constant features...")
print("=" * 60)

zero_var_features = []
for col in feature_cols:
    if X[col].std() == 0:
        zero_var_features.append(col)

print(f"Features with zero variance: {len(zero_var_features)} / {len(feature_cols)}")

# Check 4: Class-specific constant features
print(f"\n{'=' * 60}")
print("CHECK 4: Features constant within each class...")
print("=" * 60)

class_constant_features = []
for col in feature_cols:
    healthy_vals = X[y == 1][col].unique()
    failure_vals = X[y == 0][col].unique()
    
    # If each class has only one unique value, but they differ between classes
    if len(healthy_vals) == 1 and len(failure_vals) == 1 and healthy_vals[0] != failure_vals[0]:
        class_constant_features.append(col)

if class_constant_features:
    print(f"⚠️  Found {len(class_constant_features)} features constant within each class:")
    for feat in class_constant_features[:10]:
        feat_display = feat[:50] + "..." if len(feat) > 50 else feat
        healthy_val = X[y == 1][feat].iloc[0]
        failure_val = X[y == 0][feat].iloc[0]
        print(f"  - {feat_display}")
        print(f"      Healthy: {healthy_val:.2f}, Failure: {failure_val:.2f}")
    if len(class_constant_features) > 10:
        print(f"  ... and {len(class_constant_features) - 10} more")
else:
    print("✅ No class-constant features found")

# Check 5: Baseline comparison
print(f"\n{'=' * 60}")
print("CHECK 5: Baseline classifier performance...")
print("=" * 60)

from sklearn.dummy import DummyClassifier
from sklearn.model_selection import cross_val_score

# Majority class baseline
dummy_clf = DummyClassifier(strategy='most_frequent')
baseline_scores = cross_val_score(dummy_clf, X, y, cv=3, scoring='accuracy')
print(f"Majority class baseline: {baseline_scores.mean():.2%} (±{baseline_scores.std():.2%})")

# Stratified random baseline
dummy_clf_strat = DummyClassifier(strategy='stratified')
strat_scores = cross_val_score(dummy_clf_strat, X, y, cv=3, scoring='accuracy')
print(f"Stratified random baseline: {strat_scores.mean():.2%} (±{strat_scores.std():.2%})")

print(f"\n{'=' * 60}")
print("INVESTIGATION COMPLETE")
print("=" * 60)
