# 🔭 Enhanced Observability Stack

Complete observability stack with metrics, logs, traces, and GPU monitoring.

---

## 🎯 Components

### Metrics (Prometheus)
- **Chaos Generator metrics**: Request rates, latency, errors
- **NVIDIA GPU metrics**: Utilization, temperature, power, memory
- **System metrics**: Prometheus, Loki, Tempo self-monitoring

### Logs (Loki + Promtail)
- **Container logs**: All Docker container logs
- **Application logs**: Chaos generator application logs
- **System logs**: Host system logs

### Traces (Tempo)
- **Distributed tracing**: Request traces across services
- **Multiple protocols**: Jaeger, Zipkin, OTLP, OpenCensus
- **Trace-to-logs correlation**: Link traces to logs

### GPU Monitoring (NVIDIA GPU Exporter)
- **GPU utilization**: Compute and memory usage
- **Temperature**: GPU, memory, hotspot temperatures
- **Power**: Power draw and limits
- **Performance state**: P-states and clocks
- **Memory**: Used, free, total VRAM

---

## 🚀 Quick Start

### 1. Stop Existing Stack

```bash
cd /home/lostborion/Performange-analyzer-AI/chaos-generator
docker-compose down
```

### 2. Start Enhanced Stack

```bash
docker-compose up -d
```

This will start:
- ✅ Chaos Generator (port 8000)
- ✅ NVIDIA GPU Exporter (port 9835)
- ✅ Prometheus (port 9090)
- ✅ Loki (port 3100)
- ✅ Promtail (log shipper)
- ✅ Tempo (ports 3200, 4317, 4318, 9411, 14268)
- ✅ Grafana (port 3000)

### 3. Verify Services

```bash
# Check all services are running
docker-compose ps

# Check GPU metrics are being scraped
curl http://localhost:9835/metrics | grep nvidia_smi

# Check Prometheus targets
curl http://localhost:9090/api/v1/targets | jq '.data.activeTargets[] | {job: .labels.job, health: .health}'

# Check Loki is ready
curl http://localhost:3100/ready

# Check Tempo is ready
curl http://localhost:3200/ready
```

---

## 📊 Access Services

| Service | URL | Purpose |
|---------|-----|---------|
| **Grafana** | http://localhost:3000 | Dashboards (admin/admin) |
| **Prometheus** | http://localhost:9090 | Metrics query UI |
| **Loki** | http://localhost:3100 | Log aggregation API |
| **Tempo** | http://localhost:3200 | Trace query API |
| **Chaos API** | http://localhost:8000 | Chaos generator API |
| **GPU Exporter** | http://localhost:9835/metrics | GPU metrics endpoint |

---

## 🎨 Grafana Dashboards

### Existing Dashboards
1. **Chaos Generator Dashboard** - Request metrics, latency, errors
2. **Nvidia GPU Metrics** - GPU utilization, temperature, power

### New Capabilities
- **Explore → Loki**: Query and search logs
- **Explore → Tempo**: View distributed traces
- **Explore → Prometheus**: Query metrics with exemplars

### Cross-Datasource Correlation
- Click on trace ID in logs → Jump to trace in Tempo
- Click on trace span → Jump to related logs in Loki
- View metrics exemplars → Jump to traces

---

## 📈 GPU Metrics Available

The NVIDIA GPU Exporter provides these metrics:

### Utilization
- `nvidia_smi_utilization_gpu_ratio` - GPU compute utilization (0-1)
- `nvidia_smi_utilization_memory_ratio` - GPU memory utilization (0-1)

### Temperature
- `nvidia_smi_temperature_gpu_celsius` - GPU temperature
- `nvidia_smi_temperature_memory_celsius` - Memory temperature

### Power
- `nvidia_smi_power_draw_watts` - Current power draw
- `nvidia_smi_power_limit_watts` - Power limit
- `nvidia_smi_power_default_limit_watts` - Default power limit

### Memory
- `nvidia_smi_memory_used_bytes` - Used VRAM
- `nvidia_smi_memory_free_bytes` - Free VRAM
- `nvidia_smi_memory_total_bytes` - Total VRAM

### Performance
- `nvidia_smi_pstate` - Performance state (P0-P12)
- `nvidia_smi_clocks_current_graphics_mhz` - GPU clock speed
- `nvidia_smi_clocks_current_memory_mhz` - Memory clock speed
- `nvidia_smi_fan_speed_ratio` - Fan speed (0-1)

### Info
- `nvidia_smi_gpu_info` - GPU name and info

---

## 🔍 Example Queries

### Prometheus (Metrics)

```promql
# GPU utilization over time
nvidia_smi_utilization_gpu_ratio{uuid="$gpu"}

# GPU temperature
nvidia_smi_temperature_gpu_celsius{uuid="$gpu"}

# Power draw percentage
nvidia_smi_power_draw_watts{uuid="$gpu"} / nvidia_smi_power_default_limit_watts{uuid="$gpu"}

# Memory usage percentage
nvidia_smi_memory_used_bytes{uuid="$gpu"} / nvidia_smi_memory_total_bytes{uuid="$gpu"}

# Chaos generator p99 latency
histogram_quantile(0.99, rate(chaos_request_duration_seconds_bucket[1m]))

# Error rate
rate(chaos_errors_total[1m])
```

### Loki (Logs)

