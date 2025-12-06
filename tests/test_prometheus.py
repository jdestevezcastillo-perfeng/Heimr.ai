# Copyright (c) 2025 Juan Estevez Castillo
# Licensed under AGPL v3. Commercial licenses available.
# See LICENSE or https://www.gnu.org/licenses/agpl-3.0.html

import unittest
import os
from unittest.mock import patch, MagicMock
from datetime import datetime
from heimr.prometheus import PrometheusClient


class TestPrometheusClient(unittest.TestCase):
    """Tests for the PrometheusClient class."""

    def setUp(self):
        """Set up test fixtures."""
        self.fixtures_dir = os.path.join(os.path.dirname(__file__), 'fixtures')
        self.metrics_file = os.path.join(self.fixtures_dir, 'prometheus_metrics.json')

    @patch('heimr.prometheus.requests.get')
    def test_query_metric_success(self, mock_get):
        """Test successful metric query."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'status': 'success',
            'data': {
                'result': [
                    {
                        'metric': {'job': 'test'},
                        'values': [[1704067200, '0.5'], [1704067215, '0.6']]
                    }
                ]
            }
        }
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        client = PrometheusClient('http://localhost:9090')
        result = client.query_metric(
            'rate(cpu[1m])',
            datetime(2024, 1, 1, 10, 0, 0),
            datetime(2024, 1, 1, 10, 10, 0)
        )

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['metric']['job'], 'test')
        self.assertEqual(len(result[0]['values']), 2)

    @patch('heimr.prometheus.requests.get')
    def test_query_metric_failure(self, mock_get):
        """Test failed metric query."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'status': 'error',
            'error': 'invalid query'
        }
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        client = PrometheusClient('http://localhost:9090')
        result = client.query_metric(
            'invalid{',
            datetime(2024, 1, 1, 10, 0, 0),
            datetime(2024, 1, 1, 10, 10, 0)
        )

        self.assertEqual(result, [])

    @patch('heimr.prometheus.requests.get')
    def test_query_metric_exception(self, mock_get):
        """Test exception handling in query."""
        mock_get.side_effect = Exception('Connection refused')

        client = PrometheusClient('http://localhost:9090')
        result = client.query_metric(
            'up',
            datetime(2024, 1, 1, 10, 0, 0),
            datetime(2024, 1, 1, 10, 10, 0)
        )

        self.assertEqual(result, [])

    @patch('heimr.prometheus.requests.get')
    def test_get_system_metrics(self, mock_get):
        """Test fetching system metrics."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'status': 'success',
            'data': {'result': [{'metric': {'job': 'test'}, 'values': []}]}
        }
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        client = PrometheusClient('http://localhost:9090')
        metrics = client.get_system_metrics(
            datetime(2024, 1, 1, 10, 0, 0),
            datetime(2024, 1, 1, 10, 10, 0)
        )

        self.assertIn('cpu_usage', metrics)
        self.assertIn('memory_usage', metrics)

    def test_file_path_mode(self):
        """Test loading metrics from local file."""
        client = PrometheusClient('http://localhost:9090', file_path=self.metrics_file)
        metrics = client.get_system_metrics(
            datetime(2024, 1, 1, 10, 0, 0),
            datetime(2024, 1, 1, 10, 10, 0)
        )

        self.assertIn('cpu_usage', metrics)
        self.assertIn('memory_usage', metrics)
        # Verify actual data from fixture
        self.assertEqual(len(metrics['cpu_usage']), 1)
        self.assertEqual(len(metrics['cpu_usage'][0]['values']), 4)


if __name__ == '__main__':
    unittest.main()
