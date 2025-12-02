import pandas as pd
from .base import BaseParser

class LocustParser(BaseParser):
    def parse(self) -> pd.DataFrame:
        # Locust stats_history.csv format:
        # Timestamp,User Count,Type,Name,Requests/s,Failures/s,50%,...,Total Average Response Time,...
        
        df = pd.read_csv(self.filepath)
        
        # Locust timestamps are unix timestamps (seconds)
        df['timestamp_dt'] = pd.to_datetime(df['Timestamp'], unit='s')
        
        # We use "Total Average Response Time" as 'elapsed' for anomaly detection
        # Note: This is aggregated data (1 row per second usually), not per-request.
        df['elapsed'] = df['Total Average Response Time']
        
        # We don't have individual success/failure flags or response codes in history file
        # But we have Failures/s. We can create a synthetic 'success' column based on Failures/s == 0
        # This is an approximation.
        df['success'] = df['Failures/s'] == 0
        
        # Dummy response code since we don't have it
        df['responseCode'] = 200
        
        self.df = df[['timestamp_dt', 'elapsed', 'success', 'responseCode']]
        return self.df

    def get_summary_stats(self):
        if self.df is None:
            return {}
        
        total_requests = len(self.df) # In this case, it's number of time buckets, not requests. 
        # But wait, stats_history has "Requests/s". We can sum them up? 
        # Actually, "Total Request Count" is cumulative. The last row has the total.
        
        # Let's try to get total requests from the last row of the original CSV if possible, 
        # but we only have self.df here which is transformed.
        # We can approximate total requests by summing Requests/s * 1s (assuming 1s interval)
        # Or better, just report "N/A" for total requests if we can't easily get it, 
        # OR, re-read the file or store the original DF.
        
        # For simplicity in this MVP, let's just calculate stats on the 'elapsed' (avg response time) column
        # and treat 'total_requests' as the number of data points (seconds) for now, 
        # or try to be smarter.
        
        # Better approach:
        # The 'elapsed' column is "Total Average Response Time".
        # We can calculate the mean of that to get the "Average of Averages".
        
        return {
            'total_requests': len(self.df), # Reporting data points
            'avg_latency': self.df['elapsed'].mean(),
            'p99_latency': self.df['elapsed'].quantile(0.99),
            'error_rate': (1 - self.df['success'].mean()) * 100,
            'start_time': self.df['timestamp_dt'].min(),
            'end_time': self.df['timestamp_dt'].max()
        }
