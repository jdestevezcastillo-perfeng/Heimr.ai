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

try:
    import plotly.graph_objects as go
    import plotly.express as px
    from plotly.subplots import make_subplots
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False


# Color scheme matching Heimr branding
COLORS = {
    'primary': '#00D4AA',      # Cyan/Teal
    'secondary': '#7C3AED',    # Purple
    'success': '#22C55E',      # Green
    'warning': '#F59E0B',      # Amber
    'danger': '#EF4444',       # Red
    'muted': 'rgba(156, 163, 175, 0.5)',  # Gray 50% opacity
    'background': '#0F172A',   # Dark navy
    'text': '#E2E8F0',         # Light gray
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
        Generate latency distribution histogram with P50, P95, P99 markers.
        Returns HTML string.
        """
        if not PLOTLY_AVAILABLE or df.empty or 'elapsed' not in df.columns:
            return None
            
        elapsed = df['elapsed'].dropna()
        p50 = elapsed.quantile(0.50)
        p95 = elapsed.quantile(0.95)
        p99 = elapsed.quantile(0.99)
        
        fig = go.Figure()
        
        # Histogram
        fig.add_trace(go.Histogram(
            x=elapsed,
            nbinsx=50,
            marker_color=COLORS['primary'],
            opacity=0.7,
            name='Response Time',
            hovertemplate='%{x:.0f}ms: %{y} requests<extra></extra>'
        ))
        
        # Percentile lines
        for pct, val, color, name in [
            (50, p50, COLORS['success'], 'P50'),
            (95, p95, COLORS['warning'], 'P95'),
            (99, p99, COLORS['danger'], 'P99'),
        ]:
            fig.add_vline(x=val, line_dash="dash", line_color=color, line_width=2,
                         annotation_text=f"{name}: {val:.0f}ms",
                         annotation_position="top",
                         annotation_font_color=color)
        
        fig.update_layout(**cls._get_layout('Response Time Distribution'))
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
        
        fig = go.Figure()
        
        fig.add_trace(go.Scatter(
            x=agg['time'], y=agg['avg'],
            mode='lines',
            name='Avg Response Time',
            line=dict(color=COLORS['primary'], width=2),
            hovertemplate='%{x}<br>Avg: %{y:.0f}ms<extra></extra>'
        ))
        
        fig.add_trace(go.Scatter(
            x=agg['time'], y=agg['p95'],
            mode='lines',
            name='P95',
            line=dict(color=COLORS['warning'], width=2, dash='dot'),
            hovertemplate='%{x}<br>P95: %{y:.0f}ms<extra></extra>'
        ))
        
        fig.update_layout(**cls._get_layout('Response Time Over Load'))
        fig.update_xaxes(title_text='Time')
        fig.update_yaxes(title_text='Response Time (ms)')
        
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
    def resource_utilization(cls, metrics: Dict[str, Any], metric_type: str = 'cpu') -> Optional[str]:
        """
        Generate resource utilization chart from Prometheus metrics.
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
            
        fig = go.Figure()
        
        for metric_name, metric_data in category_data.items():
            series_data = PrometheusNormalizer.extract_time_series(metric_data)
            if not series_data:
                continue
                
            # Group by unique label combination
            label_groups = {}
            for point in series_data:
                label_key = str(point['labels'].get('pod', point['labels'].get('instance', 'default')))
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
                    
                fig.add_trace(go.Scatter(
                    x=[pd.Timestamp(t, unit='s') for t in data['x']],
                    y=y_values,
                    mode='lines',
                    name=f'{label}',
                    hovertemplate='%{x}<br>%{y:.1f}<extra></extra>'
                ))
        
        titles = {
            'cpu': 'CPU Utilization (%)', 
            'memory': 'Memory Usage (MB)', 
            'gpu': 'GPU Utilization',
            'disk': 'Disk I/O (MB/s)',
            'network': 'Network I/O (MB/s)',
            'db': 'Database Metrics',
            'messaging': 'Messaging/Streaming'
        }
        fig.update_layout(**cls._get_layout(titles.get(metric_type, 'Resource Utilization')))
        fig.update_xaxes(title_text='Time')
        fig.update_yaxes(title_text=titles.get(metric_type, 'Value'))
        
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
