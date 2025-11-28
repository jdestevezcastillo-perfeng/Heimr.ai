import sys
from pathlib import Path
sys.path.append(str(Path(".").resolve()))
from collectors.prometheus_exporter import PrometheusExporter
import logging

logging.basicConfig(level=logging.INFO)

exporter = PrometheusExporter()
print("Health check:", exporter.health_check())

print("Exporting metrics...")
data = exporter.export_scenario_metrics("test", duration_minutes=5)
print("Data keys:", data.keys())
print("Aggregated:", data["aggregated"])
