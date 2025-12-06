# Copyright (c) 2025 Juan Estevez Castillo
# Licensed under AGPL v3. Commercial licenses available.
# See LICENSE or https://www.gnu.org/licenses/agpl-3.0.html

import unittest
import os
from heimr.parsers.har import HARParser
from heimr.parsers.locust import LocustParser


class TestHARParser(unittest.TestCase):
    """Tests for the HARParser class."""

    def setUp(self):
        """Set up test fixtures."""
        self.fixtures_dir = os.path.join(os.path.dirname(__file__), 'fixtures')
        self.har_file = os.path.join(self.fixtures_dir, 'sample.har')

    def test_parse_har_file(self):
        """Test parsing a HAR file."""
        parser = HARParser(self.har_file)
        df = parser.parse()

        # Should have 5 entries from fixture
        self.assertEqual(len(df), 5)

        # Check required columns exist
        required_cols = ['timestamp_dt', 'elapsed', 'success', 'response_code',
                         'bytes_recv', 'bytes_sent', 'vus', 'endpoint', 'method']
        for col in required_cols:
            self.assertIn(col, df.columns)

    def test_har_success_detection(self):
        """Test success/failure detection from status codes."""
        parser = HARParser(self.har_file)
        df = parser.parse()

        # 200, 201, 200 = success, 404, 500 = failure
        success_count = df['success'].sum()
        self.assertEqual(success_count, 3)

    def test_har_response_codes(self):
        """Test response code extraction."""
        parser = HARParser(self.har_file)
        df = parser.parse()

        # Should have mix of response codes
        codes = df['response_code'].unique().tolist()
        self.assertIn(200, codes)
        self.assertIn(404, codes)
        self.assertIn(500, codes)

    def test_har_endpoints(self):
        """Test endpoint extraction from URLs."""
        parser = HARParser(self.har_file)
        df = parser.parse()

        endpoints = df['endpoint'].unique().tolist()
        self.assertIn('/api/users', endpoints)
        self.assertIn('/api/health', endpoints)

    def test_har_summary_stats(self):
        """Test summary statistics generation."""
        parser = HARParser(self.har_file)
        parser.parse()
        stats = parser.get_summary_stats()

        self.assertEqual(stats['total_requests'], 5)
        self.assertGreater(stats['avg_latency'], 0)
        # 2 failures out of 5 = 40% error rate
        self.assertAlmostEqual(stats['error_rate'], 40.0, places=1)

    def test_har_metadata(self):
        """Test metadata extraction."""
        parser = HARParser(self.har_file)
        metadata = parser.get_metadata(self.har_file)

        self.assertEqual(metadata['version'], '1.2')
        self.assertEqual(metadata['creator'], 'TestHARGenerator')
        self.assertEqual(metadata['entries'], 5)


class TestLocustParser(unittest.TestCase):
    """Tests for the LocustParser class."""

    def setUp(self):
        """Set up test fixtures."""
        self.fixtures_dir = os.path.join(os.path.dirname(__file__), 'fixtures')
        self.locust_file = os.path.join(self.fixtures_dir, 'locust_stats.csv')

    def test_parse_locust_file(self):
        """Test parsing a Locust stats_history.csv file."""
        parser = LocustParser(self.locust_file)
        df = parser.parse()

        # Should have 6 rows from fixture
        self.assertEqual(len(df), 6)

        # Check required columns exist
        required_cols = ['timestamp_dt', 'elapsed', 'success', 'vus', 'endpoint']
        for col in required_cols:
            self.assertIn(col, df.columns)

    def test_locust_response_time(self):
        """Test response time extraction."""
        parser = LocustParser(self.locust_file)
        df = parser.parse()

        # Elapsed should be populated from Total Average Response Time
        self.assertGreater(df['elapsed'].mean(), 0)
        self.assertLess(df['elapsed'].mean(), 300)  # Our fixture has ~100-200ms

    def test_locust_vus(self):
        """Test VUS extraction."""
        parser = LocustParser(self.locust_file)
        df = parser.parse()

        # VUS ranges from 10-20 in fixture
        self.assertGreaterEqual(df['vus'].min(), 10)
        self.assertLessEqual(df['vus'].max(), 20)

    def test_locust_summary_stats(self):
        """Test summary statistics generation."""
        parser = LocustParser(self.locust_file)
        parser.parse()
        stats = parser.get_summary_stats()

        self.assertEqual(stats['total_requests'], 6)
        self.assertGreater(stats['avg_latency'], 0)


if __name__ == '__main__':
    unittest.main()
