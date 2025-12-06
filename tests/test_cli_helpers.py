# Copyright (c) 2025 Juan Estevez Castillo
# Licensed under AGPL v3. Commercial licenses available.
# See LICENSE or https://www.gnu.org/licenses/agpl-3.0.html

import unittest
import os
import tempfile
import argparse
from heimr.cli import load_config, merge_config_with_args, get_parser, parse_url_or_file


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
        self.assertEqual(config['llm_model'], 'qwen2.5:7b')

    def test_load_nonexistent_config_raises(self):
        """Test loading a non-existent config file raises FileNotFoundError."""
        with self.assertRaises(FileNotFoundError):
            load_config('/nonexistent/path/config.yaml')

    def test_load_empty_path_raises(self):
        """Test loading with empty path raises FileNotFoundError."""
        with self.assertRaises(FileNotFoundError):
            load_config('')


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


class TestGetParser(unittest.TestCase):
    """Tests for the get_parser function."""

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

        parser = get_parser(filepath)
        self.assertEqual(parser.__class__.__name__, 'JTLParser')

    def test_detect_json_for_k6(self):
        """Test K6 parser detection for .json files."""
        filepath = os.path.join(self.temp_dir, 'test.json')
        with open(filepath, 'w') as f:
            f.write('{"type":"Point"}\n')

        parser = get_parser(filepath)
        self.assertEqual(parser.__class__.__name__, 'K6Parser')

    def test_detect_csv_for_locust(self):
        """Test Locust parser detection for stats_history files."""
        filepath = os.path.join(self.temp_dir, 'stats_history.csv')
        with open(filepath, 'w') as f:
            f.write('Timestamp,User Count\n')

        parser = get_parser(filepath)
        self.assertEqual(parser.__class__.__name__, 'LocustParser')

    def test_explicit_format_arg(self):
        """Test that format_arg overrides detection."""
        filepath = os.path.join(self.temp_dir, 'test.json')
        with open(filepath, 'w') as f:
            f.write('{}')

        # Force JTL format even for .json file
        parser = get_parser(filepath, format_arg='jtl')
        self.assertEqual(parser.__class__.__name__, 'JTLParser')


class TestParseUrlOrFile(unittest.TestCase):
    """Tests for the parse_url_or_file function."""

    def test_parse_url(self):
        """Test URL detection."""
        url, filepath = parse_url_or_file('http://localhost:9090')
        
        self.assertEqual(url, 'http://localhost:9090')
        self.assertIsNone(filepath)

    def test_parse_https_url(self):
        """Test HTTPS URL detection."""
        url, filepath = parse_url_or_file('https://prometheus.example.com')
        
        self.assertEqual(url, 'https://prometheus.example.com')
        self.assertIsNone(filepath)

    def test_parse_file_path(self):
        """Test file path detection."""
        url, filepath = parse_url_or_file('/path/to/metrics.json')
        
        self.assertIsNone(url)
        self.assertEqual(filepath, '/path/to/metrics.json')

    def test_parse_relative_file_path(self):
        """Test relative file path detection."""
        url, filepath = parse_url_or_file('./data/metrics.json')
        
        self.assertIsNone(url)
        self.assertEqual(filepath, './data/metrics.json')


if __name__ == '__main__':
    unittest.main()

