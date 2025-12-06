# Copyright (c) 2025 Juan Estevez Castillo
# Licensed under AGPL v3. Commercial licenses available.
# See LICENSE or https://www.gnu.org/licenses/agpl-3.0.html

import json
from urllib.parse import urlparse
import pandas as pd
from .base import BaseParser


class HARParser(BaseParser):
    """
    Parser for HTTP Archive (HAR) format files.

    HAR files are JSON-formatted recordings of HTTP transactions,
    commonly exported from:
    - Browser DevTools (Chrome, Firefox, Safari)
    - Playwright/Puppeteer automated tests
    - Postman/Insomnia API clients
    - Real User Monitoring (RUM) tools

    HAR captures client-side performance including network timing,
    resource sizes, and waterfall data.
    """

    def parse(self) -> pd.DataFrame:
        """
        Parse HAR file and convert to UnifiedSchema DataFrame.

        Returns:
            DataFrame with columns: timestamp_dt, elapsed, success,
            response_code, bytes_recv, bytes_sent, vus, endpoint, method
        """
        with open(self.filepath, 'r', encoding='utf-8') as f:
            har_data = json.load(f)

        # Validate HAR structure
        if 'log' not in har_data or 'entries' not in har_data['log']:
            raise ValueError(f"Invalid HAR file: missing 'log.entries' structure in {self.filepath}")

        entries = har_data['log']['entries']

        if not entries:
            raise ValueError(f"HAR file contains no entries: {self.filepath}")

        records = []

        for entry in entries:
            try:
                # Extract request data
                request = entry.get('request', {})
                response = entry.get('response', {})
                timings = entry.get('timings', {})

                # Parse URL to extract endpoint
                url = request.get('url', '')
                parsed_url = urlparse(url)
                endpoint = parsed_url.path or '/'

                # Calculate total time (HAR time is in milliseconds)
                # Use 'time' field if available, otherwise sum timings
                elapsed = entry.get('time', 0)
                if elapsed <= 0:
                    # Fallback: sum individual timing components
                    elapsed = sum([
                        max(0, timings.get('dns', 0)),
                        max(0, timings.get('connect', 0)),
                        max(0, timings.get('ssl', 0)),
                        max(0, timings.get('send', 0)),
                        max(0, timings.get('wait', 0)),
                        max(0, timings.get('receive', 0))
                    ])

                # Extract status code
                status = response.get('status', 0)

                # Calculate bytes sent/received
                # HAR spec: -1 means "not available"
                req_header_size = request.get('headersSize', 0)
                req_body_size = request.get('bodySize', 0)
                resp_header_size = response.get('headersSize', 0)
                resp_body_size = response.get('bodySize', 0)

                bytes_sent = max(0, req_header_size) + max(0, req_body_size)
                bytes_recv = max(0, resp_header_size) + max(0, resp_body_size)

                # Determine success (2xx and 3xx are success)
                success = 200 <= status < 400

                # Parse timestamp
                started_dt = pd.to_datetime(entry.get('startedDateTime'))

                records.append({
                    'timestamp_dt': started_dt,
                    'elapsed': elapsed,
                    'success': success,
                    'response_code': status,
                    'bytes_recv': bytes_recv,
                    'bytes_sent': bytes_sent,
                    'vus': 1,  # HAR represents single session
                    'endpoint': endpoint,
                    'method': request.get('method', 'GET')
                })

            except Exception as e:
                # Log warning but continue processing other entries
                print(f"Warning: Skipping malformed HAR entry: {e}")
                continue

        if not records:
            raise ValueError(f"No valid entries found in HAR file: {self.filepath}")

        self.df = pd.DataFrame(records)
        return self.df

    def get_metadata(self, file_path: str) -> dict:
        """
        Extract HAR metadata (browser, page info, etc.)

        Args:
            file_path: Path to HAR file

        Returns:
            Dictionary with HAR metadata
        """
        with open(file_path, 'r', encoding='utf-8') as f:
            har_data = json.load(f)

        log = har_data.get('log', {})

        return {
            'version': log.get('version', 'unknown'),
            'creator': log.get('creator', {}).get('name', 'unknown'),
            'browser': log.get('browser', {}).get('name', 'unknown'),
            'pages': len(log.get('pages', [])),
            'entries': len(log.get('entries', []))
        }

    def get_summary_stats(self) -> dict:
        """
        Returns basic statistics about the HAR session.

        Returns:
            Dictionary with summary statistics
        """
        if self.df is None or self.df.empty:
            return {
                'total_requests': 0,
                'avg_latency': 0,
                'error_rate': 0
            }

        stats = {
            'total_requests': len(self.df),
            'start_time': self.df['timestamp_dt'].min(),
            'end_time': self.df['timestamp_dt'].max(),
            'avg_latency': self.df['elapsed'].mean(),
            'p95_latency': self.df['elapsed'].quantile(0.95),
            'p99_latency': self.df['elapsed'].quantile(0.99),
            'error_rate': (1 - self.df['success'].mean()) * 100
        }
        return stats
