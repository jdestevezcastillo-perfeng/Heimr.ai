import unittest
from unittest.mock import patch, MagicMock
import sys
import os
from heimr.cli import main, load_config, merge_config_with_args

class TestCLI(unittest.TestCase):
    
    def test_merge_config_with_args(self):
        # Create a dummy args object
        class Args:
            def __init__(self):
                self.prometheus = None
                self.loki = None
                self.llm_url = None
                self.output = "cli_output.md"
        
        args = Args()
        config = {
            'prometheus': 'http://config:9090',
            'loki': 'http://config:3100',
            'output': 'config_output.md' # Should NOT override CLI arg
        }
        
        merged = merge_config_with_args(args, config)
        
        self.assertEqual(merged.prometheus, 'http://config:9090')
        self.assertEqual(merged.loki, 'http://config:3100')
        self.assertEqual(merged.output, 'cli_output.md') # CLI takes precedence

    @patch('heimr.cli.Analyzer')
    def test_analyze_command_passed(self, MockAnalyzer):
        # Setup Mock result
        mock_instance = MockAnalyzer.return_value
        result = MagicMock()
        result.status = "PASSED"
        result.kpi = {'duration': 10, 'throughput': {'total_requests': 100, 'requests_per_second': 10}, 
                      'errors': {'rate': 0}, 'latency': {'p50': 10, 'p95': 20, 'p99': 30, 'avg': 15},
                      'concurrency': {'max': 1, 'avg': 1}}
        result.anomaly_summary = {'count': 0}
        result.df.empty = False
        result.failure_signals = []
        
        mock_instance.analyze.return_value = result

        test_args = ['heimr', 'analyze', 'test.jtl', '--no-llm']
        with patch('sys.argv', test_args):
            try:
                main()
            except SystemExit as e:
                self.assertEqual(e.code, 0)
        
        MockAnalyzer.assert_called()
        call_kwargs = MockAnalyzer.call_args[1]
        self.assertEqual(call_kwargs['file_path'], 'test.jtl')
        self.assertTrue(call_kwargs['no_llm'])

    @patch('heimr.cli.Analyzer')
    def test_analyze_command_failed(self, MockAnalyzer):
        # Setup Mock result
        mock_instance = MockAnalyzer.return_value
        result = MagicMock()
        result.status = "FAILED" # Should exit 1
        result.kpi = {'duration': 10, 'throughput': {'total_requests': 100, 'requests_per_second': 10}, 
                      'errors': {'rate': 50}, 'latency': {'p50': 10, 'p95': 20, 'p99': 30, 'avg': 15},
                      'concurrency': {'max': 1, 'avg': 1}}
        result.anomaly_summary = {'count': 5, 'avg_latency': 500}
        result.df.empty = False
        result.failure_signals = ["Error Rate > 0"]
        
        mock_instance.analyze.return_value = result

        test_args = ['heimr', 'analyze', 'test.jtl']
        with patch('sys.argv', test_args):
            try:
                main()
            except SystemExit as e:
                self.assertEqual(e.code, 1)

if __name__ == '__main__':
    unittest.main()
