# Copyright (c) 2025 Juan Estevez Castillo
# Licensed under AGPL v3. Commercial licenses available.
# See LICENSE or https://www.gnu.org/licenses/agpl-3.0.html
"""
Anomaly detection using statistical methods.
"""
import pandas as pd


class AnomalyDetector:
    """
    Detects anomalies in load test metrics using statistical methods.
    """

    def __init__(self, df: pd.DataFrame):
        self.df = df

    def detect_latency_anomalies(self) -> pd.DataFrame:
        """
        Detects anomalies in the 'elapsed' (latency) column using multiple signals.
        Returns a DataFrame containing only the anomalous rows.
        """
        if 'elapsed' not in self.df.columns:
            raise ValueError("DataFrame missing 'elapsed' column")

        # Calculate statistics
        mean_latency = self.df['elapsed'].mean()
        std_latency = self.df['elapsed'].std()
        p50 = self.df['elapsed'].quantile(0.50)
        p99 = self.df['elapsed'].quantile(0.99)

        # Initialize anomalies DataFrame
        anomalies = pd.DataFrame()

        # Signal 1: Absolute latency threshold (> 500ms average)
        # Catches scenarios with consistently high latency (Global Latency Shift, Large Payload)
        if mean_latency > 500:
            # Mark all requests above P50 as anomalies
            absolute_anomalies = self.df[self.df['elapsed'] > p50].copy()
            anomalies = pd.concat([anomalies, absolute_anomalies])

        # Signal 2: Statistical outliers (> mean + 2.5σ)
        threshold = mean_latency + (2.5 * std_latency)
        statistical_anomalies = self.df[self.df['elapsed'] > threshold].copy()

        # Signal 3: Bimodal distribution check (P99 >> P50)
        # Indicates cache miss pattern or similar bimodal behavior
        if p99 > p50 * 2:
            # Mark top 10% as anomalies (tail latency)
            tail_threshold = p99 * 0.9
            tail_anomalies = self.df[self.df['elapsed'] > tail_threshold].copy()
            anomalies = pd.concat([anomalies, tail_anomalies])

        # Signal 4: Gradual degradation (memory leak pattern)
        # Check if last 20% of requests are significantly slower than first 20%
        if len(self.df) >= 20:
            first_20_pct = int(len(self.df) * 0.2)
            last_20_pct = int(len(self.df) * 0.2)

            first_avg = self.df.head(first_20_pct)['elapsed'].mean()
            last_avg = self.df.tail(last_20_pct)['elapsed'].mean()

            # If last 20% is 50% slower, mark them as anomalies
            if last_avg > first_avg * 1.5:
                degradation_anomalies = self.df.tail(last_20_pct).copy()
                anomalies = pd.concat([anomalies, degradation_anomalies])

        # Combine with statistical anomalies
        anomalies = pd.concat([anomalies, statistical_anomalies])

        # Remove duplicates
        anomalies = anomalies.drop_duplicates()

        # Sort by timestamp if available
        if 'timestamp_dt' in anomalies.columns:
            anomalies = anomalies.sort_values('timestamp_dt')

        return anomalies

    def get_anomaly_summary(self, anomalies: pd.DataFrame) -> dict:
        """
        Returns a summary dict of anomaly statistics.
        """
        if anomalies.empty:
            return {
                "count": 0,
                "avg_latency": 0,
                "max_latency": 0,
                "timestamps": []
            }

        return {
            "count": len(anomalies),
            "avg_latency": anomalies['elapsed'].mean(),
            "max_latency": anomalies['elapsed'].max(),
            "timestamps": anomalies['timestamp_dt'].tolist() if 'timestamp_dt' in anomalies.columns else []
        }
