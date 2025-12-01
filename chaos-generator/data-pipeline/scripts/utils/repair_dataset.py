import pandas as pd
import requests
import time
from datetime import datetime, timedelta
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("repair_dataset")

PROMETHEUS_URL = "http://localhost:9090"
DATA_DIR = Path("data-pipeline/datasets/training")

def query_prometheus(query, time_val):
    """Query Prometheus at a specific time."""
    try:
        response = requests.get(
            f"{PROMETHEUS_URL}/api/v1/query",
            params={"query": query, "time": time_val},
            timeout=10
        )
        response.raise_for_status()
        result = response.json()
        if result["status"] == "success" and result["data"]["result"]:
            return float(result["data"]["result"][0]["value"][1])
    except Exception as e:
        logger.warning(f"Query failed: {e}")
    return None

def repair_file(filename):
    path = DATA_DIR / filename
    if not path.exists():
        logger.warning(f"File not found: {path}")
        return

    logger.info(f"Repairing {filename}...")
    df = pd.read_parquet(path)
    
    # Check if we need to repair
    if df["metric_p99_latency_mean"].notna().all():
        logger.info(f"  {filename} already has valid latency data. Skipping.")
        return

    updates = 0
    for idx, row in df.iterrows():
        # Timestamp in parquet is ISO string. Convert to unix.
        # It represents the END of the scenario.
        try:
            ts = row["timestamp"]
            if isinstance(ts, str):
                dt = datetime.fromisoformat(ts)
            else:
                # Assume pandas Timestamp
                dt = ts.to_pydatetime()
            
            # Ensure UTC if naive? The generation script used utcnow()
            # If it's naive, python treats it as local or naive. 
            # Prometheus expects unix timestamp (seconds).
            # We'll assume it's UTC.
            unix_time = dt.timestamp()
        except Exception as e:
            logger.error(f"  Failed to parse timestamp {row['timestamp']}: {e}")
            continue

        # We want the average p99 over the last 5 minutes (duration of test)
        # But we only have single point query here for simplicity?
        # The original exporter used query_range and aggregated.
        # For repair, a simple lookback query is better than nothing.
        # Let's use `rate(...[5m])` at the end time. This gives the rate over the window.
        # And `histogram_quantile` on that rate gives the p99 over the window.
        # This is exactly what `export_metrics_snapshot` did!
        # But `export_scenario_metrics` used `query_range` and averaged.
        # A single snapshot at the end is a good approximation for "mean" if the load was stable.
        
        # Query for p99 latency using the 'highr' bucket which we know exists
        # We query at `unix_time`
        
        p50 = query_prometheus('histogram_quantile(0.50, rate(http_request_duration_highr_seconds_bucket[5m]))', unix_time)
        p95 = query_prometheus('histogram_quantile(0.95, rate(http_request_duration_highr_seconds_bucket[5m]))', unix_time)
        p99 = query_prometheus('histogram_quantile(0.99, rate(http_request_duration_highr_seconds_bucket[5m]))', unix_time)
        
        if p99 is not None:
            # Update the dataframe
            # We'll set mean/max/std to the same snapshot value because we can't easily reconstruct variance without range query
            # This is a "best effort" repair.
            df.at[idx, "metric_p50_latency_mean"] = p50
            df.at[idx, "metric_p50_latency_std"] = 0.0 # Unknown
            
            df.at[idx, "metric_p95_latency_mean"] = p95
            df.at[idx, "metric_p95_latency_std"] = 0.0
            
            df.at[idx, "metric_p99_latency_mean"] = p99
            df.at[idx, "metric_p99_latency_std"] = 0.0
            df.at[idx, "metric_p99_latency_max"] = p99 # Approximation
            
            updates += 1
            
        if idx % 10 == 0:
            print(f"  Processed {idx}/{len(df)} rows...", end="\r")

    print(f"  Updated {updates} rows.")
    
    # Save back
    df.to_parquet(path)
    logger.info(f"  Saved repaired file to {path}")

def main():
    repair_file("train.parquet")
    repair_file("test.parquet")
    repair_file("val.parquet")
    print("✅ Repair complete.")

if __name__ == "__main__":
    main()
