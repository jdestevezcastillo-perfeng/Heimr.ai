# Copyright (c) 2025 Juan Estevez Castillo
# Licensed under AGPL v3. Commercial licenses available.
# See LICENSE or https://www.gnu.org/licenses/agpl-3.0.html

import unittest
import os
import tempfile
import xml.etree.ElementTree as ET
from heimr.reporters.junit import JUnitReporter
from heimr.reporters.github import GitHubReporter


class TestJUnitReporter(unittest.TestCase):
    """Tests for the JUnitReporter class."""

    def setUp(self):
        """Set up test data."""
        self.stats = {
            'total_requests': 1000,
            'avg_latency': 150.0,
            'p50_latency': 120.0,
            'p95_latency': 250.0,
            'p99_latency': 400.0,
            'error_rate': 2.5,
            'throughput': 50.0
        }
        self.anomaly_summary = {
            'count': 15,
            'avg_latency': 800.0,
            'max_latency': 1200.0
        }

    def test_generate_junit_xml(self):
        """Test JUnit XML generation."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False) as f:
            output_path = f.name

        try:
            reporter = JUnitReporter(output_path=output_path)
            reporter.generate_report(
                stats=self.stats,
                anomalies=self.anomaly_summary,
                failure_reasons=None
            )

            # Verify file was created
            self.assertTrue(os.path.exists(output_path))

            # Parse and validate XML structure
            tree = ET.parse(output_path)
            root = tree.getroot()

            # Check root element
            self.assertEqual(root.tag, 'testsuites')

            # Should have testsuite element
            testsuite = root.find('testsuite')
            self.assertIsNotNone(testsuite)
            self.assertEqual(testsuite.get('name'), 'Heimr Performance Analysis')

            # Should have test cases
            testcases = testsuite.findall('testcase')
            self.assertGreaterEqual(len(testcases), 3)

        finally:
            if os.path.exists(output_path):
                os.remove(output_path)

    def test_junit_with_failures(self):
        """Test JUnit XML with failed tests."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False) as f:
            output_path = f.name

        try:
            reporter = JUnitReporter(output_path=output_path)
            reporter.generate_report(
                stats=self.stats,
                anomalies=self.anomaly_summary,
                failure_reasons=['p95 exceeded threshold: 250ms > 200ms', 'Error rate too high']
            )

            # Parse and check for failures
            tree = ET.parse(output_path)
            root = tree.getroot()

            testsuite = root.find('testsuite')
            failures = testsuite.get('failures', '0')
            self.assertEqual(failures, '2')

        finally:
            if os.path.exists(output_path):
                os.remove(output_path)

    def test_junit_with_tags(self):
        """Test JUnit XML with context tags."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False) as f:
            output_path = f.name

        try:
            reporter = JUnitReporter(output_path=output_path)
            reporter.generate_report(
                stats=self.stats,
                anomalies=self.anomaly_summary,
                tags={'commit': 'abc123', 'branch': 'main'}
            )

            # Parse and check properties
            tree = ET.parse(output_path)
            root = tree.getroot()

            testsuite = root.find('testsuite')
            properties = testsuite.find('properties')
            self.assertIsNotNone(properties)

            # Check that tags are in properties
            prop_names = [p.get('name') for p in properties.findall('property')]
            self.assertIn('commit', prop_names)
            self.assertIn('branch', prop_names)

        finally:
            if os.path.exists(output_path):
                os.remove(output_path)


class TestGitHubReporter(unittest.TestCase):
    """Tests for the GitHubReporter class."""

    def setUp(self):
        """Set up test data."""
        self.stats = {
            'total_requests': 1000,
            'avg_latency': 150.0,
            'p50_latency': 120.0,
            'p95_latency': 250.0,
            'p99_latency': 400.0,
            'error_rate': 2.5,
            'throughput': 50.0
        }
        self.anomaly_summary = {
            'count': 15,
            'avg_latency': 800.0
        }

    def test_generate_summary_no_output(self):
        """Test that generate_summary handles missing output path gracefully."""
        # No output path set, should return without error
        reporter = GitHubReporter(output_path=None)
        # This should not raise an exception
        reporter.generate_summary(
            stats=self.stats,
            anomalies=self.anomaly_summary
        )

    def test_generate_summary_to_file(self):
        """Test GitHub summary generation to file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            output_path = f.name

        try:
            reporter = GitHubReporter(output_path=output_path)
            reporter.generate_summary(
                stats=self.stats,
                anomalies=self.anomaly_summary
            )

            # Read content
            with open(output_path, 'r') as f:
                content = f.read()

            # Should contain key elements
            self.assertIn('Heimr', content)
            self.assertIn('P95', content)
            self.assertIn('Error Rate', content)

        finally:
            if os.path.exists(output_path):
                os.remove(output_path)

    def test_summary_with_failures(self):
        """Test summary with failure reasons."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            output_path = f.name

        try:
            reporter = GitHubReporter(output_path=output_path)
            reporter.generate_summary(
                stats=self.stats,
                anomalies=self.anomaly_summary,
                failure_reasons=['p95 exceeded threshold']
            )

            with open(output_path, 'r') as f:
                content = f.read()

            # Should indicate failure
            self.assertIn('Failed', content)
            self.assertIn('threshold', content)

        finally:
            if os.path.exists(output_path):
                os.remove(output_path)


if __name__ == '__main__':
    unittest.main()

