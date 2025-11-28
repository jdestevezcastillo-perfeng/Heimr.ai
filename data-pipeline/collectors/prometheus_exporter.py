"""Prometheus metrics exporter for chaos generator data."""
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PrometheusExporter:
    """Export metrics from Prometheus for training data generation."""
    
    def __init__(self, prometheus_url: str = "http://localhost:9090"):
        """Initialize Prometheus exporter.
        
        Args:
            prometheus_url: URL of Prometheus server
        """
        self.prometheus_url = prometheus_url
        self.api_url = f"{prometheus_url}/api/v1"
        
    def query(self, query: str) -> Dict[str, Any]:
        """Execute a PromQL query.
        
        Args:
            query: PromQL query string
            
        Returns:
            Query result as dictionary
        """
        url = f"{self.api_url}/query"
        params = {"query": query}
        
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to query Prometheus: {e}")
            return {"status": "error", "data": {"result": []}}
    
    def query_range(
        self,
        query: str,
        start: datetime,
        end: datetime,
        step: str = "15s"
    ) -> Dict[str, Any]:
        """Execute a PromQL range query.
        
        Args:
            query: PromQL query string
            start: Start time
            end: End time
            step: Query resolution step
            
        Returns:
            Query result as dictionary
        """
        url = f"{self.api_url}/query_range"
        params = {
            "query": query,
            "start": start.timestamp(),
            "end": end.timestamp(),
            "step": step
        }
        
        try:
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to query Prometheus range: {e}")
            return {"status": "error", "data": {"result": []}}
    
    def get_current_scenario(self) -> Optional[str]:
        """Get the currently active chaos scenario.
        
        Returns:
            Scenario name or None if not available
        """
        query = 'chaos_active_scenario'
        result = self.query(query)
        
        if result["status"] == "success" and result["data"]["result"]:
            # Get the scenario label from the metric
            metric = result["data"]["result"][0]
            return metric["metric"].get("scenario", "unknown")
        
        return None
    
    def export_metrics_snapshot(
        self,
        timestamp: Optional[datetime] = None
    ) -> Dict[str, float]:
        """Export a snapshot of all relevant metrics at a point in time.
        
        Args:
            timestamp: Time to query (default: now)
            
        Returns:
            Dictionary of metric values
        """
        if timestamp is None:
            timestamp = datetime.utcnow()
        
        # Define metrics to export
        metrics = {
            # Request rate
            "request_rate": 'rate(http_requests_total[5m])',
            
            # Latency percentiles
            "p50_latency": 'histogram_quantile(0.50, rate(http_request_duration_seconds_bucket[5m]))',
            "p95_latency": 'histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))',
            "p99_latency": 'histogram_quantile(0.99, rate(http_request_duration_seconds_bucket[5m]))',
            "p999_latency": 'histogram_quantile(0.999, rate(http_request_duration_seconds_bucket[5m]))',
            
            # Error rates
            "error_rate": 'rate(http_requests_total{status=~"[45].."}[5m])',
            "error_5xx_rate": 'rate(http_requests_total{status=~"5.."}[5m])',
            "error_429_rate": 'rate(http_requests_total{status="429"}[5m])',
            
            # Concurrent requests
            "concurrent_requests": 'chaos_concurrent_requests',
            
            # Chaos-specific metrics
            "chaos_latency_injected": 'chaos_latency_injected_seconds_sum',
            "chaos_errors_injected": 'rate(chaos_errors_injected_total[5m])',
        }
        
        snapshot = {}
        for name, query in metrics.items():
            result = self.query(query)
            if result["status"] == "success" and result["data"]["result"]:
                # Get the value from the first result
                value = float(result["data"]["result"][0]["value"][1])
                snapshot[name] = value
            else:
                snapshot[name] = 0.0
        
        return snapshot
    
    def export_scenario_metrics(
        self,
        scenario_name: str,
        duration_minutes: int = 5
    ) -> Dict[str, Any]:
        """Export all metrics for a chaos scenario run.
        
        Args:
            scenario_name: Name of the chaos scenario
            duration_minutes: Duration to collect metrics for
            
        Returns:
            Dictionary containing time-series metrics and aggregated stats
        """
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(minutes=duration_minutes)
        
        logger.info(f"Exporting metrics for scenario '{scenario_name}' "
                   f"from {start_time} to {end_time}")
        
        # Collect time-series data
        time_series = {}
        
        # Request rate
        time_series["request_rate"] = self.query_range(
            'rate(http_requests_total[5m])',
            start_time, end_time
        )
        
        # Latency percentiles
        for percentile in [50, 95, 99]:
            time_series[f"p{percentile}_latency"] = self.query_range(
                f'histogram_quantile(0.{percentile:02d}, '
                f'rate(http_request_duration_seconds_bucket[5m]))',
                start_time, end_time
            )
        
        # Error rate
        time_series["error_rate"] = self.query_range(
            'rate(http_requests_total{status=~"[45].."}[5m])',
            start_time, end_time
        )
        
        # Aggregate statistics
        aggregated = self._aggregate_time_series(time_series)
        
        return {
            "scenario": scenario_name,
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "duration_minutes": duration_minutes,
            "time_series": time_series,
            "aggregated": aggregated
        }
    
    def _aggregate_time_series(
        self,
        time_series: Dict[str, Any]
    ) -> Dict[str, Dict[str, float]]:
        """Aggregate time-series data into statistics.
        
        Args:
            time_series: Time-series data from Prometheus
            
        Returns:
            Dictionary of aggregated statistics (mean, std, min, max)
        """
        import statistics
        
        aggregated = {}
        
        for metric_name, data in time_series.items():
            if data["status"] != "success" or not data["data"]["result"]:
                aggregated[metric_name] = {
                    "mean": 0.0,
                    "std": 0.0,
                    "min": 0.0,
                    "max": 0.0,
                    "count": 0
                }
                continue
            
            # Extract values from time series
            values = []
            for result in data["data"]["result"]:
                for timestamp, value in result["values"]:
                    try:
                        values.append(float(value))
                    except (ValueError, TypeError):
                        continue
            
            if values:
                mean_val = statistics.mean(values)
                if len(values) > 1:
                    try:
                        variance = sum((x - mean_val) ** 2 for x in values) / (len(values) - 1)
                        std_val = variance ** 0.5
                    except Exception:
                        std_val = 0.0
                else:
                    std_val = 0.0
                    
                aggregated[metric_name] = {
                    "mean": mean_val,
                    "std": std_val,
                    "min": min(values),
                    "max": max(values),
                    "count": len(values)
                }
            else:
                aggregated[metric_name] = {
                    "mean": 0.0,
                    "std": 0.0,
                    "min": 0.0,
                    "max": 0.0,
                    "count": 0
                }
        
        return aggregated
    
    def health_check(self) -> bool:
        """Check if Prometheus is accessible.
        
        Returns:
            True if Prometheus is healthy, False otherwise
        """
        try:
            response = requests.get(f"{self.prometheus_url}/-/healthy", timeout=5)
            return response.status_code == 200
        except requests.exceptions.RequestException:
            return False


if __name__ == "__main__":
    # Test the exporter
    exporter = PrometheusExporter()
    
    if exporter.health_check():
        print("✅ Prometheus is healthy")
        
        # Get current scenario
        scenario = exporter.get_current_scenario()
        print(f"📊 Current scenario: {scenario}")
        
        # Get current metrics snapshot
        snapshot = exporter.export_metrics_snapshot()
        print("\n📈 Current metrics:")
        for metric, value in snapshot.items():
            print(f"  {metric}: {value:.4f}")
    else:
        print("❌ Prometheus is not accessible")
