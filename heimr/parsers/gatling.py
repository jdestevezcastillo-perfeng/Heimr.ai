# Copyright (c) 2025 Juan Estevez Castillo
# Licensed under AGPL v3. Commercial licenses available.
# See LICENSE or https://www.gnu.org/licenses/agpl-3.0.html

import pandas as pd
from typing import Dict, Any
from heimr.parsers.base import BaseParser


class GatlingParser(BaseParser):
    """
    Parses Gatling simulation.log files into a pandas DataFrame.
    """

    def parse(self) -> pd.DataFrame:
        """
        Reads the Gatling log file.
        Format: REQUEST <ScenarioName> <UserId> <RequestName> <StartTimestamp> <EndTimestamp> <Status> <Message>
        """
        try:
            data = []
            with open(self.filepath, 'r') as f:
                for line in f:
                    parts = line.strip().split('\t')
                    if len(parts) >= 7 and parts[0] == 'REQUEST':
                        # REQUEST record
                        # 0: REQUEST, 1: Scenario, 2: UserID, 3: RequestName, 4: Start, 5: End, 6: Status
                        start_ts = int(parts[4])
                        end_ts = int(parts[5])
                        status = parts[6] if len(parts) > 6 else 'OK'

                        row = {
                            'timestamp_dt': pd.to_datetime(end_ts, unit='ms'),
                            'elapsed': float(end_ts - start_ts),
                            'success': status == 'OK',
                            # Simplified - Gatling log might have more info
                            'response_code': '200' if status == 'OK' else '500',
                            'endpoint': parts[3] if len(parts) > 3 else 'unknown',  # RequestName
                            'method': 'mixed',  # Not typically available in standard Gatling simulation.log
                            'bytes_recv': 0.0,
                            'bytes_sent': 0.0,
                            # UserID often numeric, but treat as 1 if not
                            'vus': int(parts[2]) if parts[2].isdigit() else 1
                        }
                        data.append(row)

            self.df = pd.DataFrame(data)
            self.df = self._normalize_dataframe(self.df)
            return self.df
        except Exception as e:
            raise ValueError(f"Failed to parse Gatling log file: {e}")

    def get_summary_stats(self) -> Dict[str, Any]:
        """Returns basic statistics about the test run."""
        if self.df is None or self.df.empty:
            return {
                'total_requests': 0,
                'avg_latency': 0,
                'error_rate': 0
            }

        return {
            'total_requests': len(self.df),
            'start_time': self.df['timestamp_dt'].min(),
            'end_time': self.df['timestamp_dt'].max(),
            'avg_latency': self.df['elapsed'].mean(),
            'p95_latency': self.df['elapsed'].quantile(0.95),
            'p99_latency': self.df['elapsed'].quantile(0.99),
            'error_rate': (1 - self.df['success'].mean()) * 100
        }
