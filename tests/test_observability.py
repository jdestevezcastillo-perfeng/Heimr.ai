# Copyright (c) 2025 Juan Estevez Castillo
# Licensed under AGPL v3. Commercial licenses available.
# See LICENSE or https://www.gnu.org/licenses/agpl-3.0.html

import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime
from heimr.loki import LokiClient
from heimr.tempo import TempoClient
from heimr.llm import LLMClient

class TestObservability(unittest.TestCase):

    @patch('heimr.loki.requests.get')
    def test_loki_client(self, mock_get):
        # Mock Loki response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'status': 'success',
            'data': {
                'result': [
                    {
                        'stream': {'app': 'test'},
                        'values': [['1600000000000000000', 'Error: Something went wrong']]
                    }
                ]
            }
        }
        mock_get.return_value = mock_response

        client = LokiClient("http://loki:3100")
        logs = client.query_logs('{app="test"}', datetime.now(), datetime.now())
        
        self.assertEqual(len(logs), 1)
        self.assertEqual(logs[0]['line'], 'Error: Something went wrong')

    @patch('heimr.tempo.requests.get')
    def test_tempo_client(self, mock_get):
        # Mock Tempo response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'traces': [
                {'traceID': 'abc1234', 'duration': 1500}
            ]
        }
        mock_get.return_value = mock_response

        client = TempoClient("http://tempo:3200")
        traces = client.query_traces(min_duration="1000ms")
        
        self.assertEqual(len(traces), 1)
        self.assertEqual(traces[0]['traceID'], 'abc1234')

    def test_llm_prompt_construction(self):
        client = LLMClient(provider="mock")
        stats = {'total_requests': 100, 'avg_latency': 50, 'p99_latency': 100, 'error_rate': 0}
        anomalies = {'count': 0}
        
        loki_logs = ["Error: DB Connection Failed"]
        tempo_traces = [{'traceID': '123', 'duration': 2000}]
        
        # Access private method for testing
        prompt = client._construct_prompt(stats, anomalies, loki_logs=loki_logs, tempo_traces=tempo_traces)
        
        self.assertIn("Error Logs (Sample):", prompt)
        self.assertIn("- Error: DB Connection Failed", prompt)
        self.assertIn("Slow Traces (Sample):", prompt)
        self.assertIn("TraceID: 123", prompt)

if __name__ == '__main__':
    unittest.main()
