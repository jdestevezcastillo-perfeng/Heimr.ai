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
            numeric_cols = ['elapsed', 'Latency', 'bytes', 'sentBytes', 'responseCode']
            for col in numeric_cols:
                if col in self.df.columns:
                    self.df[col] = pd.to_numeric(self.df[col], errors='coerce')

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
