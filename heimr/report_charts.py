# Copyright (c) 2025 Juan Estevez Castillo
# Licensed under AGPL v3. Commercial licenses available.
# See LICENSE or https://www.gnu.org/licenses/agpl-3.0.html
"""
Report Chart Generator for Heimr.
Generates interactive Plotly charts for performance reports.
"""
import base64
import io
from typing import Dict, Any, List, Optional
import pandas as pd
import numpy as np

try:
    import plotly.graph_objects as go
    import plotly.express as px
    from plotly.subplots import make_subplots
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False


# Color scheme matching Heimr.ai website branding
COLORS = {
    'primary': '#00d9ff',      # Cyan from website
    'secondary': '#00ffa3',    # Teal from website  
    'success': '#22C55E',      # Green
    'warning': '#F59E0B',      # Amber
    'danger': '#EF4444',       # Red
    'muted': 'rgba(138, 146, 176, 0.5)',  # text-secondary from website
    'background': '#0a192f',   # bg-primary from website
    'text': '#e6f1ff',         # text-primary from website
}


class ReportCharts:
    """Generate Plotly charts for Heimr reports."""
    
    # Output mode: 'html' for web (interactive), 'image' for PDF/CLI (static)
    output_mode = 'html'  # Default to interactive HTML
    
    @classmethod
    def set_output_mode(cls, mode: str):
        """Set output mode: 'html' for interactive, 'image' for static PNG."""
        cls.output_mode = mode
    
    @staticmethod
    def _get_layout(title: str, height: int = 400) -> dict:
        """Get standard layout config."""
        return {
            'title': {'text': title, 'font': {'color': COLORS['text'], 'size': 16}},
            'paper_bgcolor': COLORS['background'],
            'plot_bgcolor': COLORS['background'],
            'font': {'color': COLORS['text']},
            'height': height,
            'margin': {'l': 60, 'r': 40, 't': 60, 'b': 60},
            'xaxis': {'gridcolor': 'rgba(255,255,255,0.1)', 'zerolinecolor': 'rgba(255,255,255,0.2)'},
            'yaxis': {'gridcolor': 'rgba(255,255,255,0.1)', 'zerolinecolor': 'rgba(255,255,255,0.2)'},
            'legend': {'bgcolor': 'rgba(0,0,0,0.3)', 'bordercolor': 'rgba(255,255,255,0.1)'},
        }
    
    @classmethod
    def _fig_to_output(cls, fig) -> Optional[str]:
        """Convert figure to output format (HTML or Base64 PNG)."""
        if cls.output_mode == 'html':
            return fig.to_html(include_plotlyjs='cdn', full_html=False)
        else:
            # Static PNG as Base64 for Markdown embedding
            try:
                img_bytes = fig.to_image(format='png', width=800, height=400, scale=2)
                b64 = base64.b64encode(img_bytes).decode('utf-8')
                return f'![Chart](data:image/png;base64,{b64})'
            except Exception as e:
                # Fallback to HTML if image export fails
                return fig.to_html(include_plotlyjs='cdn', full_html=False)
    
    @classmethod
    def latency_histogram(cls, df: pd.DataFrame) -> Optional[str]:
        """
        Generate latency distribution histogram with per-endpoint breakdown and percentiles.
        Total distribution is also available as a toggleable trace.
        """
        if not PLOTLY_AVAILABLE or df.empty or 'elapsed' not in df.columns:
            return None
            
        elapsed = df['elapsed'].dropna()
        p50 = elapsed.quantile(0.50)
        p95 = elapsed.quantile(0.95)
        p99 = elapsed.quantile(0.99)
        
        fig = go.Figure()

        # Calculate appropriate bin size globally regarding the total range
        # using numpy's auto binning or fixed number
        counts, bins = np.histogram(elapsed, bins=50)
        max_count = counts.max()
        
        # 1. Add "Total" trace (optional, visible by default or toggleable)
        # We put it first or last? If stacked, Total might obscure? 
        # Actually total encompasses all. We can use 'overlay' for Total vs Stacked? 
        # Mixing barmodes is tricky. Let's just create 'Total' as an outline or separate trace group.
        # User asked to "add the total request count as an option".
        
        # Let's add Total as a filled area or a separate histogram in 'overlay' mode but muted?
        # Or simpler: just let the stack BE the total. 
        # But highlighting "Total" usually means seeing the aggregate shape clearly.
        # Let's add Total as a trace that is hidden by default ('legendonly'), 
        # so user can enable it to compare everything against total profile.
        
        fig.add_trace(go.Histogram(
            x=elapsed,
            nbinsx=50,
            marker_color='rgba(200, 200, 200, 0.3)',
            marker_line_color='rgba(255, 255, 255, 0.5)',
            opacity=0.5,
            name='Total (All Requests)',
            legendgroup='total',
            hovertemplate='Total<br>%{x:.0f}ms: %{y} requests<extra></extra>',
            visible='legendonly'  # Default to hidden to let colored stack shine? Or visible? 
                                  # User said "add option to highlight". legendonly is perfect.
        ))
        
        # Add Global Percentiles (grouped with Total)
        for pct, val, color, name in [
            (50, p50, COLORS['success'], 'Total P50'),
            (95, p95, COLORS['warning'], 'Total P95'),
            (99, p99, COLORS['danger'], 'Total P99'),
        ]:
            fig.add_trace(go.Scatter(
                x=[val, val], y=[0, max_count * 1.1],
                mode='lines',
                line=dict(color=color, width=2, dash='dash'),
                name=f'{name}: {val:.0f}ms',
                legendgroup='total',
                visible='legendonly',
                hoverinfo='name'
            ))

        layout_update = {}
        
        # 2. Endpoint Traces
        if 'endpoint' in df.columns:
            endpoints = sorted(df['endpoint'].unique())
            colors = px.colors.qualitative.Plotly
            layout_update = {'barmode': 'stack'}
            
            for i, endpoint in enumerate(endpoints):
                # Filter data
                e_data = df[df['endpoint'] == endpoint]['elapsed'].dropna()
                if e_data.empty:
                    continue
                    
                # Calculate endpoint specific P95
                e_p95 = e_data.quantile(0.95)
                
                # Calculate max height roughly for this endpoint for the line
                e_counts, _ = np.histogram(e_data, bins=bins) # Use global bins for consistency
                e_max = e_counts.max()
                
                color = colors[i % len(colors)]
                
                # Histogram Trace
                fig.add_trace(go.Histogram(
                    x=e_data,
                    nbinsx=50, # Plotly handles binning, but consistent x-range helps
                    marker_color=color,
                    opacity=0.8,
                    name=endpoint,
                    legendgroup=endpoint,
                    hovertemplate=f'<b>{endpoint}</b><br>%{{x:.0f}}ms: %{{y}} requests<extra></extra>'
                ))
                
                # Percentile Line (P95) grouped with endpoint
                fig.add_trace(go.Scatter(
                    x=[e_p95, e_p95], 
                    y=[0, e_max * 1.2], # Go slightly above bar
                    mode='lines',
                    line=dict(color=color, width=2, dash='dot'),
                    name=f'{endpoint} P95: {e_p95:.0f}ms',
                    # legendgroup=endpoint,  <-- REMOVED to separate control
                    showlegend=True,         # <-- CHANGED to True to list separately
                    hoverinfo='name'
                ))
        else:
             # Fallback: Make total visible if we can't show endpoints
             fig.update_traces(selector=dict(name='Total (All Requests)'), visible=True)

        layout = cls._get_layout('Response Time Distribution', height=450)
        layout['bargap'] = 0.1
        layout.update(layout_update)
        
        fig.update_layout(**layout)
        fig.update_xaxes(title_text='Response Time (ms)')
        fig.update_yaxes(title_text='Request Count')
        
        return cls._fig_to_output(fig)
    
    @classmethod
    def response_time_over_time(cls, df: pd.DataFrame) -> Optional[str]:
        """
        Generate response time vs time line chart.
        Returns HTML string.
        """
        if not PLOTLY_AVAILABLE or df.empty:
            return None
            
        if 'timestamp_dt' not in df.columns or 'elapsed' not in df.columns:
            return None
            
        # Resample to reduce points for large datasets
        df_sorted = df.sort_values('timestamp_dt')
        
        # Group by time buckets (10 second intervals)
        df_sorted['time_bucket'] = df_sorted['timestamp_dt'].dt.floor('10s')
        agg = df_sorted.groupby('time_bucket').agg({
            'elapsed': ['mean', 'quantile']
        }).reset_index()
        agg.columns = ['time', 'avg', 'p95']
        
        # Recalculate P95 properly
        p95_data = df_sorted.groupby('time_bucket')['elapsed'].quantile(0.95).reset_index()
        p95_data.columns = ['time', 'p95']
        agg = agg.merge(p95_data, on='time', suffixes=('_drop', ''))
        agg = agg.drop(columns=['p95_drop'], errors='ignore')
        
        # Calculate throughput for the same buckets
        rps = df_sorted.groupby('time_bucket').size().reset_index(name='requests')
        rps['rps'] = rps['requests'] / 10  # 10 second buckets
        rps.columns = ['time', 'requests', 'rps']  # Rename for merge
        
        # Merge throughput into agg
        agg = agg.merge(rps, on='time', how='left').fillna(0)
        
        fig = make_subplots(specs=[[{"secondary_y": True}]])
        
        # Throughput (background, muted)
        fig.add_trace(go.Scatter(
            x=agg['time'], y=agg['rps'],
            mode='lines',
            fill='tozeroy',
            name='Throughput (RPS)',
            line=dict(color=COLORS['muted'], width=1),
            fillcolor='rgba(156, 163, 175, 0.1)',
            hovertemplate='%{y:.1f} req/s<extra></extra>'
        ), secondary_y=True)
        
        fig.add_trace(go.Scatter(
            x=agg['time'], y=agg['avg'],
            mode='lines',
            name='Avg Response Time',
            line=dict(color=COLORS['primary'], width=2),
            hovertemplate='%{x}<br>Avg: %{y:.0f}ms<extra></extra>'
        ), secondary_y=False)
        
        fig.add_trace(go.Scatter(
            x=agg['time'], y=agg['p95'],
            mode='lines',
            name='P95',
            line=dict(color=COLORS['warning'], width=2, dash='dot'),
            hovertemplate='%{x}<br>P95: %{y:.0f}ms<extra></extra>'
        ), secondary_y=False)
        
        layout = cls._get_layout('Response Time Over Load')
        layout['yaxis2'] = {'gridcolor': 'rgba(255,255,255,0.05)', 'showgrid': False}
        fig.update_layout(**layout)
        fig.update_xaxes(title_text='Time')
        fig.update_yaxes(title_text='Response Time (ms)', secondary_y=False)
        fig.update_yaxes(title_text='Throughput (RPS)', secondary_y=True)
        
        return cls._fig_to_output(fig)

    @classmethod
    def response_time_by_endpoint(cls, df: pd.DataFrame) -> Optional[str]:
        """
        Generate response time vs time line chart for each endpoint.
        Returns HTML string.
        """
        if not PLOTLY_AVAILABLE or df.empty:
            return None
            
        if 'timestamp_dt' not in df.columns or 'elapsed' not in df.columns or 'endpoint' not in df.columns:
            return None
            
        # Resample to reduce points for large datasets
        df_sorted = df.sort_values('timestamp_dt')
        
        # Group by time buckets (10 second intervals) and endpoint
        df_sorted['time_bucket'] = df_sorted['timestamp_dt'].dt.floor('10s')
        
        agg = df_sorted.groupby(['time_bucket', 'endpoint']).agg({
            'elapsed': 'mean'
        }).reset_index()
        
        # Calculate global throughput
        rps = df_sorted.groupby('time_bucket').size().reset_index(name='requests')
        rps['rps'] = rps['requests'] / 10
        
        fig = make_subplots(specs=[[{"secondary_y": True}]])
        
        # Throughput (background, muted)
        fig.add_trace(go.Scatter(
            x=rps['time_bucket'], y=rps['rps'],
            mode='lines',
            fill='tozeroy',
            name='Total Throughput (RPS)',
            line=dict(color=COLORS['muted'], width=1),
            fillcolor='rgba(156, 163, 175, 0.1)',
            hovertemplate='%{y:.1f} req/s<extra></extra>'
        ), secondary_y=True)
        
        # Get unique endpoints
        endpoints = sorted(agg['endpoint'].unique())
        
        # Generate color palette
        colors = px.colors.qualitative.Plotly
        
        for i, endpoint in enumerate(endpoints):
            endpoint_data = agg[agg['endpoint'] == endpoint]
            color = colors[i % len(colors)]
            
            fig.add_trace(go.Scatter(
                x=endpoint_data['time_bucket'], 
                y=endpoint_data['elapsed'],
                mode='lines',
                name=endpoint,
                line=dict(color=color, width=2),
                hovertemplate='%{x}<br>' + f'<b>{endpoint}</b>' + '<br>Avg: %{y:.0f}ms<extra></extra>'
            ), secondary_y=False)
        
        layout = cls._get_layout('Response Time by Endpoint')
        layout['hovermode'] = 'closest'
        layout['yaxis2'] = {'gridcolor': 'rgba(255,255,255,0.05)', 'showgrid': False} 
        
        fig.update_layout(**layout)
        fig.update_xaxes(title_text='Time')
        fig.update_yaxes(title_text='Avg Response Time (ms)', secondary_y=False)
        fig.update_yaxes(title_text='Throughput (RPS)', secondary_y=True)
        
        return cls._fig_to_output(fig)

    @classmethod
    def throughput_by_endpoint(cls, df: pd.DataFrame) -> Optional[str]:
        """
        Generate throughput (RPS) vs time line chart for each endpoint.
        Returns HTML string.
        """
        if not PLOTLY_AVAILABLE or df.empty:
            return None
            
        if 'timestamp_dt' not in df.columns or 'endpoint' not in df.columns:
            return None
            
        # Resample to reduce points for large datasets
        df_sorted = df.sort_values('timestamp_dt')
        
        # Group by time buckets (10 second intervals) and endpoint
        df_sorted['time_bucket'] = df_sorted['timestamp_dt'].dt.floor('10s')
        
        # Count requests per bucket per endpoint
        agg = df_sorted.groupby(['time_bucket', 'endpoint']).size().reset_index(name='requests')
        agg['rps'] = agg['requests'] / 10  # 10s buckets
        
        fig = go.Figure()
        
        # Get unique endpoints
        endpoints = sorted(agg['endpoint'].unique())
        
        # Generate color palette
        colors = px.colors.qualitative.Plotly
        
        for i, endpoint in enumerate(endpoints):
            endpoint_data = agg[agg['endpoint'] == endpoint]
            color = colors[i % len(colors)]
            
            fig.add_trace(go.Scatter(
                x=endpoint_data['time_bucket'], 
                y=endpoint_data['rps'],
                mode='lines',
                name=endpoint,
                line=dict(color=color, width=2),
                hovertemplate='%{x}<br>' + f'<b>{endpoint}</b>' + '<br>%{y:.1f} req/s<extra></extra>'
            ))
        
        layout = cls._get_layout('Throughput by Endpoint')
        layout['hovermode'] = 'closest'
        
        fig.update_layout(**layout)
        fig.update_xaxes(title_text='Time')
        fig.update_yaxes(title_text='Throughput (RPS)')
        
        return cls._fig_to_output(fig)
    
    @classmethod
    def throughput_over_time(cls, df: pd.DataFrame) -> Optional[str]:
        """
        Generate throughput (RPS) vs time line chart.
        Returns HTML string.
        """
        if not PLOTLY_AVAILABLE or df.empty or 'timestamp_dt' not in df.columns:
            return None
            
        df_sorted = df.sort_values('timestamp_dt')
        df_sorted['time_bucket'] = df_sorted['timestamp_dt'].dt.floor('10s')
        
        rps = df_sorted.groupby('time_bucket').size().reset_index(name='requests')
        rps['rps'] = rps['requests'] / 10  # 10 second buckets
        
        fig = go.Figure()
        
        fig.add_trace(go.Scatter(
            x=rps['time_bucket'], y=rps['rps'],
            mode='lines',
            fill='tozeroy',
            name='Throughput',
            line=dict(color=COLORS['secondary'], width=2),
            fillcolor='rgba(124, 58, 237, 0.3)',
            hovertemplate='%{x}<br>%{y:.1f} req/s<extra></extra>'
        ))
        
        fig.update_layout(**cls._get_layout('Throughput Over Time'))
        fig.update_xaxes(title_text='Time')
        fig.update_yaxes(title_text='Requests/Second')
        
        return cls._fig_to_output(fig)
    
    @classmethod
    def error_rate_with_throughput(cls, df: pd.DataFrame) -> Optional[str]:
        """
        Generate error rate vs time with throughput overlay (muted).
        Returns HTML string.
        """
        if not PLOTLY_AVAILABLE or df.empty:
            return None
            
        if 'timestamp_dt' not in df.columns or 'success' not in df.columns:
            return None
            
        df_sorted = df.sort_values('timestamp_dt')
        df_sorted['time_bucket'] = df_sorted['timestamp_dt'].dt.floor('10s')
        
        agg = df_sorted.groupby('time_bucket').agg({
            'success': ['count', lambda x: (~x).sum()]
        }).reset_index()
        agg.columns = ['time', 'total', 'errors']
        agg['error_pct'] = (agg['errors'] / agg['total']) * 100
        agg['rps'] = agg['total'] / 10
        
        fig = make_subplots(specs=[[{"secondary_y": True}]])
        
        # Throughput (background, muted)
        fig.add_trace(go.Scatter(
            x=agg['time'], y=agg['rps'],
            mode='lines',
            fill='tozeroy',
            name='Throughput (RPS)',
            line=dict(color=COLORS['muted'], width=1),
            fillcolor='rgba(156, 163, 175, 0.1)',
            hovertemplate='%{y:.1f} req/s<extra></extra>'
        ), secondary_y=True)
        
        # Error Rate (foreground)
        fig.add_trace(go.Scatter(
            x=agg['time'], y=agg['error_pct'],
            mode='lines+markers',
            name='Error Rate',
            line=dict(color=COLORS['danger'], width=3),
            marker=dict(size=6),
            hovertemplate='%{x}<br>Error: %{y:.2f}%<extra></extra>'
        ), secondary_y=False)
        
        layout = cls._get_layout('Error Rate Over Time')
        layout['yaxis2'] = {'gridcolor': 'rgba(255,255,255,0.05)', 'showgrid': False}
        fig.update_layout(**layout)
        fig.update_xaxes(title_text='Time')
        fig.update_yaxes(title_text='Error Rate (%)', secondary_y=False)
        fig.update_yaxes(title_text='Throughput (RPS)', secondary_y=True)
        
        return cls._fig_to_output(fig)
    
    @classmethod
    def resource_utilization(cls, metrics: Dict[str, Any], metric_type: str = 'cpu', throughput_df: pd.DataFrame = None) -> Optional[str]:
        """
        Generate resource utilization chart from Prometheus metrics with optional throughput overlay.
        metric_type: 'cpu', 'memory', 'gpu', 'disk', 'network'
        Returns HTML string.
        """
        if not PLOTLY_AVAILABLE or not metrics:
            return None
            
        from heimr.prometheus_normalizer import PrometheusNormalizer
        categorized = PrometheusNormalizer.categorize_metrics(metrics)
        
        category_data = categorized.get(metric_type, {})
        if not category_data:
            return None
            
        # Initialize Figure (with secondary axis if throughput provided)
        if throughput_df is not None and not throughput_df.empty:
            fig = make_subplots(specs=[[{"secondary_y": True}]])
            
            # Add Throughput (background, muted)
            fig.add_trace(go.Scatter(
                x=throughput_df['time'], 
                y=throughput_df['rps'],
                mode='lines',
                fill='tozeroy',
                name='Load (RPS)',
                line=dict(color=COLORS['muted'], width=1),
                fillcolor='rgba(156, 163, 175, 0.1)',
                hovertemplate='%{y:.1f} req/s<extra></extra>'
            ), secondary_y=True)
            
            secondary_axis = True
        else:
            fig = go.Figure()
            secondary_axis = False
        
        for metric_name, metric_data in category_data.items():
            series_data = PrometheusNormalizer.extract_time_series(metric_data)
            if not series_data:
                continue
                
            # Group by unique label combination
            label_groups = {}
            for point in series_data:
                # Extract meaningful label based on metric type
                if metric_type == 'http':
                    # For HTTP metrics, prefer status, method, or endpoint
                    val = (
                        point['labels'].get('status') or 
                        point['labels'].get('code') or
                        point['labels'].get('method') or
                        point['labels'].get('endpoint') or
                        point['labels'].get('handler') or
                        metric_name.split('_')[-1]  # Use last part of metric name
                    )
                    # Include metric suffix for clarity (e.g. "requests_total - 200")
                    # Or simple "total", "sum" is ambiguous.
                    # Let's check if val implies type, if not, prepend concise metric hint.
                    if val in ['total', 'sum', 'count', 'bucket']:
                         # Shorten metric name: http_requests_total -> requests
                         short_name = metric_name.replace('http_', '').replace('_total', '')
                         label_key = f"{short_name} ({val})"
                    else:
                        label_key = val
                        
                elif metric_type == 'db':
                    # For DB metrics, prefer database name or operation
                    label_key = (
                        point['labels'].get('database') or
                        point['labels'].get('operation') or
                        point['labels'].get('pod', point['labels'].get('instance', 'database'))
                    )
                else:
                    # For other metrics, use pod/instance
                    label_key = point['labels'].get('pod', point['labels'].get('instance', metric_name))
                
                if label_key not in label_groups:
                    label_groups[label_key] = {'x': [], 'y': []}
                label_groups[label_key]['x'].append(point['timestamp'])
                label_groups[label_key]['y'].append(point['value'])
            
            for label, data in label_groups.items():
                # Convert values based on metric type
                y_values = data['y']
                if metric_type == 'cpu':
                    y_values = [v * 100 for v in y_values]  # As percentage
                elif metric_type == 'memory':
                    y_values = [v / (1024**2) for v in y_values]  # As MB
                elif metric_type in ('disk', 'network'):
                    y_values = [v / (1024**2) for v in y_values]  # As MB/s
                    
                trace = go.Scatter(
                    x=[pd.Timestamp(t, unit='s') for t in data['x']],
                    y=y_values,
                    mode='lines',
                    name=f'{label}',
                    hovertemplate='%{x}<br>%{y:.1f}<extra></extra>'
                )
                
                if secondary_axis:
                    fig.add_trace(trace, secondary_y=False)
                else:
                    fig.add_trace(trace)
        
        titles = {
            'cpu': 'CPU Utilization (%)', 
            'memory': 'Memory Usage (MB)', 
            'gpu': 'GPU Utilization',
            'disk': 'Disk I/O (MB/s)',
            'network': 'Network I/O (MB/s)',
            'db': 'Database Metrics',
            'messaging': 'Messaging/Streaming',
            'http': 'HTTP/Application Metrics'
        }
        
        layout_name = titles.get(metric_type, 'Resource Utilization')
        layout = cls._get_layout(layout_name)
        
        if secondary_axis:
            layout['yaxis2'] = {'gridcolor': 'rgba(255,255,255,0.05)', 'showgrid': False, 'title': 'Load (RPS)'}
            fig.update_layout(**layout)
            fig.update_yaxes(title_text=titles.get(metric_type, 'Value'), secondary_y=False)
            fig.update_yaxes(title_text='Load (RPS)', secondary_y=True)
        else:
            fig.update_layout(**layout)
            fig.update_yaxes(title_text=titles.get(metric_type, 'Value'))
            
        fig.update_xaxes(title_text='Time')
        
        return cls._fig_to_output(fig)
    
    @classmethod
    def to_png_base64(cls, html: str) -> Optional[str]:
        """
        Convert Plotly HTML to PNG base64 for PDF embedding.
        Requires kaleido.
        """
        if not html:
            return None
            
        try:
            # Extract figure from HTML and re-render as PNG
            # This is a simplified approach - for full support, we'd parse the HTML
            # For now, return None and use HTML in reports (PDF will handle it)
            return None
        except Exception:
            return None
    
    @classmethod
    def thread_state_pie(cls, thread_dump: Dict[str, Any]) -> Optional[str]:
        """
        Generate pie chart of JVM thread states (RUNNABLE, BLOCKED, WAITING, etc.).
        
        Args:
            thread_dump: Parsed thread dump data from ThreadDumpParser.parse()
        
        Returns:
            HTML string with Plotly pie chart, or None if no data
        """
        if not PLOTLY_AVAILABLE or not thread_dump:
            return None
            
        summary = thread_dump.get('summary', {})
        if not summary:
            return None
        
        # Extract thread state counts
        states = ['runnable', 'blocked', 'waiting', 'timed_waiting']
        labels = ['RUNNABLE', 'BLOCKED', 'WAITING', 'TIMED_WAITING']
        values = [summary.get(state, 0) for state in states]
        
        # Only include states with non-zero values
        filtered = [(l, v) for l, v in zip(labels, values) if v > 0]
        if not filtered:
            return None
            
        labels, values = zip(*filtered)
        
        # Color mapping for thread states
        color_map = {
            'RUNNABLE': COLORS['success'],      # Green - healthy
            'BLOCKED': COLORS['danger'],        # Red - problematic
            'WAITING': COLORS['warning'],       # Amber - neutral
            'TIMED_WAITING': COLORS['primary'], # Cyan - normal
        }
        colors = [color_map.get(l, COLORS['muted']) for l in labels]
        
        fig = go.Figure(data=[go.Pie(
            labels=labels,
            values=values,
            hole=0.4,  # Donut chart
            marker=dict(colors=colors, line=dict(color=COLORS['background'], width=2)),
            textinfo='label+percent',
            textfont=dict(color=COLORS['text']),
            hovertemplate='%{label}: %{value} threads (%{percent})<extra></extra>'
        )])
        
        # Add center annotation with total
        total_threads = summary.get('total_threads', sum(values))
        
        layout = cls._get_layout('JVM Thread States', height=400)
        layout['annotations'] = [dict(
            text=f'<b>{total_threads}</b><br>threads',
            x=0.5, y=0.5,
            font=dict(size=16, color=COLORS['text']),
            showarrow=False
        )]
        
        # Add deadlock warning annotation if applicable
        if summary.get('has_deadlocks'):
            layout['annotations'].append(dict(
                text=f'⚠️ {summary.get("deadlock_count", 0)} DEADLOCK(S) DETECTED',
                x=0.5, y=-0.15,
                font=dict(size=14, color=COLORS['danger']),
                showarrow=False
            ))
        
        fig.update_layout(**layout)
        
        return cls._fig_to_output(fig)
    
    @classmethod
    def gc_pause_timeline(cls, gc_log: Dict[str, Any]) -> Optional[str]:
        """
        Generate timeline of GC pause events with pause duration on Y-axis.
        
        Args:
            gc_log: Parsed GC log data from GCLogParser.parse()
        
        Returns:
            HTML string with Plotly timeline chart, or None if no data
        """
        if not PLOTLY_AVAILABLE or not gc_log:
            return None
            
        timeline = gc_log.get('timeline', [])
        if not timeline:
            return None
        
        # Separate Young GC and Full GC events
        young_gc = [e for e in timeline if not e.get('is_full_gc', False)]
        full_gc = [e for e in timeline if e.get('is_full_gc', False)]
        
        fig = go.Figure()
        
        # Young GC events (smaller, green/cyan)
        if young_gc:
            fig.add_trace(go.Scatter(
                x=[e.get('uptime_seconds', 0) for e in young_gc],
                y=[e.get('pause_ms', 0) for e in young_gc],
                mode='markers',
                name='Young GC',
                marker=dict(
                    color=COLORS['primary'],
                    size=8,
                    symbol='circle'
                ),
                hovertemplate='Young GC at %{x:.1f}s<br>Pause: %{y:.1f}ms<extra></extra>'
            ))
        
        # Full GC events (larger, red - these are problematic)
        if full_gc:
            fig.add_trace(go.Scatter(
                x=[e.get('uptime_seconds', 0) for e in full_gc],
                y=[e.get('pause_ms', 0) for e in full_gc],
                mode='markers',
                name='Full GC',
                marker=dict(
                    color=COLORS['danger'],
                    size=12,
                    symbol='diamond'
                ),
                hovertemplate='⚠️ Full GC at %{x:.1f}s<br>Pause: %{y:.1f}ms<extra></extra>'
            ))
        
        # Add threshold line at 200ms (common SLA target)
        max_pause = max([e.get('pause_ms', 0) for e in timeline], default=0)
        if max_pause > 200:
            fig.add_hline(
                y=200, 
                line_dash='dash', 
                line_color=COLORS['warning'],
                annotation_text='200ms SLA target',
                annotation_position='top right',
                annotation_font_color=COLORS['warning']
            )
        
        layout = cls._get_layout('GC Pause Timeline', height=400)
        fig.update_layout(**layout)
        fig.update_xaxes(title_text='Uptime (seconds)')
        fig.update_yaxes(title_text='Pause Duration (ms)')
        
        return cls._fig_to_output(fig)

