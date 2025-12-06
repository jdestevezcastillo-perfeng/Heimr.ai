# Copyright (c) 2025 Juan Estevez Castillo
# Licensed under AGPL v3. Commercial licenses available.
# See LICENSE or https://www.gnu.org/licenses/agpl-3.0.html

import unittest
import os
import pandas as pd
from heimr.parsers.har import HARParser

class TestHARParser(unittest.TestCase):
    """Test suite for HAR parser"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.fixture_dir = os.path.join(os.path.dirname(__file__), 'fixtures')
        self.sample_har = os.path.join(self.fixture_dir, 'sample.har')
    
    def test_parse_basic(self):
        """Test basic HAR parsing"""
        parser = HARParser(self.sample_har)
        df = parser.parse()
        
        # Verify DataFrame structure
        self.assertIsInstance(df, pd.DataFrame)
        self.assertFalse(df.empty)
        
        # Verify required columns exist
        required_cols = ['timestamp_dt', 'elapsed', 'success', 'response_code',
                        'bytes_recv', 'bytes_sent', 'vus', 'endpoint', 'method']
        for col in required_cols:
            self.assertIn(col, df.columns, f"Missing required column: {col}")
    
    def test_entry_count(self):
        """Test correct number of entries parsed"""
        parser = HARParser(self.sample_har)
        df = parser.parse()
        
        # Sample HAR has 5 entries
        self.assertEqual(len(df), 5)
    
    def test_timing_extraction(self):
        """Test timing data extraction"""
        parser = HARParser(self.sample_har)
        df = parser.parse()
        
        # First entry should have ~245.5ms elapsed time
        first_entry = df.iloc[0]
        self.assertAlmostEqual(first_entry['elapsed'], 245.5, places=1)
        
        # Slow endpoint should have ~5240.8ms
        slow_entry = df[df['endpoint'] == '/api/slow-endpoint'].iloc[0]
        self.assertAlmostEqual(slow_entry['elapsed'], 5240.8, places=1)
    
    def test_status_code_extraction(self):
        """Test HTTP status code extraction"""
        parser = HARParser(self.sample_har)
        df = parser.parse()
        
        # Check successful request
        users_entry = df[df['endpoint'] == '/api/users'].iloc[0]
        self.assertEqual(users_entry['response_code'], 200)
        self.assertTrue(users_entry['success'])
        
        # Check error request
        error_entry = df[df['endpoint'] == '/api/slow-endpoint'].iloc[0]
        self.assertEqual(error_entry['response_code'], 500)
        self.assertFalse(error_entry['success'])
    
    def test_method_extraction(self):
        """Test HTTP method extraction"""
        parser = HARParser(self.sample_har)
        df = parser.parse()
        
        # Check GET request
        get_entry = df[df['endpoint'] == '/api/users'].iloc[0]
        self.assertEqual(get_entry['method'], 'GET')
        
        # Check POST request
        post_entry = df[df['endpoint'] == '/api/orders'].iloc[0]
        self.assertEqual(post_entry['method'], 'POST')
    
    def test_endpoint_extraction(self):
        """Test URL path extraction"""
        parser = HARParser(self.sample_har)
        df = parser.parse()
        
        endpoints = df['endpoint'].tolist()
        
        self.assertIn('/api/users', endpoints)
        self.assertIn('/api/orders', endpoints)
        self.assertIn('/static/logo.png', endpoints)
        self.assertIn('/api/slow-endpoint', endpoints)
        self.assertIn('/api/products', endpoints)
    
    def test_bytes_calculation(self):
        """Test bytes sent/received calculation"""
        parser = HARParser(self.sample_har)
        df = parser.parse()
        
        # First entry: headers(350) + body(0) sent, headers(280) + body(1250) received
        first_entry = df.iloc[0]
        self.assertEqual(first_entry['bytes_sent'], 350)
        self.assertEqual(first_entry['bytes_recv'], 1530)
        
        # POST entry should have body bytes sent
        post_entry = df[df['endpoint'] == '/api/orders'].iloc[0]
        self.assertEqual(post_entry['bytes_sent'], 932)  # 420 + 512
    
    def test_vus_always_one(self):
        """Test that VUs is always 1 for HAR (single session)"""
        parser = HARParser(self.sample_har)
        df = parser.parse()
        
        # All entries should have vus=1
        self.assertTrue((df['vus'] == 1).all())
    
    def test_timestamp_parsing(self):
        """Test timestamp parsing"""
        parser = HARParser(self.sample_har)
        df = parser.parse()
        
        # Verify timestamps are datetime objects
        self.assertTrue(pd.api.types.is_datetime64_any_dtype(df['timestamp_dt']))
        
        # Verify timestamps are in UTC
        self.assertEqual(str(df['timestamp_dt'].dt.tz), 'UTC')
        
        # Verify chronological order (sample HAR is ordered)
        timestamps = df['timestamp_dt'].tolist()
        self.assertEqual(timestamps, sorted(timestamps))
    
    def test_metadata_extraction(self):
        """Test metadata extraction"""
        parser = HARParser(self.sample_har)
        metadata = parser.get_metadata(self.sample_har)
        
        self.assertEqual(metadata['version'], '1.2')
        self.assertEqual(metadata['creator'], 'Chrome DevTools')
        self.assertEqual(metadata['browser'], 'Chrome')
        self.assertEqual(metadata['entries'], 5)
        self.assertEqual(metadata['pages'], 1)
    
    def test_error_rate_calculation(self):
        """Test error rate can be calculated from parsed data"""
        parser = HARParser(self.sample_har)
        df = parser.parse()
        
        total = len(df)
        errors = len(df[~df['success']])
        error_rate = (errors / total) * 100
        
        # Sample has 1 error out of 5 requests = 20%
        self.assertEqual(error_rate, 20.0)
    
    def test_invalid_har_structure(self):
        """Test handling of invalid HAR structure"""
        import tempfile
        import json
        
        # Create invalid HAR (missing 'log.entries')
        with tempfile.NamedTemporaryFile(mode='w', suffix='.har', delete=False) as f:
            json.dump({'log': {'version': '1.2'}}, f)
            invalid_har = f.name
        
        try:
            parser = HARParser(invalid_har)
            with self.assertRaises(ValueError):
                parser.parse()
        finally:
            os.unlink(invalid_har)
    
    def test_empty_har(self):
        """Test handling of HAR with no entries"""
        import tempfile
        import json
        
        # Create HAR with empty entries
        with tempfile.NamedTemporaryFile(mode='w', suffix='.har', delete=False) as f:
            json.dump({'log': {'version': '1.2', 'entries': []}}, f)
            empty_har = f.name
        
        try:
            parser = HARParser(empty_har)
            with self.assertRaises(ValueError):
                parser.parse()
        finally:
            os.unlink(empty_har)

if __name__ == '__main__':
    unittest.main()
