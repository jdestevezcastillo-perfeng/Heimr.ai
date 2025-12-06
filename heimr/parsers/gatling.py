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
                        # Ensure status is string
                        status = str(status)
                        
                        row = {
                            'timestamp_dt': pd.to_datetime(end_ts, unit='ms'),
                            'elapsed': float(end_ts - start_ts),
                            'success': status == 'OK',
                            'response_code': '200' if status == 'OK' else '500', # Simplified, Gatling log might have more info
                            'endpoint': parts[3] if len(parts) > 3 else 'unknown', # RequestName
                            'method': 'mixed', # Not typically available in standard Gatling simulation.log
                            'bytes_recv': 0.0,
                            'bytes_sent': 0.0,
                            'vus': int(parts[2]) if parts[2].isdigit() else 1 # UserID often numeric, but treat as 1 if not
                        }
                        data.append(row)

            self.df = pd.DataFrame(data)
            self.df = self._normalize_dataframe(self.df)
            return self.df
        except Exception as e:
            raise ValueError(f"Failed to parse Gatling log file: {e}")


