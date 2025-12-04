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
        # Resample data to 1-second intervals for cleaner charts
        if not self.df.empty:
            df_resampled = self.df.set_index('timestamp_dt').resample('1s').agg({
                'elapsed': 'mean',
                'success': 'count'  # Total requests per second
            }).rename(columns={'success': 'throughput'})
            
            # Calculate errors per second
            errors_resampled = self.df[~self.df['success']].set_index('timestamp_dt').resample('1s').count()['success']
            df_resampled['errors'] = errors_resampled.fillna(0)
            
            # Fill NaN latencies (seconds with no requests)
            df_resampled['elapsed'] = df_resampled['elapsed'].fillna(0)
            
            timestamps = df_resampled.index.strftime('%H:%M:%S').tolist()
            latency_data = df_resampled['elapsed'].round(2).tolist()
            throughput_data = df_resampled['throughput'].tolist()
            error_data = df_resampled['errors'].tolist()
        else:
            timestamps = []
            latency_data = []
            throughput_data = []
            error_data = []

        # Prepare Prometheus data (if available)
        cpu_data = []
        mem_data = []
        prom_timestamps = []
        
        if self.prom_metrics:
            if 'cpu_usage' in self.prom_metrics and self.prom_metrics['cpu_usage']:
                # Assuming values are [timestamp, value]
                cpu_values = self.prom_metrics['cpu_usage'][0]['values']
                # Convert timestamps to readable format
                prom_timestamps = [pd.to_datetime(float(v[0]), unit='s').strftime('%H:%M:%S') for v in cpu_values]
                cpu_data = [float(v[1]) * 100 for v in cpu_values] # Convert to %
            
            if 'memory_usage' in self.prom_metrics and self.prom_metrics['memory_usage']:
                mem_values = self.prom_metrics['memory_usage'][0]['values']
                mem_data = [float(v[1]) / (1024*1024) for v in mem_values] # Convert to MB

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
        .container {{ max_width: 1200px; margin: 0 auto; }}
        .header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }}
        .card {{ background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); margin-bottom: 20px; }}
        .kpi-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin-bottom: 20px; }}
        .kpi-card {{ background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); text-align: center; }}
        .kpi-value {{ font-size: 24px; font-weight: bold; color: #2c3e50; }}
        .kpi-label {{ color: #7f8c8d; font-size: 14px; }}
        h1 {{ color: #2c3e50; }}
        h2 {{ color: #34495e; margin-top: 0; }}
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

        <div class="card">
            <h2>Latency & Throughput</h2>
            <canvas id="mainChart"></canvas>
        </div>

        <div class="card">
            <h2>System Metrics (CPU & Memory)</h2>
            <canvas id="systemChart"></canvas>
        </div>
    </div>

    <script>
        const ctx = document.getElementById('mainChart').getContext('2d');
        new Chart(ctx, {{
            type: 'line',
            data: {{
                labels: {json.dumps(timestamps)},
                datasets: [
                    {{
                        label: 'Avg Latency (ms)',
                        data: {json.dumps(latency_data)},
                        borderColor: '#3498db',
                        yAxisID: 'y',
                        tension: 0.1
                    }},
                    {{
                        label: 'Throughput (req/s)',
                        data: {json.dumps(throughput_data)},
                        borderColor: '#2ecc71',
                        yAxisID: 'y1',
                        tension: 0.1
                    }},
                    {{
                        label: 'Errors (count)',
                        data: {json.dumps(error_data)},
                        borderColor: '#e74c3c',
                        yAxisID: 'y1',
                        tension: 0.1
                    }}
                ]
            }},
            options: {{
                responsive: true,
                interaction: {{ mode: 'index', intersect: false }},
                scales: {{
                    y: {{ type: 'linear', display: true, position: 'left', title: {{ display: true, text: 'Latency (ms)' }} }},
                    y1: {{ type: 'linear', display: true, position: 'right', title: {{ display: true, text: 'Throughput / Errors' }}, grid: {{ drawOnChartArea: false }} }}
                }}
            }}
        }});

        const sysCtx = document.getElementById('systemChart').getContext('2d');
        new Chart(sysCtx, {{
            type: 'line',
            data: {{
                labels: {json.dumps(prom_timestamps)},
                datasets: [
                    {{
                        label: 'CPU Usage (%)',
                        data: {json.dumps(cpu_data)},
                        borderColor: '#9b59b6',
                        yAxisID: 'y',
                        tension: 0.1
                    }},
                    {{
                        label: 'Memory Usage (MB)',
                        data: {json.dumps(mem_data)},
                        borderColor: '#f1c40f',
                        yAxisID: 'y1',
                        tension: 0.1
                    }}
                ]
            }},
            options: {{
                responsive: true,
                interaction: {{ mode: 'index', intersect: false }},
                scales: {{
                    y: {{ type: 'linear', display: true, position: 'left', title: {{ display: true, text: 'CPU (%)' }} }},
                    y1: {{ type: 'linear', display: true, position: 'right', title: {{ display: true, text: 'Memory (MB)' }}, grid: {{ drawOnChartArea: false }} }}
                }}
            }}
        }});
    </script>
</body>
</html>
"""
        with open(output_path, 'w') as f:
            f.write(html_content)
        print(f"✅ Dashboard saved to: {output_path}")
