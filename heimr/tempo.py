# Copyright (c) 2025 Juan Estevez Castillo
# Licensed under AGPL v3. Commercial licenses available.
# See LICENSE or https://www.gnu.org/licenses/agpl-3.0.html
import requests
from typing import Dict, Any, List
from datetime import datetime


class TempoClient:
    """
    Client for querying Grafana Tempo traces.
    """

    def __init__(self, url: str = "http://localhost:3200", file_path: str = None):
        self.url = url.rstrip('/')
        # Tempo uses the same API structure as Jaeger or Zipkin usually,
        # but often exposes a search API at /api/search
        self.api_url = f"{self.url}/api/search"
        self.file_path = file_path

    def query_traces(self, min_duration: str = None, start_time: datetime = None,
                     end_time: datetime = None, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Queries Tempo for traces.
        """
        try:
            params = {
                'limit': limit
            }
            if start_time:
                params['start'] = int(start_time.timestamp())
            if end_time:
                params['end'] = int(end_time.timestamp())
            if min_duration:
                params['minDuration'] = min_duration

            # print(f"DEBUG: Querying Tempo at {self.api_url} with params {params}")
            response = requests.get(self.api_url, params=params, timeout=5)
            response.raise_for_status()

            result = response.json()
            # Result is usually a list of traces
            return result.get('traces', [])
        except Exception as e:
            print(f"Error querying Tempo: {e}")
            return []

    def get_slow_traces(self, start_time: datetime, end_time: datetime,
                        min_duration_ms: int = 1000) -> List[Dict[str, Any]]:
        """
        Fetches traces slower than the specified duration.
        """
        if self.file_path:
            import json
            try:
                with open(self.file_path, 'r') as f:
                    data = json.load(f)
                    # Expecting {"data": [traces...]}
                    traces = data.get('data', [])
                    # Filter by duration
                    slow_traces = []
                    for trace in traces:
                        # Find root span or max duration
                        # Simplified: check any span duration
                        for span in trace.get('spans', []):
                            if span.get('duration', 0) >= min_duration_ms * 1000:  # us
                                slow_traces.append(trace)
                                break
                    return slow_traces
            except Exception as e:
                print(f"Error reading Tempo file: {e}")
                return []

        return self.query_traces(
            min_duration=f"{min_duration_ms}ms",
            start_time=start_time,
            end_time=end_time
        )
