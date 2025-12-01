import pandas as pd
import json
import ast
import glob
import os
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def load_data(data_dir):
    """
    Loads all Parquet files from the specified directory and concatenates them.
    """
    files = glob.glob(os.path.join(data_dir, "*.parquet"))
    if not files:
        logging.warning(f"No Parquet files found in {data_dir}")
        return pd.DataFrame()
    
    logging.info(f"Found {len(files)} files. Loading...")
    dfs = []
    for f in files:
        try:
            df = pd.read_parquet(f)
            # Extract scenario ID from filename (e.g., ..._API-001_...)
            filename = os.path.basename(f)
            if "_API-" in filename:
                scenario_id = filename.split("_API-")[1].split("_")[0]
                df['scenario_id'] = "API-" + scenario_id
            else:
                df['scenario_id'] = "UNKNOWN"
            
            # Label: 0 for Healthy (API-001), 1 for Failure (others)
            df['is_failure'] = df['scenario_id'].apply(lambda x: 0 if x == 'API-001' else 1)
            
            dfs.append(df)
        except Exception as e:
            logging.error(f"Error loading {f}: {e}")
    
    if not dfs:
        return pd.DataFrame()
        
    full_df = pd.concat(dfs, ignore_index=True)
    logging.info(f"Loaded {len(full_df)} rows total.")
    return full_df

def parse_logs(df):
    """
    Extracts features from the 'log_context' column.
    """
    if 'log_context' not in df.columns:
        return df

    logging.info("Parsing log_context...")
    
    # Feature: Log Error Count
    def count_errors(log_str):
        if not log_str: return 0
        try:
            logs = ast.literal_eval(log_str)
            count = 0
            for log in logs:
                if "ERROR" in log or "Exception" in log or " 500 " in log or " 503 " in log:
                    count += 1
            return count
        except:
            return 0

    df['log_error_count'] = df['log_context'].apply(count_errors)
    
    # Feature: Specific Keywords (Categorical-ish)
    # For now, let's just extract if specific keywords are present
    keywords = ["OOM", "Timeout", "Connection refused", "deadlock"]
    for kw in keywords:
        df[f'log_has_{kw.lower().replace(" ", "_")}'] = df['log_context'].apply(lambda x: 1 if isinstance(x, str) and kw in x else 0)

    return df

def parse_traces(df):
    """
    Extracts features from 'trace_slowest_json'.
    """
    if 'trace_slowest_json' not in df.columns:
        return df

    logging.info("Parsing trace_slowest_json...")

    def extract_trace_features(trace_str):
        duration = 0
        has_error = 0
        span_count = 0
        
        if not isinstance(trace_str, str) or len(trace_str) < 5:
            return pd.Series([0, 0, 0])

        try:
            trace = json.loads(trace_str)
            # OTLP format support
            spans = []
            if "batches" in trace:
                for batch in trace.get("batches", []):
                    for scope_span in batch.get("scopeSpans", []):
                        spans.extend(scope_span.get("spans", []))
            elif "spans" in trace:
                spans = trace["spans"]
            
            span_count = len(spans)
            
            if spans:
                # Max duration
                for span in spans:
                    start = int(span.get("startTimeUnixNano", 0))
                    end = int(span.get("endTimeUnixNano", 0))
                    d = (end - start) / 1e6
                    if d > duration:
                        duration = d
                    
                    # Check for error status (status code 2 = Error in OTLP)
                    status = span.get("status", {})
                    if status.get("code") == 2 or status.get("code") == "STATUS_CODE_ERROR":
                        has_error = 1
                        
        except:
            pass
            
        return pd.Series([duration, has_error, span_count])

    df[['trace_max_duration_ms', 'trace_has_error', 'trace_span_count']] = df['trace_slowest_json'].apply(extract_trace_features)
    return df

def preprocess_data(data_dir):
    df = load_data(data_dir)
    if df.empty:
        return df
    
    df = parse_logs(df)
    df = parse_traces(df)
    
    # Fill NaNs for created features
    cols_to_fill = ['log_error_count', 'trace_max_duration_ms', 'trace_has_error', 'trace_span_count']
    for col in cols_to_fill:
        if col in df.columns:
            df[col] = df[col].fillna(0)
            
    return df
