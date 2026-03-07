# Copyright (c) 2025 Juan Estevez Castillo
# Licensed under AGPL v3. Commercial licenses available.
# See LICENSE or https://www.gnu.org/licenses/agpl-3.0.html

import unittest
import os
import tempfile
import argparse
from heimr.cli import load_config, merge_config_with_args, normalize_config
from heimr.analyzer import Analyzer


class TestLoadConfig(unittest.TestCase):
    """Tests for the load_config function."""

    def setUp(self):
        """Set up test fixtures."""
        self.fixtures_dir = os.path.join(os.path.dirname(__file__), 'fixtures')
        self.config_file = os.path.join(self.fixtures_dir, 'config_sample.yaml')

    def test_load_valid_config(self):
        """Test loading a valid config file."""
        config = load_config(self.config_file)

        self.assertIsNotNone(config)
        self.assertEqual(config['prometheus_url'], 'http://localhost:9090')
        self.assertEqual(config['loki_url'], 'http://localhost:3100')
        self.assertEqual(config['llm_model'], 'qwen3.5:9b')

    def test_load_nonexistent_config_raises(self):
        """Test loading a non-existent config file raises FileNotFoundError."""
        with self.assertRaises(FileNotFoundError):
            load_config('/nonexistent/path/config.yaml')


class TestMergeConfigWithArgs(unittest.TestCase):
    """Tests for the merge_config_with_args function."""

    def test_cli_takes_precedence(self):
        """Test that CLI arguments override config file values."""
        # Create mock args object
        args = argparse.Namespace(
            prometheus='http://cli-prometheus:9090',
            loki=None,  # Not set via CLI
            output='cli_output.md'
        )
        
        config = {
            'prometheus_url': 'http://config-prometheus:9090',
            'loki_url': 'http://config-loki:3100',
            'output': 'config_output.md'
        }

        merge_config_with_args(args, config)

        # CLI should win for prometheus
        self.assertEqual(args.prometheus, 'http://cli-prometheus:9090')
        # Config should be used for loki (not set in CLI)
        self.assertEqual(args.loki, 'http://config-loki:3100')
        # CLI should win for output
        self.assertEqual(args.output, 'cli_output.md')


class TestNormalizeConfig(unittest.TestCase):
    def test_explain_false_disables_llm_and_normalizes_url(self):
        config = {
            "explain": False,
            "llm_url": "http://localhost:11434",
            "llm_model": "medium",
            "llm_timeout_sec": 30,
            "llm_max_retries": 1,
        }
        normalized = normalize_config(config)
        self.assertTrue(normalized["disable_llm"])
        self.assertEqual(normalized["llm_url"], "http://localhost:11434/v1")

    def test_no_llm_alias(self):
        config = {"no_llm": True}
        normalized = normalize_config(config)
        self.assertTrue(normalized["disable_llm"])


class TestInspector(unittest.TestCase):
    """Tests for Analyzer helpers."""

    def setUp(self):
        """Create temporary test files."""
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up temp files."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_detect_jtl_by_extension(self):
        """Test JTL parser detection by extension."""
        filepath = os.path.join(self.temp_dir, 'test.jtl')
        with open(filepath, 'w') as f:
            f.write('timeStamp,elapsed,label\n')

        fmt = Analyzer.detect_file_format(filepath)
        self.assertEqual(fmt, 'jtl')

    def test_detect_json_for_k6(self):
        """Test K6 parser detection for .json files."""
        filepath = os.path.join(self.temp_dir, 'test.json')
        with open(filepath, 'w') as f:
            f.write('{"type":"Point"}\n')

        fmt = Analyzer.detect_file_format(filepath)
        self.assertEqual(fmt, 'k6')

    def test_detect_csv_for_locust(self):
        """Test Locust parser detection for stats_history files."""
        filepath = os.path.join(self.temp_dir, 'stats_history.csv')
        with open(filepath, 'w') as f:
            f.write('Timestamp,User Count\n')

        fmt = Analyzer.detect_file_format(filepath)
        self.assertEqual(fmt, 'locust')

    def test_parse_url(self):
        """Test URL parsing helper."""
        url, filepath = Analyzer.parse_url_or_file('http://localhost:9090')
        self.assertEqual(url, 'http://localhost:9090')
        self.assertIsNone(filepath)

    def test_parse_file_path(self):
        """Test file path parsing helper."""
        url, filepath = Analyzer.parse_url_or_file('/path/to/metrics.json')
        self.assertIsNone(url)
        self.assertEqual(filepath, '/path/to/metrics.json')


if __name__ == '__main__':
    unittest.main()
