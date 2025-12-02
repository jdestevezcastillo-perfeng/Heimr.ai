import unittest
import pandas as pd
import os
from heimr.parsers.jtl import JTLParser
from heimr.parsers.k6 import K6Parser
from heimr.parsers.gatling import GatlingParser

class TestParsers(unittest.TestCase):
    def setUp(self):
        # Create dummy files
        self.jtl_file = "test.jtl"
        with open(self.jtl_file, "w") as f:
            f.write("timeStamp,elapsed,label,responseCode,responseMessage,threadName,dataType,success,failureMessage,bytes,sentBytes,grpThreads,allThreads,URL,Latency,IdleTime,Connect\n")
            f.write("1641024000000,100,HTTP Request,200,OK,Thread Group 1-1,text,true,,1024,512,1,1,http://example.com,90,0,10\n")
            f.write("1641024001000,200,HTTP Request,500,Internal Server Error,Thread Group 1-1,text,false,Error,1024,512,1,1,http://example.com,190,0,10\n")

        self.k6_file = "test.json"
        with open(self.k6_file, "w") as f:
            f.write('{"type":"Point","data":{"time":"2022-01-01T00:00:00.000Z","value":100,"tags":{"status":"200"}},"metric":"http_req_duration"}\n')
            f.write('{"type":"Point","data":{"time":"2022-01-01T00:00:01.000Z","value":200,"tags":{"status":"500"}},"metric":"http_req_duration"}\n')

        self.gatling_file = "test.log"
        with open(self.gatling_file, "w") as f:
            f.write("RUN\tsim\tuser\t1641024000000\t3.9.5\n")
            f.write("REQUEST\tScenario1\t1\tRequest1\t1641024000000\t1641024000100\tOK\n")
            f.write("REQUEST\tScenario1\t2\tRequest1\t1641024001000\t1641024001200\tKO\n")

    def tearDown(self):
        # Clean up
        if os.path.exists(self.jtl_file): os.remove(self.jtl_file)
        if os.path.exists(self.k6_file): os.remove(self.k6_file)
        if os.path.exists(self.gatling_file): os.remove(self.gatling_file)

    def test_jtl_parser(self):
        parser = JTLParser(self.jtl_file)
        df = parser.parse()
        stats = parser.get_summary_stats()
        
        self.assertEqual(len(df), 2)
        self.assertEqual(stats['total_requests'], 2)
        self.assertAlmostEqual(stats['avg_latency'], 150.0)
        self.assertAlmostEqual(stats['error_rate'], 50.0)

    def test_k6_parser(self):
        parser = K6Parser(self.k6_file)
        df = parser.parse()
        stats = parser.get_summary_stats()
        
        self.assertEqual(len(df), 2)
        self.assertEqual(stats['total_requests'], 2)
        self.assertAlmostEqual(stats['avg_latency'], 150.0)
        self.assertAlmostEqual(stats['error_rate'], 50.0)

    def test_gatling_parser(self):
        parser = GatlingParser(self.gatling_file)
        df = parser.parse()
        stats = parser.get_summary_stats()
        
        self.assertEqual(len(df), 2)
        self.assertEqual(stats['total_requests'], 2)
        self.assertAlmostEqual(stats['avg_latency'], 150.0)
        self.assertAlmostEqual(stats['error_rate'], 50.0)

if __name__ == '__main__':
    unittest.main()
