# Copyright (c) 2025 Juan Estevez Castillo
# Licensed under AGPL v3. Commercial licenses available.
# See LICENSE or https://www.gnu.org/licenses/agpl-3.0.html

import unittest
from heimr.comparator import PerformanceComparator


class TestPerformanceComparator(unittest.TestCase):
    """Tests for the PerformanceComparator class."""

    def setUp(self):
        """Create baseline and current stats for comparison."""
        self.baseline_stats = {
            'total_requests': 1000,
            'avg_latency': 100.0,
            'p95_latency': 200.0,
            'p99_latency': 300.0,
            'error_rate': 1.0,
            'throughput': 50.0
        }
        
        # Current with some regression (higher latency, higher errors)
        self.current_stats_regression = {
            'total_requests': 1000,
            'avg_latency': 150.0,  # 50% increase
            'p95_latency': 300.0,  # 50% increase
            'p99_latency': 450.0,  # 50% increase
            'error_rate': 3.0,     # 200% increase
            'throughput': 40.0     # 20% decrease
        }
        
        # Current with improvement
        self.current_stats_improvement = {
            'total_requests': 1200,
            'avg_latency': 80.0,   # 20% decrease
            'p95_latency': 150.0,
            'p99_latency': 250.0,
            'error_rate': 0.5,     # 50% decrease
            'throughput': 60.0     # 20% increase
        }

    def test_compare_metrics_regression(self):
        """Test detection of performance regression."""
        comparator = PerformanceComparator(self.baseline_stats, self.current_stats_regression)
        result = comparator.compare_metrics()
        
        # Should detect regressions
        self.assertIn('avg_latency', result)
        self.assertGreater(result['avg_latency']['pct_change'], 40)  # ~50% increase
        self.assertFalse(result['avg_latency']['improved'])  # 'improved' not 'is_improvement'
        
        self.assertIn('error_rate', result)
        self.assertGreater(result['error_rate']['pct_change'], 100)  # 200% increase
        
        self.assertIn('throughput', result)
        self.assertLess(result['throughput']['pct_change'], 0)  # Decrease

    def test_compare_metrics_improvement(self):
        """Test detection of performance improvement."""
        comparator = PerformanceComparator(self.baseline_stats, self.current_stats_improvement)
        result = comparator.compare_metrics()
        
        # Should detect improvements
        self.assertIn('avg_latency', result)
        self.assertLess(result['avg_latency']['pct_change'], 0)  # Decrease
        self.assertTrue(result['avg_latency']['improved'])
        
        self.assertIn('throughput', result)
        self.assertGreater(result['throughput']['pct_change'], 0)  # Increase
        self.assertTrue(result['throughput']['improved'])

    def test_compare_anomalies(self):
        """Test anomaly comparison."""
        baseline_anomalies = {'count': 5, 'avg_latency': 500}
        current_anomalies = {'count': 10, 'avg_latency': 600}
        
        comparator = PerformanceComparator(self.baseline_stats, self.current_stats_regression)
        result = comparator.compare_anomalies(baseline_anomalies, current_anomalies)
        
        # API uses 'delta' not 'count_change'
        self.assertIn('delta', result)
        self.assertEqual(result['delta'], 5)  # 10 - 5
        self.assertTrue(result['new_anomalies'])

    def test_check_failure_conditions_fail_on_regression(self):
        """Test failure condition with regression threshold."""
        comparator = PerformanceComparator(self.baseline_stats, self.current_stats_regression)
        metrics_comparison = comparator.compare_metrics()
        
        # Should fail with 10% regression threshold
        result = comparator.check_failure_conditions(
            metrics_comparison,
            fail_on_regression=10.0
        )
        
        self.assertTrue(result['failed'])
        self.assertGreater(len(result['reasons']), 0)

    def test_check_failure_conditions_pass(self):
        """Test failure condition with improvements (no regression threshold)."""
        comparator = PerformanceComparator(self.baseline_stats, self.current_stats_improvement)
        metrics_comparison = comparator.compare_metrics()
        
        # Without any fail conditions, should pass
        result = comparator.check_failure_conditions(
            metrics_comparison,
            fail_on_regression=None,
            fail_conditions=None
        )
        
        self.assertFalse(result['failed'])

    def test_check_failure_conditions_custom(self):
        """Test custom failure conditions."""
        comparator = PerformanceComparator(self.baseline_stats, self.current_stats_regression)
        metrics_comparison = comparator.compare_metrics()
        
        # Custom condition: p95 > 250
        result = comparator.check_failure_conditions(
            metrics_comparison,
            fail_conditions=['p95_latency > 250']
        )
        
        self.assertTrue(result['failed'])

    def test_calculate_verdict(self):
        """Test verdict calculation."""
        comparator = PerformanceComparator(self.baseline_stats, self.current_stats_regression)
        metrics = comparator.compare_metrics()
        # Build anomalies dict matching expected structure
        anomalies = {'delta': 5, 'new_anomalies': True}
        
        verdict = comparator._calculate_verdict(metrics, anomalies)
        
        # Verdict is a full message string, should indicate regression
        self.assertIsInstance(verdict, str)
        self.assertIn('REGRESSION', verdict)

    def test_generate_comparison_report(self):
        """Test Markdown report generation."""
        comparator = PerformanceComparator(self.baseline_stats, self.current_stats_regression)
        metrics = comparator.compare_metrics()
        anomalies = comparator.compare_anomalies({'count': 5}, {'count': 10})
        
        report = comparator.generate_comparison_report(metrics, anomalies)
        
        # Report should contain key sections
        self.assertIn('Performance Comparison', report)
        self.assertIn('Latency', report)
        self.assertIn('%', report)  # Percentage changes


if __name__ == '__main__':
    unittest.main()

