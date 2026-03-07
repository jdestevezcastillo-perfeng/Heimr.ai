# Copyright (c) 2025 Juan Estevez Castillo
# Licensed under AGPL v3. Commercial licenses available.
# See LICENSE or https://www.gnu.org/licenses/agpl-3.0.html
"""
Anomaly detection using statistical methods.
"""
import pandas as pd
from typing import Dict, Optional


class AnomalyDetector:
    """
    Detects anomalies in load test metrics using statistical methods.
    """

    def __init__(self, df: pd.DataFrame, mode: str = "simple", trend_threshold: float = 0.5):
        self.df = df
        self.mode = (mode or "simple").lower()
        self.trend_threshold = trend_threshold

    def detect_latency_anomalies(self) -> pd.DataFrame:
        """
        Detects anomalies in the 'elapsed' (latency) column using multiple signals.
        Returns a DataFrame containing only the anomalous rows.
        """
        if 'elapsed' not in self.df.columns:
            raise ValueError("DataFrame missing 'elapsed' column")

        if self.df.empty:
            return pd.DataFrame(columns=self.df.columns)

        if self.mode == "mad":
            return self._detect_mad_anomalies()
        if self.mode == "trend":
            return self._detect_trend_anomalies()

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
            absolute_anomalies["anomaly_reason"] = "absolute_shift"
            anomalies = pd.concat([anomalies, absolute_anomalies])

        # Signal 2: Statistical outliers (> mean + 2.5σ)
        threshold = mean_latency + (2.5 * std_latency)
        statistical_anomalies = self.df[self.df['elapsed'] > threshold].copy()
        if not statistical_anomalies.empty:
            statistical_anomalies["anomaly_reason"] = "zscore_outlier"

        # Signal 3: Bimodal distribution check (P99 >> P50)
        # Indicates cache miss pattern or similar bimodal behavior
        if p99 > p50 * 2:
            # Mark top 10% as anomalies (tail latency)
            tail_threshold = p99 * 0.9
            tail_anomalies = self.df[self.df['elapsed'] > tail_threshold].copy()
            tail_anomalies["anomaly_reason"] = "bimodal_tail"
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
                degradation_anomalies["anomaly_reason"] = "degradation_tail"
                anomalies = pd.concat([anomalies, degradation_anomalies])

        # Combine with statistical anomalies
        anomalies = pd.concat([anomalies, statistical_anomalies])

        # Remove duplicates
        anomalies = anomalies.drop_duplicates()

        # Sort by timestamp if available
        if 'timestamp_dt' in anomalies.columns:
            anomalies = anomalies.sort_values('timestamp_dt')

        return anomalies

    def _detect_mad_anomalies(self) -> pd.DataFrame:
        """Robust outlier detection via Median Absolute Deviation."""
        series = self.df["elapsed"]
        median = series.median()
        mad = (series - median).abs().median()
        if mad == 0 or pd.isna(mad):
            # Fallback to simple z-score when MAD collapses (e.g., many identical values).
            mean = series.mean()
            std = series.std()
            if std == 0 or pd.isna(std):
                return pd.DataFrame(columns=self.df.columns)
            threshold = mean + (2.5 * std)
            anomalies = self.df[series > threshold].copy()
            if not anomalies.empty:
                anomalies["anomaly_reason"] = "zscore_fallback"
            return anomalies
        modified_z = 0.6745 * (series - median) / mad
        anomalies = self.df[modified_z.abs() > 3.5].copy()
        if not anomalies.empty:
            anomalies["anomaly_reason"] = "mad_outlier"
        return anomalies

    def _detect_trend_anomalies(self) -> pd.DataFrame:
        """Detect trend-based degradation plus basic outliers."""
        anomalies = pd.DataFrame()
        n = len(self.df)
        quarter = max(int(n * 0.25), 1)
        first_avg = self.df.head(quarter)["elapsed"].mean()
        last_avg = self.df.tail(quarter)["elapsed"].mean()
        if first_avg > 0 and last_avg > first_avg * (1 + self.trend_threshold):
            tail = self.df.tail(quarter).copy()
            tail["anomaly_reason"] = "trend_degradation"
            anomalies = pd.concat([anomalies, tail])

        # Also include robust MAD outliers for spikes
        mad_anoms = self._detect_mad_anomalies()
        if not mad_anoms.empty:
            anomalies = pd.concat([anomalies, mad_anoms])

        anomalies = anomalies.drop_duplicates()
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

    def detect_per_endpoint_anomalies(self) -> Dict[str, dict]:
        """
        Run latency anomaly detection per endpoint/method.
        Returns mapping: "<METHOD> <endpoint>" -> anomaly summary dict.
        """
        if self.df.empty or 'endpoint' not in self.df.columns:
            return {}
        results: Dict[str, dict] = {}
        for (endpoint, method), group in self.df.groupby(['endpoint', 'method'], dropna=False):
            if len(group) < 5:
                continue
            sub_detector = AnomalyDetector(group, mode=self.mode, trend_threshold=self.trend_threshold)
            anomalies = sub_detector.detect_latency_anomalies()
            summary = sub_detector.get_anomaly_summary(anomalies)
            if summary["count"] > 0:
                results[f"{method} {endpoint}"] = summary
        return results
