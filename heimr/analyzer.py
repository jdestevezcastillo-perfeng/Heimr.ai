import os
import pandas as pd
from typing import Dict, Any, Optional, List, Union, Generator
from dataclasses import dataclass, field

from heimr.parsers.jtl import JTLParser
from heimr.parsers.k6 import K6Parser
from heimr.parsers.gatling import GatlingParser
from heimr.parsers.locust import LocustParser
from heimr.parsers.har import HARParser
from heimr.detector import AnomalyDetector
from heimr.kpi import KPIEngine
from heimr.llm import LLMClient
from heimr.prometheus import PrometheusClient
from heimr.loki import LokiClient
from heimr.tempo import TempoClient

@dataclass
class AnalysisResult:
    """Holds the results of an analysis run."""
    df: pd.DataFrame
    kpi: Dict[str, Any]
    stats: Dict[str, Any]
    anomalies: pd.DataFrame
    anomaly_summary: Dict[str, Any]
    prom_metrics: Dict[str, Any] = field(default_factory=dict)
    loki_logs: List[Any] = field(default_factory=list)
    tempo_traces: List[Any] = field(default_factory=list)
    failure_signals: List[str] = field(default_factory=list)
    status: str = "PASSED"
    llm_explanation: Optional[str] = None

class Analyzer:
    """
    Main orchestration class for Heimr analysis.
    Encapsulates parsing, KPI calculation, anomaly detection,
    observability usage, and LLM analysis.
    """

    def __init__(self, 
                 file_path: str, 
                 config: Dict[str, Any] = None,
                 llm_url: str = None, 
                 llm_model: str = None,
                 no_llm: bool = False):
        self.file_path = file_path
        self.config = config or {}
        self.llm_url = llm_url
        self.llm_model = llm_model
        self.no_llm = no_llm
        
        # Merge config values if not provided in init args
        if not self.no_llm:
            # Check config if not explicitly disabled
            if self.config.get('explain') is False:
                self.no_llm = True
                
        if not self.llm_url:
            self.llm_url = self.config.get('llm_url')
        
        if not self.llm_model:
            self.llm_model = self.config.get('llm_model', 'medium')

    @staticmethod
    def detect_file_format(file_path: str) -> str:
        """Auto-detect load test file format."""
        ext = os.path.splitext(file_path)[1].lower()
        if ext == '.json':
            return 'k6'
        elif ext == '.log':
            return 'gatling'
        elif 'stats_history' in file_path:
            return 'locust'
        elif file_path.endswith('.har'):
            return 'har'
        else:
            # Try to detect HAR by content
            try:
                with open(file_path, 'r') as f:
                    first_chars = f.read(100)
                    if '"log"' in first_chars and '"entries"' in first_chars:
                        return 'har'
            except Exception:
                pass
            return 'jtl'

    @staticmethod
    def parse_url_or_file(value: str):
        """
        Parse a value that could be either a URL or a file path.
        Returns a tuple of (url, file_path) where one is None.
        """
        if not value:
            return None, None
        
        if value.startswith('http://') or value.startswith('https://'):
            return value, None
        else:
            return None, value

    def _get_parser(self, file_format: str):
        if file_format == 'k6':
            return K6Parser(self.file_path)
        elif file_format == 'gatling':
            return GatlingParser(self.file_path)
        elif file_format == 'locust':
            return LocustParser(self.file_path)
        elif file_format == 'har':
            return HARParser(self.file_path)
        else:
            return JTLParser(self.file_path)

    def analyze(self, stream_callback=None) -> AnalysisResult:
        """Run the full analysis pipeline."""
        
        # 1. Parse File
        file_format = self.detect_file_format(self.file_path)
        parser = self._get_parser(file_format)
        df = parser.parse()
        
        # 2. Key Performance Indicators
        kpi_engine = KPIEngine(df)
        kpi_data = kpi_engine.get_kpi_dict()
        
        # Build legacy stats adapter
        stats = {
            'total_requests': kpi_data['throughput']['total_requests'],
            'start_time': df['timestamp_dt'].min() if not df.empty else None,
            'end_time': df['timestamp_dt'].max() if not df.empty else None,
            'avg_latency': kpi_data['latency']['avg'],
            'p95_latency': kpi_data['latency']['p95'],
            'p99_latency': kpi_data['latency']['p99'],
            'p50_latency': kpi_data['latency']['p50'],
            'error_rate': kpi_data['errors']['rate'],
            'median_latency': kpi_data['latency']['p50'],
            'min_latency': kpi_data['latency']['min'],
            'max_latency': kpi_data['latency']['max'],
            'throughput': kpi_data['throughput']['requests_per_second']
        }
        
        # 3. Anomaly Detection
        detector = AnomalyDetector(df)
        anomalies = detector.detect_latency_anomalies()
        anomaly_summary = detector.get_anomaly_summary(anomalies)
        
        # 4. Observability Data (Prometheus, Loki, Tempo)
        prom_metrics = {}
        loki_logs = []
        tempo_traces = []
        
        if not df.empty and stats['start_time'] and stats['end_time']:
            # Prometheus
            prom_conf = self.config.get('prometheus')
            if prom_conf:
                try:
                    url, path = self.parse_url_or_file(prom_conf)
                    prom = PrometheusClient(url=url or "http://localhost:9090", file_path=path)
                    prom_metrics = prom.get_system_metrics(stats['start_time'], stats['end_time'])
                except Exception as e:
                    print(f"Warning: Failed to fetch Prometheus metrics: {e}")

            # Loki
            loki_conf = self.config.get('loki')
            if loki_conf:
                try:
                    url, path = self.parse_url_or_file(loki_conf)
                    loki = LokiClient(url=url or "http://localhost:3100", file_path=path)
                    loki_logs = loki.get_error_logs(stats['start_time'], stats['end_time'])
                except Exception as e:
                    print(f"Warning: Failed to fetch Loki logs: {e}")

            # Tempo
            tempo_conf = self.config.get('tempo')
            if tempo_conf:
                try:
                    url, path = self.parse_url_or_file(tempo_conf)
                    tempo = TempoClient(url=url or "http://localhost:3200", file_path=path)
                    min_duration = int(stats.get('p99_latency', 1000))
                    tempo_traces = tempo.get_slow_traces(
                        stats['start_time'], stats['end_time'], min_duration_ms=min_duration)
                except Exception as e:
                    print(f"Warning: Failed to fetch Tempo traces: {e}")
        
        # 5. Multi-Signal Failure Detection
        failure_signals = self._detect_failures(stats, anomaly_summary, prom_metrics, loki_logs, tempo_traces)
        status = "FAILED" if failure_signals else "PASSED"
        
        # 6. AI Analysis
        llm_explanation = None
        if not self.no_llm:
            try:
                # Smart default for URL
                target_url = self.llm_url
                if not target_url:
                    has_api_key = os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("OPENAI_API_KEY")
                    if not has_api_key:
                        target_url = "http://localhost:11434/v1"

                llm = LLMClient(base_url=target_url, model=self.llm_model)
                generator = llm.generate_explanation(
                    stats, anomaly_summary, prom_metrics, loki_logs, tempo_traces
                )
                
                chunks = []
                for chunk in generator:
                    if stream_callback:
                        stream_callback(chunk)
                    chunks.append(chunk)
                llm_explanation = "".join(chunks)
            except Exception as e:
                print(f"Warning: LLM analysis failed: {e}")
        
        return AnalysisResult(
            df=df,
            kpi=kpi_data,
            stats=stats,
            anomalies=anomalies,
            anomaly_summary=anomaly_summary,
            prom_metrics=prom_metrics,
            loki_logs=loki_logs,
            tempo_traces=tempo_traces,
            failure_signals=failure_signals,
            status=status,
            llm_explanation=llm_explanation
        )

    def _detect_failures(self, stats, anomaly_summary, prom_metrics, loki_logs, tempo_traces) -> List[str]:
        """Detect failure conditions across multiple signals."""
        signals = []

        if anomaly_summary['count'] > 0:
            signals.append(f"Anomalies: {anomaly_summary['count']}")

        if stats.get('error_rate', 0) > 0:
            signals.append(f"Error Rate: {stats['error_rate']:.2f}%")

        if prom_metrics and 'cpu_usage' in prom_metrics and len(prom_metrics['cpu_usage']) > 0:
            cpu_values = [float(v[1]) for v in prom_metrics['cpu_usage'][0]['values']]
            avg_cpu = sum(cpu_values) / len(cpu_values) if cpu_values else 0
            if avg_cpu > 0.8:  # TODO: Make configurable
                signals.append(f"High CPU: {avg_cpu * 100:.1f}%")
               # Signal 6: Memory growth (from Prometheus)
        if prom_metrics and 'memory_usage' in prom_metrics and prom_metrics['memory_usage']:
            try:
                mem_values = [float(v[1]) for v in prom_metrics['memory_usage'][0]['values']]
                if len(mem_values) >= 2 and mem_values[0] > 0:
                    mem_growth = (mem_values[-1] - mem_values[0]) / mem_values[0]
                    if mem_growth > 0.5:
                        signals.append(f"Memory Growth: {mem_growth*100:.1f}%")
            except (IndexError, ValueError):
                pass

        if loki_logs:
            error_count = sum(1 for log in loki_logs if 'level=error' in log or 'level=warn' in log)
            if error_count > 0:
                signals.append(f"Error/Warn Logs: {error_count}")

        if tempo_traces and len(tempo_traces) > 5:
            p99 = stats.get('p99_latency', 1000)
            very_slow_traces = [t for t in tempo_traces if t.get('duration', 0) > p99 * 2]
            if len(very_slow_traces) > 0:
                signals.append(f"Very Slow Traces: {len(very_slow_traces)}")

        return signals
