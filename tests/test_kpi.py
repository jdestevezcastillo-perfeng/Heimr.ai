# Copyright (c) 2025 Juan Estevez Castillo
# Licensed under AGPL v3. Commercial licenses available.
# See LICENSE or https://www.gnu.org/licenses/agpl-3.0.html

import unittest
import pandas as pd
import numpy as np
from heimr.kpi import KPIEngine


class TestKPIEngine(unittest.TestCase):
    """Tests for the KPIEngine class."""

    def setUp(self):
        """Create test data with known values."""
        # 10 requests over 10 seconds
        timestamps = pd.date_range(start='2024-01-01 10:00:00', periods=10, freq='1s')
        
        self.df = pd.DataFrame({
            'timestamp_dt': timestamps,
            'elapsed': [100, 150, 200, 120, 180, 90, 250, 300, 110, 500],  # Known latencies
            'success': [True, True, True, True, False, True, True, False, True, True],  # 2 failures
            'response_code': ['200', '200', '200', '200', '500', '200', '200', '404', '200', '200'],
            'bytes_recv': [1000, 1200, 1100, 1050, 500, 1000, 1500, 200, 900, 1000],
            'bytes_sent': [100, 150, 120, 110, 100, 100, 200, 50, 90, 100],
            'vus': [5, 5, 10, 10, 10, 15, 15, 15, 10, 5]
        })

    def test_latency_stats(self):
        """Test latency statistics calculation."""
        engine = KPIEngine(self.df)
        stats = engine.calculate_latency_stats()
        
        # Verify known values
        self.assertEqual(stats['min'], 90)
        self.assertEqual(stats['max'], 500)
        self.assertAlmostEqual(stats['avg'], 200.0, places=1)
        
        # Percentiles should be within expected range
        self.assertGreater(stats['p50'], 100)
        self.assertLess(stats['p50'], 250)
        self.assertGreater(stats['p95'], 250)
        self.assertGreater(stats['p99'], 300)

    def test_throughput(self):
        """Test throughput calculation."""
        engine = KPIEngine(self.df)
        stats = engine.calculate_throughput()
        
        self.assertEqual(stats['total_requests'], 10)
        # Duration is 9 seconds (10:00:00 to 10:00:09)
        # RPS should be ~10/9 ≈ 1.11
        self.assertGreater(stats['requests_per_second'], 1.0)
        self.assertLess(stats['requests_per_second'], 2.0)
        
        # Bytes should be positive
        self.assertGreater(stats['bytes_in_per_second'], 0)
        self.assertGreater(stats['bytes_out_per_second'], 0)

    def test_error_rate(self):
        """Test error rate and classification."""
        engine = KPIEngine(self.df)
        stats = engine.calculate_error_rate()
        
        # 2 out of 10 failed = 20%
        self.assertAlmostEqual(stats['rate'], 20.0, places=1)
        self.assertEqual(stats['count'], 2)
        
        # Classification
        self.assertEqual(stats['classification']['http_5xx'], 1)
        self.assertEqual(stats['classification']['http_4xx'], 1)
        self.assertEqual(stats['classification']['timeout'], 0)

    def test_concurrency(self):
        """Test VUS statistics."""
        engine = KPIEngine(self.df)
        stats = engine.calculate_concurrency()
        
        self.assertEqual(stats['max'], 15)
        self.assertEqual(stats['avg'], 10.0)

    def test_get_kpi_dict(self):
        """Test full KPI dictionary generation."""
        engine = KPIEngine(self.df)
        kpi = engine.get_kpi_dict()
        
        # All sections should exist
        self.assertIn('latency', kpi)
        self.assertIn('throughput', kpi)
        self.assertIn('errors', kpi)
        self.assertIn('concurrency', kpi)
        self.assertIn('duration', kpi)
        
        self.assertGreater(kpi['duration'], 0)

    def test_empty_dataframe(self):
        """Test handling of empty DataFrame."""
        empty_df = pd.DataFrame(columns=['timestamp_dt', 'elapsed', 'success', 
                                          'response_code', 'bytes_recv', 'bytes_sent', 'vus'])
        engine = KPIEngine(empty_df)
        
        latency = engine.calculate_latency_stats()
        self.assertEqual(latency['avg'], 0.0)
        
        throughput = engine.calculate_throughput()
        self.assertEqual(throughput['total_requests'], 0)
        
        errors = engine.calculate_error_rate()
        self.assertEqual(errors['rate'], 0.0)


if __name__ == '__main__':
    unittest.main()
