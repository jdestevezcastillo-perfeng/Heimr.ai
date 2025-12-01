"""Data schema definitions for training datasets."""
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Dict, List, Optional
from enum import Enum


class BottleneckType(str, Enum):
    """Types of performance bottlenecks."""
    HEALTHY = "healthy"
    LATENCY_SPIKE = "latency_spike"
    LATENCY_BIMODAL = "latency_bimodal"
    LATENCY_DEGRADATION = "latency_degradation"
    ERROR_SPIKE = "error_spike"
    ERROR_INTERMITTENT = "error_intermittent"
    RATE_LIMIT = "rate_limit"
    RESOURCE_EXHAUSTION = "resource_exhaustion"
    CPU_BOUND = "cpu_bound"
    CASCADE_FAILURE = "cascade_failure"


class Severity(str, Enum):
    """Severity levels for bottlenecks."""
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class MetricsSnapshot:
    """Snapshot of performance metrics."""
    # Request metrics
    request_rate: float = 0.0
    
    # Latency metrics (in seconds)
    p50_latency: float = 0.0
    p95_latency: float = 0.0
    p99_latency: float = 0.0
    p999_latency: float = 0.0
    
    # Error metrics
    error_rate: float = 0.0
    error_5xx_rate: float = 0.0
    error_429_rate: float = 0.0
    
    # Resource metrics
    concurrent_requests: float = 0.0
    
    # Chaos-specific metrics
    chaos_latency_injected: float = 0.0
    chaos_errors_injected: float = 0.0
    
    def to_dict(self) -> Dict[str, float]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class AggregatedMetrics:
    """Aggregated metrics over a time window."""
    # Request rate statistics
    request_rate_mean: float = 0.0
    request_rate_std: float = 0.0
    request_rate_min: float = 0.0
    request_rate_max: float = 0.0
    
    # Latency statistics (in seconds)
    p50_latency_mean: float = 0.0
    p50_latency_std: float = 0.0
    p95_latency_mean: float = 0.0
    p95_latency_std: float = 0.0
    p99_latency_mean: float = 0.0
    p99_latency_std: float = 0.0
    p99_latency_max: float = 0.0
    
    # Error statistics
    error_rate_mean: float = 0.0
    error_rate_std: float = 0.0
    error_rate_max: float = 0.0
    
    # Resource statistics
    concurrent_requests_mean: float = 0.0
    concurrent_requests_max: float = 0.0
    
    def to_dict(self) -> Dict[str, float]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class TrainingLabels:
    """Ground truth labels for training."""
    has_bottleneck: bool
    bottleneck_type: BottleneckType
    severity: Severity
    root_cause: str
    recommendations: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "has_bottleneck": self.has_bottleneck,
            "bottleneck_type": self.bottleneck_type.value,
            "severity": self.severity.value,
            "root_cause": self.root_cause,
            "recommendations": self.recommendations
        }


