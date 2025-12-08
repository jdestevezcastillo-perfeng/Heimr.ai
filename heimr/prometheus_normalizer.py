# Copyright (c) 2025 Juan Estevez Castillo
# Licensed under AGPL v3. Commercial licenses available.
# See LICENSE or https://www.gnu.org/licenses/agpl-3.0.html
"""
Prometheus Metric Normalizer for Heimr.
Normalizes metrics from various exporters to standard names.
"""
from typing import Dict, Any, List, Optional
import re


class PrometheusNormalizer:
    """Normalize Prometheus metrics from various exporters to standard names."""
    
    # CPU metric patterns
    CPU_PATTERNS = [
        r'container_cpu_usage_seconds_total',
        r'node_cpu_seconds_total',
        r'process_cpu_seconds_total',
        r'cpu_usage.*',
    ]
    
    # Memory metric patterns
    MEMORY_PATTERNS = [
        r'container_memory_usage_bytes',
        r'container_memory_working_set_bytes',
        r'node_memory_MemTotal_bytes',
        r'node_memory_MemAvailable_bytes',
        r'process_resident_memory_bytes',
        r'memory_usage.*',
    ]
    
    # GPU metric patterns (NVIDIA, AMD, Intel)
    GPU_PATTERNS = [
        # NVIDIA
        r'nvidia_smi_.*',
        r'nvml_.*',
        r'dcgm_.*',
        r'gpu_utilization.*nvidia.*',
        # AMD
        r'rocm_.*',
        r'amd_gpu_.*',
        # Intel
        r'intel_gpu_.*',
        r'xe_.*',
        # Generic
        r'gpu_.*',
    ]
    
    # Database metric patterns
    DB_PATTERNS = [
        # PostgreSQL
        r'pg_.*',
        r'postgres_.*',
        # MySQL
        r'mysql_.*',
        r'mysqld_.*',
        # Redis
        r'redis_.*',
        # MongoDB
        r'mongodb_.*',
        r'mongo_.*',
        # Generic
        r'db_.*',
    ]
    
    # Disk I/O patterns
    DISK_PATTERNS = [
        r'node_disk_read_bytes_total',
        r'node_disk_written_bytes_total',
        r'container_fs_reads_bytes_total',
        r'container_fs_writes_bytes_total',
    ]
    
    # Network I/O patterns
    NETWORK_PATTERNS = [
        r'node_network_receive_bytes_total',
        r'node_network_transmit_bytes_total',
        r'container_network_receive_bytes_total',
        r'container_network_transmit_bytes_total',
    ]
    
    # Messaging/Streaming patterns (Kafka, RabbitMQ, SQS, NATS, etc.)
    MESSAGING_PATTERNS = [
        # Kafka
        r'kafka_.*',
        r'kafka_consumer_.*',
        r'kafka_producer_.*',
        r'kafka_server_.*',
        r'kafka_controller_.*',
        r'kafka_network_.*',
        r'kafka_log_.*',
        # RabbitMQ
        r'rabbitmq_.*',
        r'rabbit_.*',
        # AWS SQS/SNS
        r'aws_sqs_.*',
        r'aws_sns_.*',
        r'sqs_.*',
        # NATS
        r'nats_.*',
        r'jetstream_.*',
        # ActiveMQ
        r'activemq_.*',
        # Redis Streams (pub/sub)
        r'redis_stream_.*',
        r'redis_pubsub_.*',
        # Pulsar
        r'pulsar_.*',
        # Generic message queue patterns
        r'mq_.*',
        r'queue_.*',
        r'message_.*',
    ]
    
    # HTTP/Application metrics patterns
    HTTP_PATTERNS = [
        r'http_requests_total',
        r'http_requests_failed_total',
        r'http_request_duration_.*',
        r'http_request_size_bytes.*',
        r'http_response_size_bytes.*',
        r'http_active_requests',
        r'http_server_.*',
        r'http_client_.*',
        # Injection/chaos metrics from our demo
        r'injection_.*',
    ]

    @classmethod
    def categorize_metrics(cls, metrics: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        """
        Categorize metrics into standard categories.
        
        Returns dict with keys: cpu, memory, gpu, db, disk, network, other
        """
        categorized = {
            'cpu': {},
            'memory': {},
            'gpu': {},
            'db': {},
            'disk': {},
            'network': {},
            'messaging': {},
            'http': {},
            'other': {}
        }
        
        for metric_name, metric_data in metrics.items():
            category = cls._get_category(metric_name)
            categorized[category][metric_name] = metric_data
            
        return categorized
    
    @classmethod
    def _get_category(cls, metric_name: str) -> str:
        """Determine the category of a metric based on its name."""
        name_lower = metric_name.lower()
        
        for pattern in cls.CPU_PATTERNS:
            if re.match(pattern, name_lower):
                return 'cpu'
                
        for pattern in cls.MEMORY_PATTERNS:
            if re.match(pattern, name_lower):
                return 'memory'
                
        for pattern in cls.GPU_PATTERNS:
            if re.match(pattern, name_lower):
                return 'gpu'
                
        for pattern in cls.DB_PATTERNS:
            if re.match(pattern, name_lower):
                return 'db'
                
        for pattern in cls.DISK_PATTERNS:
            if re.match(pattern, name_lower):
                return 'disk'
                
        for pattern in cls.NETWORK_PATTERNS:
            if re.match(pattern, name_lower):
                return 'network'
        
        for pattern in cls.MESSAGING_PATTERNS:
            if re.match(pattern, name_lower):
                return 'messaging'
        
        for pattern in cls.HTTP_PATTERNS:
            if re.match(pattern, name_lower):
                return 'http'
                
        return 'other'
    
    @classmethod
    def extract_time_series(cls, metric_data: Any) -> List[Dict[str, Any]]:
        """
        Extract time series values from metric data.
        Returns list of {timestamp, value, labels} dicts.
        """
        result = []
        
        if not metric_data:
            return result
            
        # Handle list of series (common format)
        for series in metric_data if isinstance(metric_data, list) else [metric_data]:
            labels = series.get('metric', {})
            values = series.get('values', [])
            
            for point in values:
                try:
                    timestamp = float(point[0])
                    value = float(point[1])
                    result.append({
                        'timestamp': timestamp,
                        'value': value,
                        'labels': labels
                    })
                except (ValueError, IndexError):
                    continue
                    
        return result
    
    @classmethod
    def has_gpu_metrics(cls, metrics: Dict[str, Any]) -> bool:
        """Check if GPU metrics are present."""
        categorized = cls.categorize_metrics(metrics)
        return len(categorized.get('gpu', {})) > 0
    
    @classmethod
    def has_db_metrics(cls, metrics: Dict[str, Any]) -> bool:
        """Check if database metrics are present."""
        categorized = cls.categorize_metrics(metrics)
        return len(categorized.get('db', {})) > 0
    
    @classmethod
    def has_messaging_metrics(cls, metrics: Dict[str, Any]) -> bool:
        """Check if messaging/streaming metrics are present (Kafka, RabbitMQ, etc.)."""
        categorized = cls.categorize_metrics(metrics)
        return len(categorized.get('messaging', {})) > 0

