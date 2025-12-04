# Copyright (c) 2025 Juan Estevez Castillo
# Licensed under AGPL v3. Commercial licenses available.
# See LICENSE or https://www.gnu.org/licenses/agpl-3.0.html

import pandas as pd
import json
from typing import Dict, Any
from heimr.parsers.base import BaseParser

class K6Parser(BaseParser):
    """
    Parses k6 JSON output files into a pandas DataFrame.
    Expects k6 output generated with `k6 run --out json=results.json`.
    """
    def parse(self) -> pd.DataFrame:
        """
        Reads the k6 JSON file and maps metrics to the internal schema.
        """
        try:
            data = []
            with open(self.filepath, 'r') as f:
                for line in f:
                    try:
                        entry = json.loads(line)
                        if entry['type'] == 'Point' and entry['metric'] == 'http_req_duration':
                            # k6 'http_req_duration' is the total time for the request
                            status = int(entry['data']['tags'].get('status', 200))
                            row = {
                                'timestamp_dt': pd.to_datetime(entry['data']['time']),
                                'elapsed': entry['data']['value'], # ms
                                'success': status < 400,
                                'responseCode': status
                            }
                            data.append(row)
                    except json.JSONDecodeError:
                        continue

            self.df = pd.DataFrame(data)
            return self.df
        except Exception as e:
            raise ValueError(f"Failed to parse k6 JSON file: {e}")

    def get_summary_stats(self) -> Dict[str, Any]:
        """
        Returns basic statistics about the test run.
        """
        if self.df is None or self.df.empty:
             return {
                'total_requests': 0,
                'avg_latency': 0,
                'error_rate': 0
            }
        
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
