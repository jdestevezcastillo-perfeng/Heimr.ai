import unittest
import pandas as pd
import datetime
from heimr.kpi import KPIEngine

class TestKPIEngine(unittest.TestCase):
    def setUp(self):
        # Create a sample DataFrame conforming to UnifiedSchema
        self.data = {
            'timestamp_dt': [
                datetime.datetime(2023, 1, 1, 10, 0, 0),
                datetime.datetime(2023, 1, 1, 10, 0, 1),
                datetime.datetime(2023, 1, 1, 10, 0, 2),
                datetime.datetime(2023, 1, 1, 10, 0, 3)
            ],
            'elapsed': [100.0, 200.0, 800.0, 1200.0],
            'success': [True, True, True, False],
            'response_code': ['200', '200', '200', '500'],
            'endpoint': ['/api/v1/foo', '/api/v1/foo', '/api/v1/bar', '/api/v1/bar'],
            'bytes_recv': [1000, 2000, 1000, 500],
            'bytes_sent': [100, 100, 100, 100],
            'vus': [1, 5, 10, 5]
        }
        self.df = pd.DataFrame(self.data)
        self.kpi = KPIEngine(self.df)

    def test_latency_stats(self):
        stats = self.kpi.calculate_latency_stats()
        self.assertEqual(stats['min'], 100.0)
        self.assertEqual(stats['max'], 1200.0)
        self.assertEqual(stats['p50'], 500.0) # (200+800)/2
        self.assertAlmostEqual(stats['avg'], 575.0)

    def test_throughput(self):
        tp = self.kpi.calculate_throughput()
        self.assertEqual(tp['total_requests'], 4)
        # Duration is 3 seconds (10:00:00 to 10:00:03)
        self.assertAlmostEqual(tp['requests_per_second'], 4/3)

    def test_error_rate(self):
        err = self.kpi.calculate_error_rate()
        self.assertEqual(err['count'], 1)
        self.assertEqual(err['rate'], 25.0)
        self.assertEqual(err['classification']['http_5xx'], 1)



    def test_concurrency(self):
        conc = self.kpi.calculate_concurrency()
        self.assertEqual(conc['max'], 10)
        self.assertEqual(conc['avg'], 5.2) # (1+5+10+5)/4 = 5.25 -> 5.2

if __name__ == '__main__':
    unittest.main()
