# Copyright (c) 2025 Juan Estevez Castillo
# Licensed under AGPL v3. Commercial licenses available.
# See LICENSE or https://www.gnu.org/licenses/agpl-3.0.html
from typing import Dict, Any, List
from datetime import datetime


class PerformanceComparator:
    """
    Compares two load test runs and generates a comparison report.
    """

    def __init__(self, baseline_stats: Dict[str, Any], current_stats: Dict[str, Any]):
        self.baseline = baseline_stats
        self.current = current_stats

    def compare_metrics(self) -> Dict[str, Any]:
        """Compare key performance metrics between baseline and current."""
        comparison = {}

        metrics_to_compare = [
            'total_requests',
            'avg_latency',
            'median_latency',
            'p95_latency',
            'p99_latency',
            'min_latency',
            'max_latency',
            'error_rate',
            'error_count',
            'throughput'
        ]

        for metric in metrics_to_compare:
            baseline_val = self.baseline.get(metric, 0)
            current_val = self.current.get(metric, 0)

            if baseline_val == 0:
                pct_change = 0 if current_val == 0 else float('inf')
            else:
                pct_change = ((current_val - baseline_val) / baseline_val) * 100

            comparison[metric] = {
                'baseline': baseline_val,
                'current': current_val,
                'delta': current_val - baseline_val,
                'pct_change': pct_change,
                'improved': self._is_improvement(metric, pct_change)
            }

        return comparison

    def _is_improvement(self, metric: str, pct_change: float) -> bool:
        """Determine if a change is an improvement based on metric type."""
        # For these metrics, lower is better
        lower_is_better = [
            'avg_latency', 'median_latency', 'p95_latency', 'p99_latency',
            'min_latency', 'max_latency', 'error_rate', 'error_count'
        ]

        # For these metrics, higher is better
        higher_is_better = ['throughput', 'total_requests']

        if metric in lower_is_better:
            return pct_change < 0  # Negative change is improvement
        elif metric in higher_is_better:
            return pct_change > 0  # Positive change is improvement
        else:
            return False

    def compare_anomalies(self, baseline_anomalies: Dict[str, Any],
                          current_anomalies: Dict[str, Any]) -> Dict[str, Any]:
        """Compare anomaly detection results."""
        baseline_count = baseline_anomalies.get('count', 0)
        current_count = current_anomalies.get('count', 0)

        return {
            'baseline_count': baseline_count,
            'current_count': current_count,
            'delta': current_count - baseline_count,
            'new_anomalies': current_count > baseline_count,
            'baseline_avg_latency': baseline_anomalies.get('avg_latency', 0),
            'current_avg_latency': current_anomalies.get('avg_latency', 0),
            'baseline_max_latency': baseline_anomalies.get('max_latency', 0),
            'current_max_latency': current_anomalies.get('max_latency', 0)
        }

    def compare_prometheus(self, baseline_metrics: Dict[str, Any], current_metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Compare Prometheus system metrics."""
        comparison = {}

        for metric_name in ['cpu_usage', 'memory_usage']:
            if metric_name not in baseline_metrics or metric_name not in current_metrics:
                continue

            baseline_values = self._extract_metric_values(baseline_metrics[metric_name])
            current_values = self._extract_metric_values(current_metrics[metric_name])

            if not baseline_values or not current_values:
                continue

            baseline_avg = sum(baseline_values) / len(baseline_values)
            current_avg = sum(current_values) / len(current_values)

            pct_change = ((current_avg - baseline_avg) / baseline_avg * 100) if baseline_avg != 0 else 0

            comparison[metric_name] = {
                'baseline_avg': baseline_avg,
                'current_avg': current_avg,
                'baseline_max': max(baseline_values),
                'current_max': max(current_values),
                'pct_change': pct_change,
                'regression': pct_change > 10  # >10% increase is a regression
            }

        return comparison

    def _extract_metric_values(self, metric_data: List[Dict]) -> List[float]:
        """Extract numeric values from Prometheus metric data."""
        values = []
        for series in metric_data:
            for timestamp, value in series.get('values', []):
                try:
                    values.append(float(value))
                except (ValueError, TypeError):
                    continue
        return values

    def compare_logs(self, baseline_logs: List[str], current_logs: List[str]) -> Dict[str, Any]:
        """Compare log patterns between baseline and current."""
        baseline_errors = sum(1 for log in baseline_logs if 'error' in log.lower() or 'level=error' in log.lower())
        current_errors = sum(1 for log in current_logs if 'error' in log.lower() or 'level=error' in log.lower())

        baseline_warnings = sum(1 for log in baseline_logs if 'warn' in log.lower() or 'level=warn' in log.lower())
        current_warnings = sum(1 for log in current_logs if 'warn' in log.lower() or 'level=warn' in log.lower())

        return {
            'baseline_total': len(baseline_logs),
            'current_total': len(current_logs),
            'baseline_errors': baseline_errors,
            'current_errors': current_errors,
            'error_delta': current_errors - baseline_errors,
            'baseline_warnings': baseline_warnings,
            'current_warnings': current_warnings,
            'warning_delta': current_warnings - baseline_warnings
        }

    def compare_traces(self, baseline_traces: List[Dict], current_traces: List[Dict]) -> Dict[str, Any]:
        """Compare distributed traces between baseline and current."""
        baseline_ops = self._extract_operations(baseline_traces)
        current_ops = self._extract_operations(current_traces)

        # Find new slow operations
        new_slow_ops = set(current_ops.keys()) - set(baseline_ops.keys())

        # Find operations that got slower
        slower_ops = []
        for op in baseline_ops:
            if op in current_ops:
                baseline_avg = sum(baseline_ops[op]) / len(baseline_ops[op])
                current_avg = sum(current_ops[op]) / len(current_ops[op])
                if current_avg > baseline_avg * 1.2:  # 20% slower
                    slower_ops.append({
                        'operation': op,
                        'baseline_avg': baseline_avg,
                        'current_avg': current_avg,
                        'pct_change': ((current_avg - baseline_avg) / baseline_avg * 100)
                    })

        return {
            'baseline_trace_count': len(baseline_traces),
            'current_trace_count': len(current_traces),
            'new_slow_operations': list(new_slow_ops),
            'slower_operations': slower_ops
        }

    def _extract_operations(self, traces: List[Dict]) -> Dict[str, List[float]]:
        """Extract operation names and their durations from traces."""
        operations = {}
        for trace in traces:
            for span in trace.get('spans', []):
                op_name = span.get('operationName', 'unknown')
                duration_us = span.get('duration', 0)
                duration_ms = duration_us / 1000  # Convert to ms

                if op_name not in operations:
                    operations[op_name] = []
                operations[op_name].append(duration_ms)

        return operations

    def generate_comparison_report(
        self,
        metrics_comparison: Dict[str, Any],
        anomalies_comparison: Dict[str, Any],
        prometheus_comparison: Dict[str, Any] = None,
        logs_comparison: Dict[str, Any] = None,
        traces_comparison: Dict[str, Any] = None
    ) -> str:
        """Generate a Markdown comparison report."""

        report = []
        report.append("# Performance Comparison Report")
        report.append("")
        report.append(f"**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")

        # Overall verdict
        report.append("## Overall Verdict")
        report.append("")
        verdict = self._calculate_verdict(metrics_comparison, anomalies_comparison)
        report.append(verdict)
        report.append("")

        # Metrics comparison
        report.append("## Key Performance Metrics")
        report.append("")
        report.append("| Metric | Baseline | Current | Delta | Change | Status |")
        report.append("|--------|----------|---------|-------|--------|--------|")

        for metric, data in metrics_comparison.items():
            baseline = data['baseline']
            current = data['current']
            delta = data['delta']
            pct = data['pct_change']
            improved = data['improved']

            # Format values based on metric type
            if 'latency' in metric or 'duration' in metric:
                baseline_str = f"{baseline:.2f} ms"
                current_str = f"{current:.2f} ms"
                delta_str = f"{delta:+.2f} ms"
            elif 'rate' in metric:
                baseline_str = f"{baseline:.2f}%"
                current_str = f"{current:.2f}%"
                delta_str = f"{delta:+.2f}%"
            elif 'throughput' in metric:
                baseline_str = f"{baseline:.2f} req/s"
                current_str = f"{current:.2f} req/s"
                delta_str = f"{delta:+.2f} req/s"
            else:
                baseline_str = f"{baseline}"
                current_str = f"{current}"
                delta_str = f"{delta:+}"

            pct_str = f"{pct:+.1f}%" if pct != float('inf') else "N/A"
            status = "✅ Improved" if improved else ("⚠️ Regression" if pct != 0 else "➖ No change")

            metric_display = metric.replace('_', ' ').title()
            report.append(f"| {metric_display} | {baseline_str} | {current_str} | {delta_str} | {pct_str} | {status} |")

        report.append("")

        # Anomalies comparison
        report.append("## Anomaly Detection")
        report.append("")
        baseline_count = anomalies_comparison['baseline_count']
        current_count = anomalies_comparison['current_count']
        delta = anomalies_comparison['delta']

        if delta > 0:
            report.append(f"⚠️ **Regression**: {delta} more anomalies detected ({baseline_count} → {current_count})")
        elif delta < 0:
            report.append(
                f"✅ **Improvement**: {abs(delta)} fewer anomalies detected ({baseline_count} → {current_count})")
        else:
            report.append(f"➖ **No change**: {current_count} anomalies detected in both runs")

        report.append("")

        # Prometheus comparison
        if prometheus_comparison:
            report.append("## System Resource Utilization")
            report.append("")
            for metric, data in prometheus_comparison.items():
                metric_name = metric.replace('_', ' ').title()
                baseline_avg = data['baseline_avg']
                current_avg = data['current_avg']
                pct_change = data['pct_change']

                if 'cpu' in metric:
                    # Show absolute change in percentage points for clarity
                    abs_change = (current_avg - baseline_avg) * 100
                    report.append(
                        f"**{metric_name}**: {baseline_avg * 100:.1f}% → {current_avg * 100:.1f}% "
                        f"({abs_change:+.1f}pp)"
                    )
                elif 'memory' in metric:
                    # Show absolute change in MB
                    abs_change_mb = (current_avg - baseline_avg) / 1024 / 1024
                    report.append(
                        f"**{metric_name}**: {baseline_avg / 1024 / 1024:.1f}MB → "
                        f"{current_avg / 1024 / 1024:.1f}MB ({abs_change_mb:+.1f}MB, {pct_change:+.1f}%)"
                    )

                if data['regression']:
                    report.append("  - ⚠️ Resource usage increased significantly")

            report.append("")

        # Logs comparison
        if logs_comparison:
            report.append("## Application Logs")
            report.append("")
            error_delta = logs_comparison['error_delta']
            warn_delta = logs_comparison['warning_delta']

            if error_delta != 0:
                status = "⚠️" if error_delta > 0 else "✅"
                report.append(
                    f"{status} **Errors**: {logs_comparison['baseline_errors']} → "
                    f"{logs_comparison['current_errors']} ({error_delta:+})"
                )

            if warn_delta != 0:
                status = "⚠️" if warn_delta > 0 else "✅"
                report.append(
                    f"{status} **Warnings**: {logs_comparison['baseline_warnings']} → "
                    f"{logs_comparison['current_warnings']} ({warn_delta:+})"
                )

            report.append("")

        # Traces comparison
        if traces_comparison:
            report.append("## Distributed Traces")
            report.append("")

            if traces_comparison['new_slow_operations']:
                report.append("### ⚠️ New Slow Operations")
                for op in traces_comparison['new_slow_operations']:
                    report.append(f"- `{op}`")
                report.append("")

            if traces_comparison['slower_operations']:
                report.append("### ⚠️ Operations That Got Slower")
                report.append("")
                report.append("| Operation | Baseline Avg | Current Avg | Change |")
                report.append("|-----------|--------------|-------------|--------|")
                for op in traces_comparison['slower_operations']:
                    report.append(
                        f"| `{op['operation']}` | {op['baseline_avg']:.2f}ms | "
                        f"{op['current_avg']:.2f}ms | {op['pct_change']:+.1f}% |"
                    )
                report.append("")

        # Recommendations
        report.append("## Recommendations")
        report.append("")
        recommendations = self._generate_recommendations(
            metrics_comparison, anomalies_comparison, prometheus_comparison, logs_comparison, traces_comparison
        )
        for i, rec in enumerate(recommendations, 1):
            report.append(f"{i}. {rec}")

        return "\n".join(report)

    def check_failure_conditions(
        self,
        metrics_comparison: Dict[str, Any],
        fail_on_regression: float = None,
        fail_conditions: List[str] = None
    ) -> Dict[str, Any]:
        """
        Check if the comparison fails based on defined conditions.

        Args:
            metrics_comparison: Result from compare_metrics()
            fail_on_regression: Percentage threshold (e.g. 10 for 10%)
            fail_conditions: List of strings like "p99_latency > 500"

        Returns:
            Dict with 'failed' (bool) and 'reasons' (List[str])
        """
        failed = False
        reasons = []

        # 1. Check Regression Threshold
        if fail_on_regression is not None:
            for metric, data in metrics_comparison.items():
                # Only check degradations (not improvements)
                if not data['improved'] and data['pct_change'] > fail_on_regression:
                    # Skip if baseline was 0 and we can't calculate a meaningful % change
                    if data['baseline'] == 0:
                        continue

                    failed = True
                    reasons.append(
                        f"Regression detected: {metric} worsened by {data['pct_change']:.1f}% "
                        f"(Threshold: {fail_on_regression}%)"
                    )

        # 2. Check Absolute Thresholds
        if fail_conditions:
            current_stats = self.current
            for condition in fail_conditions:
                try:
                    # Basic parsing: "p99_latency > 500"
                    # Supports >, <, >=, <=
                    parts = condition.split()
                    if len(parts) != 3:
                        print(f"Warning: Invalid condition format '{condition}'. Expected 'metric op value'")
                        continue

                    metric_name, op, threshold_str = parts[0], parts[1], parts[2]
                    threshold = float(threshold_str)

                    if metric_name not in current_stats:
                        print(f"Warning: Unknown metric '{metric_name}' in condition")
                        continue

                    value = float(current_stats[metric_name])

                    condition_met = False
                    if op == '>':
                        condition_met = value > threshold
                    elif op == '>=':
                        condition_met = value >= threshold
                    elif op == '<':
                        condition_met = value < threshold
                    elif op == '<=':
                        condition_met = value <= threshold

                    if condition_met:
                        failed = True
                        reasons.append(f"Failure condition met: {metric_name} ({value}) {op} {threshold}")

                except Exception as e:
                    print(f"Error parsing condition '{condition}': {e}")

        return {'failed': failed, 'reasons': reasons}

    def _calculate_verdict(self, metrics: Dict[str, Any], anomalies: Dict[str, Any]) -> str:
        """Calculate overall verdict based on comparison."""
        regressions = sum(1 for m in metrics.values() if not m['improved'] and m['pct_change'] != 0)
        improvements = sum(1 for m in metrics.values() if m['improved'])

        anomaly_delta = anomalies['delta']

        if regressions > improvements or anomaly_delta > 5:
            return "⚠️ **REGRESSION DETECTED** - Performance has degraded compared to baseline."
        elif improvements > regressions and anomaly_delta <= 0:
            return "✅ **IMPROVEMENT** - Performance has improved compared to baseline."
        else:
            return "➖ **MIXED RESULTS** - Some metrics improved, others regressed."

    def _generate_recommendations(
        self, metrics, anomalies, prometheus, logs, traces
    ) -> List[str]:
        """Generate actionable recommendations based on comparison."""
        recommendations = []

        # Check for latency regressions
        if metrics.get('p99_latency', {}).get('pct_change', 0) > 10:
            recommendations.append("Investigate P99 latency regression - check for new slow queries or operations")

        # Check for error rate increase
        if metrics.get('error_rate', {}).get('pct_change', 0) > 0:
            recommendations.append("Error rate has increased - review application logs for new error patterns")

        # Check for throughput decrease
        if metrics.get('throughput', {}).get('pct_change', 0) < -5:
            recommendations.append("Throughput has decreased - check for resource bottlenecks or configuration changes")

        # Check for new anomalies
        if anomalies.get('delta', 0) > 0:
            recommendations.append(
                f"New anomalies detected ({anomalies['delta']}) - correlate with recent code or infrastructure changes"
            )

        # Check for resource regressions
        if prometheus:
            for metric, data in prometheus.items():
                if data.get('regression'):
                    recommendations.append(
                        f"{metric.replace('_', ' ').title()} increased significantly - review resource allocation"
                    )

        # Check for new slow operations
        if traces and traces.get('new_slow_operations'):
            recommendations.append(f"New slow operations detected: {', '.join(traces['new_slow_operations'][:3])}")

        if not recommendations:
            recommendations.append("No significant regressions detected - continue monitoring")

        return recommendations
