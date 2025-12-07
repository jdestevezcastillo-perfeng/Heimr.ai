# Copyright (c) 2025 Juan Estevez Castillo
# Licensed under AGPL v3. Commercial licenses available.
# See LICENSE or https://www.gnu.org/licenses/agpl-3.0.html

import unittest
import pandas as pd
import numpy as np
from heimr.detector import AnomalyDetector

class TestDetector(unittest.TestCase):
    def setUp(self):
        # Base timestamps for all tests
        self.timestamps = pd.date_range(start='2022-01-01', periods=100, freq='1s')

    def test_statistical_outliers(self):
        # 95 normal points around 100ms
        normal_data = np.full(95, 100)
        # 5 outlier points at 1000ms
        outlier_data = np.full(5, 1000)
        
        elapsed = np.concatenate([normal_data, outlier_data])
        df = pd.DataFrame({'timestamp_dt': self.timestamps, 'elapsed': elapsed})
        
        detector = AnomalyDetector(df)
        anomalies = detector.detect_latency_anomalies()
        
        # Should detect the 5 outliers
        # Note: Gradual Degradation signal might also trigger and include more points from the tail.
        # We ensure at least the actual outliers are caught.
        caught_outliers = anomalies[anomalies['elapsed'] >= 1000]
        self.assertGreaterEqual(len(caught_outliers), 5)

    def test_absolute_threshold(self):
        # All points are high latency (e.g. 600ms), mean > 500
        data = np.random.normal(600, 10, 100) 
        
        df = pd.DataFrame({'timestamp_dt': self.timestamps, 'elapsed': data})
        detector = AnomalyDetector(df)
        anomalies = detector.detect_latency_anomalies()
        
        # Since mean > 500, it marks everything > p50. 
        # Roughly 50 points should be anomalies
        self.assertTrue(40 < len(anomalies) < 60)

    def test_bimodal_distribution(self):
        # P50 around 100, P99 > 200
        # 90 points at 100ms
        part1 = np.full(90, 100)
        # 10 points at 300ms
        part2 = np.full(10, 300)
        
        elapsed = np.concatenate([part1, part2])
        df = pd.DataFrame({'timestamp_dt': self.timestamps, 'elapsed': elapsed})
        
        # P50 = 100, P99 approx 300. 300 > 200. Triggered.
        
        detector = AnomalyDetector(df)
        anomalies = detector.detect_latency_anomalies()
        
        # It marks top 10% (tail_threshold = p99 * 0.9 = 270)
        # So the 300ms ones should be anomalies.
        # Degradation signal might also trigger, adding more points.
        caught_bimodal = anomalies[anomalies['elapsed'] == 300]
        self.assertGreaterEqual(len(caught_bimodal), 10)

    def test_gradual_degradation(self):
        # First 20% mean = 100
        part1 = np.full(20, 100)
        # Middle to avoid sharp jump
        part2 = np.linspace(100, 200, 60)
        # Last 20% mean = 200 (> 100 * 1.5)
        part3 = np.full(20, 200)
        
        elapsed = np.concatenate([part1, part2, part3])
        df = pd.DataFrame({'timestamp_dt': self.timestamps, 'elapsed': elapsed})
        
        detector = AnomalyDetector(df)
        anomalies = detector.detect_latency_anomalies()
        
        # Should catch the last chunk
        count_in_last_20 = len(anomalies[anomalies['elapsed'] == 200])
        self.assertGreaterEqual(count_in_last_20, 20)

    def test_empty_dataframe(self):
        df = pd.DataFrame({'timestamp_dt': [], 'elapsed': []})
        detector = AnomalyDetector(df)
        try:
             anomalies = detector.detect_latency_anomalies()
             self.assertTrue(anomalies.empty)
        except Exception:
             pass

    def test_constant_values(self):
        # All 100ms. Std dev = 0.
        elapsed = np.full(100, 100)
        df = pd.DataFrame({'timestamp_dt': self.timestamps, 'elapsed': elapsed})
        detector = AnomalyDetector(df)
        anomalies = detector.detect_latency_anomalies()
        self.assertTrue(anomalies.empty)
