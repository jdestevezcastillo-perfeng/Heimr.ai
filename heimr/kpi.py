# Copyright (c) 2025 Juan Estevez Castillo
# Licensed under AGPL v3. Commercial licenses available.
# See LICENSE or https://www.gnu.org/licenses/agpl-3.0.html
import pandas as pd
from typing import Dict, Any


class KPIEngine:
    """
    Centralized calculation engine for Performance Report KPIs.
    Expects a DataFrame normalized to the UnifiedSchema (see parsers.base).
    """

    def __init__(self, df: pd.DataFrame):
        self.df = df

        # Pre-computational check
        if self.df.empty:
            self.empty = True
        else:
            self.empty = False
            self.duration_seconds = (self.df['timestamp_dt'].max() - self.df['timestamp_dt'].min()).total_seconds()
            if self.duration_seconds <= 0:
                self.duration_seconds = 1.0  # Prevent division by zero

    def calculate_latency_stats(self) -> Dict[str, float]:
        """Calculates p50, p90, p95, p99, min, max, stddev, avg."""
        if self.empty:
            return {k: 0.0 for k in ['p50', 'p90', 'p95', 'p99', 'min', 'max', 'avg', 'stddev']}

        return {
            'min': self.df['elapsed'].min(),
            'max': self.df['elapsed'].max(),
            'avg': self.df['elapsed'].mean(),
            'stddev': self.df['elapsed'].std(),
            'p50': self.df['elapsed'].quantile(0.50),
            'p90': self.df['elapsed'].quantile(0.90),
            'p95': self.df['elapsed'].quantile(0.95),
            'p99': self.df['elapsed'].quantile(0.99)
        }

    def calculate_throughput(self) -> Dict[str, float]:
        """Calculates throughput (RPS, Bytes/sec)."""
        if self.empty:
            return {
                'requests_per_second': 0.0,
                'bytes_in_per_second': 0.0,
                'bytes_out_per_second': 0.0,
                'total_requests': 0}

        total_reqs = len(self.df)
        total_bytes_in = self.df['bytes_recv'].sum()
        total_bytes_out = self.df['bytes_sent'].sum()

        return {
            'total_requests': total_reqs,
            'requests_per_second': total_reqs / self.duration_seconds,
            'bytes_in_per_second': total_bytes_in / self.duration_seconds,
            'bytes_out_per_second': total_bytes_out / self.duration_seconds
        }

    def calculate_error_rate(self) -> Dict[str, Any]:
        """Calculates overall error rate and classifies errors."""
        if self.empty:
            return {'rate': 0.0, 'count': 0, 'classification': {}}

        total = len(self.df)
        failed = self.df[~self.df['success']]
        failed_count = len(failed)

        # Classification
        classification = {
            'http_4xx': 0,
            'http_5xx': 0,
            'timeout': 0,
            'other': 0
        }

        if failed_count > 0:
            # Vectorized classification if possible, or simple iteration
            # Assuming response_code is str and normalized

            # 4xx
            is_4xx = failed['response_code'].str.startswith('4', na=False)
            classification['http_4xx'] = is_4xx.sum()

            # 5xx
            is_5xx = failed['response_code'].str.startswith('5', na=False)
            classification['http_5xx'] = is_5xx.sum()

            # Timeouts (often 0 or 504 depending on parser, assuming '0' or specific code for now)
            # Usually parser would mark timeout. Assuming '0' or 'timeout' string.
            is_timeout = failed['response_code'].isin(['0', 'timeout'])
            classification['timeout'] = is_timeout.sum()

            classification['other'] = failed_count - \
                (classification['http_4xx'] + classification['http_5xx'] + classification['timeout'])

        return {
            'rate': (failed_count / total) * 100.0,
            'count': failed_count,
            'classification': classification
        }

    def calculate_concurrency(self) -> Dict[str, Any]:
        """Calculates stats about virtual users."""
        if self.empty:
            return {'max': 0, 'avg': 0}

        # Assuming 'vus' column is populated (default 1)
        max_vus = self.df['vus'].max()
        avg_vus = self.df['vus'].mean()

        return {
            'max': int(max_vus),
            'avg': float(round(avg_vus, 1))
        }

    def get_kpi_dict(self) -> Dict[str, Any]:
        """Returns the fully structured KPI dictionary for reporting."""
        return {
            'latency': self.calculate_latency_stats(),
            'throughput': self.calculate_throughput(),
            'errors': self.calculate_error_rate(),
            'concurrency': self.calculate_concurrency(),
            'duration': self.duration_seconds
        }