```logql
# All chaos generator logs
{service="chaos-generator"}

# Error logs only
{service="chaos-generator"} |= "ERROR"

# Logs with latency > 1s
{service="chaos-generator"} | json | latency > 1

# Count errors per minute
sum(count_over_time({service="chaos-generator"} |= "ERROR" [1m]))
```

### Tempo (Traces)

```traceql
# All traces for chaos-generator
{service.name="chaos-generator"}

# Slow traces (> 1s)
{duration > 1s}

# Traces with errors
{status=error}

# Traces for specific scenario
{scenario="latency_spike"}
```

---

## 🎯 Training Data Collection

This observability stack provides rich data for AI training:

### 1. Metrics Data (Prometheus)
- Time-series performance metrics
- GPU utilization patterns
- Resource consumption
- Error rates and patterns

### 2. Log Data (Loki)
- Application logs with context
- Error messages and stack traces
- Request/response logs
- System events

### 3. Trace Data (Tempo)
- Request flow through system
- Service dependencies
- Latency breakdown by component
- Error propagation paths

### 4. Correlated Data
- Metrics + Logs + Traces for same time window
- Root cause analysis training data
- Multi-modal learning opportunities

---

## 📦 Data Export for Training

### Export Metrics
```bash
# Export Prometheus data
curl 'http://localhost:9090/api/v1/query_range?query=nvidia_smi_utilization_gpu_ratio&start=2025-11-28T00:00:00Z&end=2025-11-28T23:59:59Z&step=15s' | jq .
```

### Export Logs
```bash
# Export Loki logs
curl -G -s "http://localhost:3100/loki/api/v1/query_range" \
  --data-urlencode 'query={service="chaos-generator"}' \
  --data-urlencode "start=$(date -d '1 hour ago' +%s)000000000" \
  --data-urlencode "end=$(date +%s)000000000" | jq .
```

### Export Traces
```bash
# Query traces from Tempo
curl -s "http://localhost:3200/api/search?tags=service.name=chaos-generator" | jq .
```

---

## 🐛 Troubleshooting

### GPU Exporter Not Working

```bash
# Check if NVIDIA runtime is available
docker run --rm --gpus all nvidia/cuda:11.8.0-base-ubuntu22.04 nvidia-smi

# Check GPU exporter logs
docker logs nvidia-gpu-exporter

# Restart GPU exporter
docker-compose restart nvidia-gpu-exporter
```

### Loki Not Receiving Logs

```bash
# Check Promtail logs
docker logs promtail

# Check Loki logs
docker logs loki

# Test Loki API
curl http://localhost:3100/ready
```

### Tempo Not Receiving Traces

```bash
# Check Tempo logs
docker logs tempo

# Test Tempo API
curl http://localhost:3200/ready

# Check if ports are accessible
curl http://localhost:4318/v1/traces  # OTLP HTTP
```

### Prometheus Not Scraping Targets

```bash
# Check Prometheus targets
curl http://localhost:9090/api/v1/targets | jq '.data.activeTargets[] | {job: .labels.job, health: .health, lastError: .lastError}'

# Reload Prometheus config
curl -X POST http://localhost:9090/-/reload
```

---

## 🔧 Configuration Files

| File | Purpose |
|------|---------|
| `docker-compose.yml` | Service definitions |
| `prometheus.yml` | Prometheus scrape config |
| `loki-config.yml` | Loki storage and retention |
| `promtail-config.yml` | Log shipping configuration |
| `tempo-config.yml` | Trace storage and receivers |
| `grafana/provisioning/datasources/` | Grafana datasources |

---

## 📊 Resource Usage

Estimated resource usage:

| Service | CPU | Memory | Disk |
|---------|-----|--------|------|
| Chaos Generator | ~0.1 cores | ~100 MB | Minimal |
| NVIDIA GPU Exporter | ~0.05 cores | ~50 MB | Minimal |
| Prometheus | ~0.2 cores | ~500 MB | ~1 GB/day |
| Loki | ~0.1 cores | ~200 MB | ~500 MB/day |
| Promtail | ~0.05 cores | ~50 MB | Minimal |
| Tempo | ~0.1 cores | ~200 MB | ~500 MB/day |
| Grafana | ~0.1 cores | ~200 MB | ~100 MB |

**Total**: ~0.7 cores, ~1.3 GB RAM, ~2 GB/day disk

---

## 🎯 Next Steps

### 1. Validate GPU Metrics
```bash
# Check your Nvidia GPU Metrics dashboard
# URL: http://localhost:3000/d/vlvPlrgnk/nvidia-gpu-metrics
```

### 2. Explore Logs
```bash
# Go to Grafana → Explore → Loki
# Query: {service="chaos-generator"}
```

### 3. Add Tracing to Chaos Generator
```python
# Add OpenTelemetry instrumentation
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

# Configure tracer
trace.set_tracer_provider(TracerProvider())
otlp_exporter = OTLPSpanExporter(endpoint="http://tempo:4317")
trace.get_tracer_provider().add_span_processor(BatchSpanProcessor(otlp_exporter))
```

### 4. Collect Training Data
- Metrics: GPU + application metrics
- Logs: Error patterns, request logs
- Traces: Request flows, latency breakdown

---

**Status**: ✅ Complete observability stack ready!

**Includes**: Metrics (Prometheus) + Logs (Loki) + Traces (Tempo) + GPU (NVIDIA Exporter)
