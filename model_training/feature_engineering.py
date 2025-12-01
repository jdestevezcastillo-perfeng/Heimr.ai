import pandas as pd
import logging

def select_features(df):
    """
    Selects relevant features for training.
    """
    # 1. Base Metrics (Numerical)
    # We need to find the actual column names from the dataframe as they might have labels
    # For simplicity, we'll look for columns containing specific substrings
    
    metric_keywords = [
        "http_request_duration_seconds_sum", 
        "container_cpu_usage_seconds_total",
        "container_memory_usage_bytes",
        "go_memstats_alloc_bytes",
        "process_cpu_seconds_total"
    ]
    
    selected_metrics = []
    for col in df.columns:
        for kw in metric_keywords:
            if kw in col:
                selected_metrics.append(col)
                break
    
    # 2. Extracted Features (from Logs/Traces)
    extracted_features = [
        'log_error_count',
        'log_has_oom',
        'log_has_timeout',
        'log_has_connection_refused',
        'log_has_deadlock',
        'trace_max_duration_ms',
        'trace_has_error',
        'trace_span_count'
    ]
    
    # Ensure extracted features exist
    valid_extracted = [f for f in extracted_features if f in df.columns]
    
    feature_cols = selected_metrics + valid_extracted
    
    logging.info(f"Selected {len(feature_cols)} features: {len(selected_metrics)} metrics + {len(valid_extracted)} extracted.")
    
    X = df[feature_cols].copy()
    
    # Handle missing values in metrics (fill with 0 or mean)
    X = X.fillna(0)
    
    # Target
    y = df['is_failure']
    
    return X, y, feature_cols
