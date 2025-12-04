# Copyright (c) 2025 Juan Estevez Castillo
# Licensed under AGPL v3. Commercial licenses available.
# See LICENSE or https://www.gnu.org/licenses/agpl-3.0.html

import unittest
import pandas as pd
import numpy as np
from heimr.detector import AnomalyDetector

class TestDetector(unittest.TestCase):
    def setUp(self):
        # Create synthetic data with a clear anomaly
        # 100 normal points around 100ms
        normal_data = np.random.normal(100, 10, 100)
        # 5 anomalous points around 1000ms
        anomaly_data = np.random.normal(1000, 10, 5)
        
        elapsed = np.concatenate([normal_data, anomaly_data])
        timestamps = pd.date_range(start='2022-01-01', periods=105, freq='1s')
        
        self.df = pd.DataFrame({
            'timestamp_dt': timestamps,
            'elapsed': elapsed
        })

    def test_anomaly_detection(self):
        detector = AnomalyDetector(self.df)
        anomalies = detector.detect_latency_anomalies()
        summary = detector.get_anomaly_summary(anomalies)
        
        # Should detect roughly 5 anomalies (might vary slightly due to random forest nature)
        self.assertGreaterEqual(summary['count'], 3)
        self.assertLessEqual(summary['count'], 7)
        
        # Average anomaly latency should be high
        self.assertGreater(summary['avg_latency'], 800)

if __name__ == '__main__':
    unittest.main()