@dataclass
class TrainingExample:
    """Complete training example with metrics and labels."""
    # Metadata
    id: str
    timestamp: datetime
    scenario: str
    duration_seconds: int
    
    # Metrics
    metrics: AggregatedMetrics
    
    # Labels
    labels: TrainingLabels
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for storage."""
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat(),
            "scenario": self.scenario,
            "duration_seconds": self.duration_seconds,
            "metrics": self.metrics.to_dict(),
            "labels": self.labels.to_dict()
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'TrainingExample':
        """Create from dictionary."""
        return cls(
            id=data["id"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            scenario=data["scenario"],
            duration_seconds=data["duration_seconds"],
            metrics=AggregatedMetrics(**data["metrics"]),
            labels=TrainingLabels(
                has_bottleneck=data["labels"]["has_bottleneck"],
                bottleneck_type=BottleneckType(data["labels"]["bottleneck_type"]),
                severity=Severity(data["labels"]["severity"]),
                root_cause=data["labels"]["root_cause"],
                recommendations=data["labels"]["recommendations"]
            )
        )


# Scenario to bottleneck type mapping
SCENARIO_MAPPING = {
    "healthy": {
        "bottleneck_type": BottleneckType.HEALTHY,
        "severity": Severity.NONE,
        "root_cause": "System is operating normally with no performance issues.",
        "recommendations": []
    },
    "latency_spike": {
        "bottleneck_type": BottleneckType.LATENCY_SPIKE,
        "severity": Severity.HIGH,
        "root_cause": "Detected p99 latency spike indicating tail latency issues affecting 1-10% of requests. Likely causes: GC pauses, network congestion, cache misses, or database query slowdowns.",
        "recommendations": [
            "Check GC logs for long pause times",
            "Review network latency to upstream services",
            "Analyze cache hit rates for degradation",
            "Examine slow query logs in database",
            "Monitor for resource contention"
        ]
    },
    "bimodal_latency": {
        "bottleneck_type": BottleneckType.LATENCY_BIMODAL,
        "severity": Severity.MEDIUM,
        "root_cause": "Bimodal latency distribution detected with two distinct performance modes. This typically indicates cache hit/miss patterns, hot/cold data access, or primary/replica routing issues.",
        "recommendations": [
            "Analyze cache hit/miss ratios",
            "Review data access patterns for hot spots",
            "Check if read replicas are properly balanced",
            "Investigate connection pool behavior",
            "Consider warming up caches proactively"
        ]
    },
    "gradual_degradation": {
        "bottleneck_type": BottleneckType.LATENCY_DEGRADATION,
        "severity": Severity.HIGH,
        "root_cause": "Gradual performance degradation over time indicating resource leaks, memory pressure, or accumulating system state. This pattern suggests the system will eventually fail if not addressed.",
        "recommendations": [
            "Check for memory leaks in application code",
            "Monitor heap usage and GC frequency",
            "Review connection pool exhaustion",
            "Investigate file descriptor leaks",
            "Analyze disk space and I/O patterns",
            "Consider implementing circuit breakers"
        ]
    },
    "error_spike": {
        "bottleneck_type": BottleneckType.ERROR_SPIKE,
        "severity": Severity.CRITICAL,
        "root_cause": "High error rate (5xx errors) indicating service degradation or dependency failures. This requires immediate attention to prevent cascading failures.",
        "recommendations": [
            "Check upstream service health",
            "Review application error logs",
            "Verify database connectivity",
            "Check for deployment issues",
            "Implement retry logic with backoff",
            "Enable circuit breakers for failing dependencies"
        ]
    },
    "intermittent": {
        "bottleneck_type": BottleneckType.ERROR_INTERMITTENT,
        "severity": Severity.MEDIUM,
        "root_cause": "Intermittent failures indicating flaky behavior, race conditions, or transient network issues. These are often difficult to reproduce and debug.",
        "recommendations": [
            "Add detailed logging around failure points",
            "Implement request tracing",
            "Check for race conditions in concurrent code",
            "Review network stability",
            "Add retry logic for transient failures",
            "Monitor for patterns in failure timing"
        ]
    },
    "rate_limited": {
        "bottleneck_type": BottleneckType.RATE_LIMIT,
        "severity": Severity.MEDIUM,
        "root_cause": "Rate limiting is being triggered (429 errors), indicating the system is receiving more requests than configured capacity. This is a protective measure but indicates capacity planning issues.",
        "recommendations": [
            "Review rate limit thresholds",
            "Implement client-side backoff and retry",
            "Consider horizontal scaling",
            "Analyze traffic patterns for spikes",
            "Implement request queuing",
            "Add autoscaling based on load"
        ]
    },
    "connection_exhaustion": {
        "bottleneck_type": BottleneckType.RESOURCE_EXHAUSTION,
        "severity": Severity.HIGH,
        "root_cause": "Connection pool exhaustion detected. The system is unable to handle concurrent requests due to limited connection resources.",
        "recommendations": [
            "Increase connection pool size",
            "Reduce connection timeout values",
            "Implement connection pooling best practices",
            "Check for connection leaks",
            "Add request queuing",
            "Consider horizontal scaling"
        ]
    },
    "cpu_bound": {
        "bottleneck_type": BottleneckType.CPU_BOUND,
        "severity": Severity.HIGH,
        "root_cause": "CPU saturation detected. Requests are CPU-bound, likely due to expensive computations, inefficient algorithms, or lack of caching.",
        "recommendations": [
            "Profile CPU usage to identify hot paths",
            "Optimize expensive algorithms",
            "Implement caching for computed results",
            "Consider async processing for heavy tasks",
            "Add more CPU resources (vertical scaling)",
            "Distribute load across more instances"
        ]
    },
    "cascade_failure": {
        "bottleneck_type": BottleneckType.CASCADE_FAILURE,
        "severity": Severity.CRITICAL,
        "root_cause": "Cascading failure detected with both increasing errors and latency under load. This indicates the system is in a degraded state and may be approaching total failure.",
        "recommendations": [
            "Implement circuit breakers immediately",
            "Add load shedding to protect the system",
            "Enable rate limiting",
            "Scale up resources urgently",
            "Investigate root cause of dependency failures",
            "Consider graceful degradation strategies",
            "Enable bulkhead pattern for isolation"
        ]
    }
}


def get_labels_for_scenario(scenario: str) -> TrainingLabels:
    """Get training labels for a given scenario.
    
    Args:
        scenario: Scenario name
        
    Returns:
        TrainingLabels with appropriate values
    """
    if scenario not in SCENARIO_MAPPING:
        raise ValueError(f"Unknown scenario: {scenario}")
    
    mapping = SCENARIO_MAPPING[scenario]
    
    return TrainingLabels(
        has_bottleneck=(scenario != "healthy"),
        bottleneck_type=mapping["bottleneck_type"],
        severity=mapping["severity"],
        root_cause=mapping["root_cause"],
        recommendations=mapping["recommendations"]
    )
