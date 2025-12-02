import pandas as pd
from pyod.models.iforest import IForest
from typing import List, Dict

class AnomalyDetector:
    """
    Detects anomalies in load test metrics using PyOD.
    """
    def __init__(self, df: pd.DataFrame):
        self.df = df
        self.model = IForest(contamination=0.05, random_state=42)

    def detect_latency_anomalies(self) -> pd.DataFrame:
        """
        Detects anomalies in the 'elapsed' (latency) column.
        Returns a DataFrame containing only the anomalous rows.
        """
        if 'elapsed' not in self.df.columns:
            raise ValueError("DataFrame missing 'elapsed' column")

        # Prepare data for PyOD (requires 2D array)
        X = self.df[['elapsed']].values

        # Fit and predict
        self.model.fit(X)
        y_pred = self.model.predict(X)  # 1 for outlier, 0 for inlier

        # Add prediction to DataFrame
        self.df['is_anomaly'] = y_pred
        
        # Filter anomalies
        anomalies = self.df[self.df['is_anomaly'] == 1].copy()
        return anomalies

    def get_anomaly_summary(self, anomalies: pd.DataFrame) -> Dict:
        """
        Returns summary stats of the detected anomalies.
        """
        if anomalies.empty:
            return {"count": 0, "message": "No anomalies detected"}
        
        return {
            "count": len(anomalies),
            "avg_latency": anomalies['elapsed'].mean(),
            "min_latency": anomalies['elapsed'].min(),
            "max_latency": anomalies['elapsed'].max(),
            "timestamps": anomalies['timestamp_dt'].astype(str).tolist()
        }
