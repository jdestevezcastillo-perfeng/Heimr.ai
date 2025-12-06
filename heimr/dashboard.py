# Copyright (c) 2025 Juan Estevez Castillo
# Licensed under AGPL v3. Commercial licenses available.
import json
import pandas as pd
from typing import Dict, Any


class DashboardGenerator:
    """
    Generates an interactive HTML dashboard for load test results.
    """

    def __init__(self, df: pd.DataFrame, stats: Dict[str, Any], prom_metrics: Dict[str, Any] = None):
        self.df = df
        self.stats = stats
        self.prom_metrics = prom_metrics

    def generate(self, output_path: str):
        """
        Generates the HTML dashboard and saves it to output_path.
        """
        # Prepare data for charts
        if not self.df.empty:
            df_resampled = self.df.set_index('timestamp_dt').resample('1s').agg({
                'elapsed': ['mean', lambda x: x.quantile(0.95), lambda x: x.quantile(0.99)],
                'success': 'count'
            })
            # Flatten columns
            df_resampled.columns = ['avg_latency', 'p95_latency', 'p99_latency', 'throughput']

            # Calculate errors per second
            errors_resampled = self.df[~self.df['success']].set_index('timestamp_dt').resample('1s').count()['success']
            df_resampled['errors'] = errors_resampled.fillna(0)

            # Fill NaN latencies
            df_resampled['avg_latency'] = df_resampled['avg_latency'].fillna(0)
            df_resampled['p95_latency'] = df_resampled['p95_latency'].fillna(0)
            df_resampled['p99_latency'] = df_resampled['p99_latency'].fillna(0)

            timestamps = df_resampled.index.strftime('%H:%M:%S').tolist()
            avg_latency_data = df_resampled['avg_latency'].round(2).tolist()
            p95_latency_data = df_resampled['p95_latency'].round(2).tolist()
            p99_latency_data = df_resampled['p99_latency'].round(2).tolist()
            throughput_data = df_resampled['throughput'].tolist()
            error_data = df_resampled['errors'].tolist()
        else:
            timestamps = []
            avg_latency_data = []
            p95_latency_data = []
            p99_latency_data = []
            throughput_data = []
            error_data = []

        # Prepare Prometheus data
        cpu_data = []
        mem_data = []
        prom_timestamps = []

        if self.prom_metrics:
            if 'cpu_usage' in self.prom_metrics and self.prom_metrics['cpu_usage']:
                cpu_values = self.prom_metrics['cpu_usage'][0]['values']
                prom_timestamps = [pd.to_datetime(float(v[0]), unit='s').strftime('%H:%M:%S') for v in cpu_values]
                cpu_data = [float(v[1]) * 100 for v in cpu_values]

            if 'memory_usage' in self.prom_metrics and self.prom_metrics['memory_usage']:
                mem_values = self.prom_metrics['memory_usage'][0]['values']
                # If timestamps differ slightly, we might need to align, but usually they are scraped together
                # For simplicity, assume same timestamps or use CPU timestamps
                if not prom_timestamps:
                    prom_timestamps = [pd.to_datetime(float(v[0]), unit='s').strftime('%H:%M:%S') for v in mem_values]
                mem_data = [float(v[1]) / (1024 * 1024) for v in mem_values]

        html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Heimr Analysis Dashboard</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 0; padding: 20px; background-color: #f4f4f9; }}
        .container {{ max_width: 1400px; margin: 0 auto; }}
        .header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }}
        .kpi-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin-bottom: 20px; }}
        .kpi-card {{ background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); text-align: center; }}
        .kpi-value {{ font-size: 24px; font-weight: bold; color: #2c3e50; }}
        .kpi-label {{ color: #7f8c8d; font-size: 14px; }}

        .charts-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(450px, 1fr)); gap: 20px; }}
        .chart-card {{ background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        h1 {{ color: #2c3e50; }}
        h3 {{ color: #34495e; margin-top: 0; margin-bottom: 15px; text-align: center; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Heimr Analysis Dashboard</h1>
            <div>{self.stats.get('start_time')} - {self.stats.get('end_time')}</div>
        </div>

        <div class="kpi-grid">
            <div class="kpi-card">
                <div class="kpi-value">{self.stats.get('total_requests')}</div>
                <div class="kpi-label">Total Requests</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-value">{self.stats.get('avg_latency', 0):.2f} ms</div>
                <div class="kpi-label">Avg Latency</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-value">{self.stats.get('p99_latency', 0):.2f} ms</div>
                <div class="kpi-label">P99 Latency</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-value">{self.stats.get('error_rate', 0):.2f}%</div>
                <div class="kpi-label">Error Rate</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-value">{self.stats.get('throughput', 0):.2f} req/s</div>
                <div class="kpi-label">Throughput</div>
            </div>
        </div>

        <div class="charts-grid">
            <div class="chart-card">
                <h3>Latency (ms)</h3>
                <canvas id="latencyChart"></canvas>
            </div>
            <div class="chart-card">
                <h3>Throughput (req/s)</h3>
                <canvas id="throughputChart"></canvas>
            </div>
            <div class="chart-card">
                <h3>Errors (count)</h3>
                <canvas id="errorChart"></canvas>
            </div>
            <div class="chart-card">
                <h3>CPU Usage (%)</h3>
                <canvas id="cpuChart"></canvas>
            </div>
            <div class="chart-card">
                <h3>Memory Usage (MB)</h3>
                <canvas id="memChart"></canvas>
            </div>
        </div>
    </div>

    <script>
        const commonOptions = {{
            responsive: true,
            interaction: {{ mode: 'index', intersect: false }},
            plugins: {{ legend: {{ position: 'bottom' }} }},
            scales: {{ x: {{ ticks: {{ maxTicksLimit: 10 }} }} }}
        }};

        // Latency Chart
        new Chart(document.getElementById('latencyChart'), {{
            type: 'line',
            data: {{
                labels: {json.dumps(timestamps)},
                datasets: [
                    {{ label: 'Avg', data: {json.dumps(avg_latency_data)}, borderColor: '#3498db', tension: 0.1, pointRadius: 0 }},
                    {{ label: 'P95', data: {json.dumps(p95_latency_data)}, borderColor: '#f39c12', tension: 0.1, pointRadius: 0 }},
                    {{ label: 'P99', data: {json.dumps(p99_latency_data)}, borderColor: '#e74c3c', tension: 0.1, pointRadius: 0 }}
                ]
            }},
            options: commonOptions
        }});

        // Throughput Chart
        new Chart(document.getElementById('throughputChart'), {{
            type: 'line',
            data: {{
                labels: {json.dumps(timestamps)},
                datasets: [
                    {{ label: 'Throughput', data: {json.dumps(throughput_data)}, borderColor: '#2ecc71', backgroundColor: 'rgba(46, 204, 113, 0.2)', fill: true, tension: 0.1, pointRadius: 0 }}
                ]
            }},
            options: commonOptions
        }});

        // Error Chart
        new Chart(document.getElementById('errorChart'), {{
            type: 'bar',
            data: {{
                labels: {json.dumps(timestamps)},
                datasets: [
                    {{ label: 'Errors', data: {json.dumps(error_data)}, backgroundColor: '#e74c3c' }}
                ]
            }},
            options: commonOptions
        }});

        // CPU Chart
        new Chart(document.getElementById('cpuChart'), {{
            type: 'line',
            data: {{
                labels: {json.dumps(prom_timestamps)},
                datasets: [
                    {{ label: 'CPU Usage', data: {json.dumps(cpu_data)}, borderColor: '#9b59b6', backgroundColor: 'rgba(155, 89, 182, 0.2)', fill: true, tension: 0.1, pointRadius: 0 }}
                ]
            }},
            options: {{
                ...commonOptions,
                scales: {{ y: {{ min: 0, max: 100 }} }}
            }}
        }});

        // Memory Chart
        new Chart(document.getElementById('memChart'), {{
            type: 'line',
            data: {{
                labels: {json.dumps(prom_timestamps)},
                datasets: [
                    {{ label: 'Memory Usage', data: {json.dumps(mem_data)}, borderColor: '#f1c40f', backgroundColor: 'rgba(241, 196, 15, 0.2)', fill: true, tension: 0.1, pointRadius: 0 }}
                ]
            }},
            options: commonOptions
        }});
    </script>
</body>
</html>
"""
        with open(output_path, 'w') as f:
            f.write(html_content)
        print(f"✅ Dashboard saved to: {output_path}")
