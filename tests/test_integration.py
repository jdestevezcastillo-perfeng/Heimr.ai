import unittest
import os
import shutil
import tempfile
from unittest.mock import MagicMock, patch
from heimr.analyzer import Analyzer, AnalysisResult

class TestAnalyzerIntegration(unittest.TestCase):
    def setUp(self):
        # Create a temporary directory
        self.test_dir = tempfile.mkdtemp()
        
        # Create a sample JTL file
        self.jtl_path = os.path.join(self.test_dir, "test.jtl")
        with open(self.jtl_path, "w") as f:
            f.write("timeStamp,elapsed,label,responseCode,responseMessage,threadName,dataType,success,failureMessage,bytes,sentBytes,grpThreads,allThreads,URL,Latency,IdleTime,Connect\n")
            # Normal requests
            for i in range(10):
                f.write(f"{1600000000000 + i*1000},100,home,200,OK,Thread-1,text,true,,1024,0,1,1,http://localhost/home,100,0,0\n")
            # Error request
            f.write(f"{1600000020000},500,api,500,Error,Thread-1,text,false,,1024,0,1,1,http://localhost/api,500,0,0\n")
            # High latency request (anomaly)
            f.write(f"{1600000030000},2000,api,200,OK,Thread-1,text,true,,1024,0,1,1,http://localhost/api,2000,0,0\n")

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_analyzer_basic_flow(self):
        """Test basic analysis without LLM or external services."""
        analyzer = Analyzer(self.jtl_path, no_llm=True)
        result = analyzer.analyze()
        
        self.assertIsInstance(result, AnalysisResult)
        self.assertFalse(result.df.empty)
        # 12 requests total
        self.assertEqual(len(result.df), 12)
        
        # Check KPI
        self.assertIn('throughput', result.kpi)
        self.assertEqual(result.stats['total_requests'], 12)
        self.assertEqual(result.stats['error_count'], 1)
        self.assertIn('per_endpoint', result.kpi)
        
        # Check Failure Signals (should fail due to error rate and anomalies)
        self.assertEqual(result.status, "FAILED")
        self.assertTrue(any("Error Rate" in s for s in result.failure_signals))
        self.assertTrue(any("Anomalies" in s for s in result.failure_signals))

    @patch('heimr.analyzer.LLMClient')
    def test_analyzer_with_llm(self, MockLLMClient):
        """Test analysis with mocked LLM."""
        # Setup Mock
        mock_llm = MockLLMClient.return_value
        mock_llm.provider = "mock"
        # Return a generator
        def mock_generator(*args, **kwargs):
            yield "This is a "
            yield "mocked explanation."
        
        mock_llm.generate_explanation.side_effect = mock_generator

        analyzer = Analyzer(self.jtl_path, no_llm=False, llm_url="http://mock", llm_model="test")
        
        # Test streaming callback
        chunks = []
        def callback(chunk):
            chunks.append(chunk)
            
        result = analyzer.analyze(stream_callback=callback)
        
        self.assertEqual(result.llm_explanation, "This is a mocked explanation.")
        self.assertEqual("".join(chunks), "This is a mocked explanation.")
        
        # Verify LLM was called with correct data
        mock_llm.generate_explanation.assert_called_once() 
        # Check that stats were passed
        call_args = mock_llm.generate_explanation.call_args
        self.assertEqual(call_args[0][0]['total_requests'], 12) # stats is first arg

    @patch('heimr.analyzer.PrometheusClient')
    def test_analyzer_with_prometheus(self, MockProm):
        """Test analysis with mocked Prometheus."""
        mock_prom = MockProm.return_value
        mock_prom.get_system_metrics.return_value = {
            'cpu_usage': [{'values': [[0, 0.9]]}] # 90% CPU
        }
        
        config = {'prometheus': 'http://localhost:9090'}
        analyzer = Analyzer(self.jtl_path, config=config, no_llm=True)
        
        result = analyzer.analyze()
        
        # Should detect high CPU
        self.assertIn('cpu_usage', result.prom_metrics)
        self.assertTrue(any("High CPU" in s for s in result.failure_signals))

    def test_fail_condition_single_run(self):
        analyzer = Analyzer(self.jtl_path, config={"fail_conditions": ["p99_latency > 1500"]}, no_llm=True)
        result = analyzer.analyze()
        self.assertEqual(result.status, "FAILED")
        self.assertTrue(any("Failure condition met" in s for s in result.failure_signals))

if __name__ == '__main__':
    unittest.main()
