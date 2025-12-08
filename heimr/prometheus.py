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
        Tries multiple metric sources: Node Exporter, cAdvisor, and app-level HTTP metrics.
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

        # Try multiple query strategies in order of preference
        query_strategies = {
            'cpu_usage': [
                # Node Exporter
                'avg(1 - rate(node_cpu_seconds_total{mode="idle"}[1m]))',
                # cAdvisor
                'avg(rate(container_cpu_usage_seconds_total[1m]))',
            ],
            'memory_usage': [
                # Node Exporter  
                '1 - (sum(node_memory_MemAvailable_bytes) / sum(node_memory_MemTotal_bytes))',
                # cAdvisor
                'sum(container_memory_usage_bytes) / sum(machine_memory_bytes)',
            ],
            # App-level HTTP metrics (always try if available)
            # App-level HTTP metrics (always try if available)
            'http_requests_total': [
                'sum by (endpoint)(rate(http_requests_total[1m]))',
            ],
            'http_requests_failed_total': [
                'sum by (endpoint)(rate(http_requests_failed_total[1m]))',
            ],
            'http_request_duration_seconds_sum': [
                'sum by (endpoint)(rate(http_request_duration_seconds_sum[1m]))',
            ],
            'injection_enabled': [
                'injection_enabled',
            ],
            'injection_latency_ms': [
                'injection_latency_ms',
            ],
            'injection_memory_mb': [
                'injection_memory_mb',
            ],
            # Disk I/O (Node Exporter)
            'node_disk_read_bytes_total': [
                'sum(rate(node_disk_read_bytes_total[1m]))',
            ],
            'node_disk_written_bytes_total': [
                'sum(rate(node_disk_written_bytes_total[1m]))',
            ],
            # Network I/O (Node Exporter)
            'node_network_receive_bytes_total': [
                'sum(rate(node_network_receive_bytes_total[1m]))',
            ],
            'node_network_transmit_bytes_total': [
                'sum(rate(node_network_transmit_bytes_total[1m]))',
            ],
        }

        for metric_name, queries in query_strategies.items():
            for query in queries:
                result = self.query_metric(query, start_time, end_time)
                if result:  # Got data, use it
                    metrics[metric_name] = result
                    break  # Move to next metric

        return metrics
