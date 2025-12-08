# Copyright (c) 2025 Juan Estevez Castillo
# Licensed under AGPL v3. Commercial licenses available.
# See LICENSE or https://www.gnu.org/licenses/agpl-3.0.html
import requests
from typing import Dict, Any, List
from datetime import datetime


class LokiClient:
    """
    Client for querying Grafana Loki logs.
    """

    def __init__(self, url: str = "http://localhost:3100", file_path: str = None):
        self.url = url.rstrip('/')
        self.api_url = f"{self.url}/loki/api/v1/query_range"
        self.file_path = file_path

    def query_logs(self, query: str, start_time: datetime, end_time: datetime,
                   limit: int = 100) -> List[Dict[str, Any]]:
        """
        Queries Loki for logs matching the LogQL query.
        """
        try:
            # Loki expects nanosecond timestamps for start/end
            params = {
                'query': query,
                'start': int(start_time.timestamp() * 1e9),
                'end': int(end_time.timestamp() * 1e9),
                'limit': limit
            }
            response = requests.get(self.api_url, params=params)
            response.raise_for_status()

            result = response.json()
            if result.get('status') == 'success':
                # Extract log lines
                # Result format: data -> result -> [{stream: {}, values: [[ts, line], ...]}, ...]
                logs = []
                for stream in result['data']['result']:
                    labels = stream['stream']
                    for value in stream['values']:
                        logs.append({
                            'timestamp': value[0],
                            'line': value[1],
                            'labels': labels
                        })
                return logs
            else:
                print(f"Loki query failed: {result.get('error')}")
                return []
        except Exception as e:
            print(f"Error querying Loki: {e}")
            return []

    def get_error_logs(self, start_time: datetime, end_time: datetime, limit: int = 50) -> List[str]:
        """
        Fetches logs containing 'error' or 'exception'.
        Tries multiple query patterns to support different environments.
        """
        if self.file_path:
            import json
            try:
                with open(self.file_path, 'r') as f:
                    data = json.load(f)
                    # Expecting same structure as API response or simplified
                    # Let's assume the mock generator produces the API response structure
                    if 'data' in data and 'result' in data['data']:
                        logs = []
                        for stream in data['data']['result']:
                            for value in stream['values']:
                                logs.append(value[1])  # value is [ts, line]
                        return logs
                    return []
            except Exception as e:
                print(f"Error reading Loki file: {e}")
                return []

        # Try multiple query patterns for different environments
        queries = [
            # Local demo environment (demo-api server)
            '{job="demo-api"} |= "error"',
            '{service="demo-api"} |= "error"',
            # Kubernetes/Heimr namespaces
            '{namespace=~"heimr-(test|demo)"} |= "error"',
            # Generic fallback - any error logs
            '{job=~".+"} |= "error" |= "level"',
        ]
        
        for query in queries:
            logs = self.query_logs(query, start_time, end_time, limit)
            if logs:
                return [log['line'] for log in logs]
        
        return []
    
    def get_all_logs(self, start_time: datetime, end_time: datetime, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Fetches all logs within the time range.
        Tries multiple query patterns to support different environments.
        """
        queries = [
            '{job="demo-api"}',
            '{service="demo-api"}',
            '{namespace=~"heimr-(test|demo)"}',
        ]
        
        for query in queries:
            logs = self.query_logs(query, start_time, end_time, limit)
            if logs:
                return logs
        
        return []
