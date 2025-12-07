# Copyright (c) 2025 Juan Estevez Castillo
# Licensed under AGPL v3. Commercial licenses available.
# See LICENSE or https://www.gnu.org/licenses/agpl-3.0.html
import requests
from typing import Dict, Any, List
from datetime import datetime


class PrometheusClient:
    """
    Client for querying Prometheus metrics.
    """

    def __init__(self, url: str = "http://localhost:9090", file_path: str = None):
        self.url = url.rstrip('/')
        self.api_url = f"{self.url}/api/v1/query_range"
        self.file_path = file_path

    def query_metric(self, query: str, start_time: datetime, end_time: datetime,
                     step: str = "15s") -> List[Dict[str, Any]]:
        """
        Queries Prometheus for a specific metric over a time range.
        """
        try:
            params = {
                'query': query,
                'start': start_time.timestamp(),
                'end': end_time.timestamp(),
                'step': step
            }
            response = requests.get(self.api_url, params=params)
            response.raise_for_status()

            result = response.json()
            if result['status'] == 'success':
                return result['data']['result']
            else:
                print(f"Prometheus query failed: {result.get('error')}")
                return []
        except Exception as e:
            print(f"Error querying Prometheus: {e}")
            return []

    def get_system_metrics(self, start_time: datetime, end_time: datetime) -> Dict[str, Any]:
        """
        Fetches key system metrics (CPU, Memory) for the given time range.
        """
        if self.file_path:
            import json
            try:
                with open(self.file_path, 'r') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error reading Prometheus file: {e}")
                return {}

        metrics = {}

        # Example queries - adjust based on actual environment
        queries = {
            # Fallback to Node Exporter metrics if cAdvisor is not scraping containers
            'cpu_usage': 'avg(1 - rate(node_cpu_seconds_total{mode="idle"}[1m]))',
            'memory_usage': '1 - (sum(node_memory_MemAvailable_bytes) / sum(node_memory_MemTotal_bytes))'
        }

        for name, query in queries.items():
            metrics[name] = self.query_metric(query, start_time, end_time)

        return metrics
