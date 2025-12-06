# Copyright (c) 2025 Juan Estevez Castillo
# Licensed under AGPL v3. Commercial licenses available.
# See LICENSE or https://www.gnu.org/licenses/agpl-3.0.html

import pandas as pd
from typing import Dict, Any
from heimr.parsers.base import BaseParser


class JTLParser(BaseParser):
    """
    Parses JMeter JTL files (CSV format) into a pandas DataFrame.
    """

    def parse(self) -> pd.DataFrame:
        """
        Reads the JTL file and performs basic preprocessing.
        """
        try:
            # Read CSV
            self.df = pd.read_csv(self.filepath)

            # Convert timestamp to datetime
            if 'timeStamp' in self.df.columns:
                self.df['timestamp_dt'] = pd.to_datetime(self.df['timeStamp'], unit='ms')

            # Ensure numeric types for key metrics
            numeric_cols = ['elapsed', 'Latency', 'bytes', 'sentBytes', 'responseCode', 'allThreads', 'grpThreads']
            for col in numeric_cols:
                if col in self.df.columns:
                    self.df[col] = pd.to_numeric(self.df[col], errors='coerce')

            # Map JTL columns to Unified Schema
            # elapsed -> elapsed (already there)
            # responseCode -> response_code
            if 'responseCode' in self.df.columns:
                self.df['response_code'] = self.df['responseCode'].astype(str)
            else:
                self.df['response_code'] = '200'

            # bytes -> bytes_recv
            if 'bytes' in self.df.columns:
                self.df['bytes_recv'] = self.df['bytes']

            # sentBytes -> bytes_sent
            if 'sentBytes' in self.df.columns:
                self.df['bytes_sent'] = self.df['sentBytes']

            # allThreads -> vus
            if 'allThreads' in self.df.columns:
                self.df['vus'] = self.df['allThreads']
            elif 'grpThreads' in self.df.columns:
                self.df['vus'] = self.df['grpThreads']

            # endpoint/label
            if 'label' in self.df.columns:
                self.df['endpoint'] = self.df['label']

            # method (usually not in JTL, default to mixed/unknown)
            self.df['method'] = 'mixed'

            self.df = self._normalize_dataframe(self.df)
            return self.df
        except Exception as e:
            raise ValueError(f"Failed to parse JTL file: {e}")

    def get_summary_stats(self) -> Dict[str, Any]:
        """
        Returns basic statistics about the test run.
        """
        if self.df is None:
            raise ValueError("Data not parsed yet. Call parse() first.")

        stats = {
            'total_requests': len(self.df),
            'start_time': self.df['timestamp_dt'].min(),
            'end_time': self.df['timestamp_dt'].max(),
            'avg_latency': self.df['elapsed'].mean(),
            'p95_latency': self.df['elapsed'].quantile(0.95),
            'p99_latency': self.df['elapsed'].quantile(0.99),
            'error_rate': (1 - self.df['success'].mean()) * 100
        }
        return stats
