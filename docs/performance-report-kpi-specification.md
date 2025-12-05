# Performance Testing Report KPI Specification

> **Purpose**: This document defines the essential KPIs that MUST appear in any performance testing report, regardless of system architecture. Use this as the authoritative reference for report generation, metric prioritization, and threshold evaluation.

---

## 1. REPORT STRUCTURE HIERARCHY

Reports MUST display metrics in this priority order:

```
LEVEL 1 (Always Show - Report Header)
├── Response Time Distribution (P50, P95, P99)
├── Throughput (RPS/TPS)
├── Error Rate (%)
├── Apdex Score (if threshold defined)
└── Test Context Metadata

LEVEL 2 (Summary Section)
├── Resource Utilization Peaks (CPU, Memory)
├── Concurrency Profile (peak VUs, pattern)
└── SLO Compliance Status

LEVEL 3 (Drill-Down / Details)
├── Per-endpoint breakdown
├── Time-series charts
├── Error categorization
└── Resource correlation analysis
```

---

## 2. UNIVERSAL KPIs (Required for ALL architectures)

### 2.1 Response Time / Latency

**Definition**: Time elapsed between request initiation and complete response receipt.

**Required Percentiles**:

| Metric | Formula | Interpretation | Report Priority |
|--------|---------|----------------|-----------------|
| `p50` | 50th percentile of response times | Median/typical user experience | HIGH |
| `p90` | 90th percentile of response times | Experience for 90% of requests | MEDIUM |
| `p95` | 95th percentile of response times | SLO baseline; excludes worst 5% | HIGH |
| `p99` | 99th percentile of response times | Tail latency; architectural issues | HIGH |
| `min` | Minimum observed response time | Best-case baseline | LOW |
| `max` | Maximum observed response time | Worst-case (debugging only) | LOW |
| `avg` | Arithmetic mean | CAUTION: Misleading with skewed distributions | LOW |
| `stddev` | Standard deviation | Consistency indicator | MEDIUM |

**Display Rules**:
- ALWAYS show p50, p95, p99 in the header
- NEVER use average as the primary latency metric
- Flag when p99 > 3× p50 (indicates high variability)
- Include units (ms or s) explicitly

**Thresholds** (general guidance, adjust per SLO):
| Rating | Web API | User-Facing UI | Background Job |
|--------|---------|----------------|----------------|
| Good | p95 < 200ms | p95 < 1s | p95 < 5s |
| Acceptable | p95 < 500ms | p95 < 2.5s | p95 < 30s |
| Poor | p95 > 1s | p95 > 4s | p95 > 60s |

---

### 2.2 Throughput

**Definition**: Volume of work processed per unit time.

**Metrics**:

| Metric | Formula | Use Case |
|--------|---------|----------|
| `requests_per_second` | Total Requests / Test Duration (s) | HTTP APIs, microservices |
| `transactions_per_second` | Completed Transactions / Test Duration (s) | Business flows, e-commerce |
| `iterations_per_second` | Completed Test Iterations / Test Duration (s) | k6-specific |
| `data_throughput` | Total Bytes Transferred / Test Duration (s) | Data pipelines, file transfers |

**Display Rules**:
- Show both `average` and `peak` throughput
- Include `total_requests` or `total_transactions` count
- For load tests: show throughput vs. time chart
- Note the concurrency level at which throughput was measured

**Derived Insight**:
```
throughput_per_vu = throughput / concurrent_users
```
Use this to assess per-user capacity and scaling efficiency.

---

### 2.3 Error Rate

**Definition**: Proportion of requests that failed or returned errors.

**Formula**:
```
error_rate = (failed_requests / total_requests) × 100
```

**Alternative (Success Rate)**:
```
success_rate = (successful_requests / total_requests) × 100
success_rate = 100 - error_rate
```

**Error Classification** (must categorize):

| Category | Description | Severity |
|----------|-------------|----------|
| `http_4xx` | Client errors (bad request, auth failure) | MEDIUM |
| `http_5xx` | Server errors (internal error, bad gateway) | HIGH |
| `timeout` | Request exceeded timeout threshold | HIGH |
| `connection_error` | TCP/network level failures | CRITICAL |
| `business_error` | HTTP 200 but payload indicates failure | MEDIUM |

**Display Rules**:
- Show overall error rate prominently
- Break down by error category
- Flag if error_rate > 1% (typical SLO threshold)
- For zero errors, explicitly state "0% error rate" (don't omit)

**Thresholds**:
| Rating | Error Rate |
|--------|------------|
| Excellent | < 0.1% |
| Good | < 1% |
| Acceptable | < 5% |
| Poor | ≥ 5% |

---

### 2.4 Apdex Score

**Definition**: Application Performance Index—standardized user satisfaction score.

**Formula**:
```
apdex = (satisfied_count + (tolerable_count × 0.5)) / total_samples
```

**Classification Rules** (based on threshold T):

| Category | Condition | Weight |
|----------|-----------|--------|
| Satisfied | response_time ≤ T | 1.0 |
| Tolerable | T < response_time ≤ 4T | 0.5 |
| Frustrated | response_time > 4T OR error | 0.0 |

**Score Interpretation**:
| Apdex Score | Rating | Description |
|-------------|--------|-------------|
| 0.94 - 1.00 | Excellent | Users very satisfied |
| 0.85 - 0.93 | Good | Users satisfied |
| 0.70 - 0.84 | Fair | Some users frustrated |
| 0.50 - 0.69 | Poor | Many users frustrated |
| 0.00 - 0.49 | Unacceptable | Most users frustrated |

**Display Rules**:
- Only show if threshold T is defined
- Display T value alongside Apdex score
- Show distribution: X% satisfied, Y% tolerable, Z% frustrated
- Common T values: 500ms (APIs), 2000ms (web pages), 100ms (real-time)

---

### 2.5 Resource Utilization

**Definition**: Infrastructure resource consumption during test execution.

**Required Metrics**:

| Metric | Formula | Alert Threshold |
|--------|---------|-----------------|
| `cpu_utilization` | (1 - cpu_idle) × 100 | > 80% sustained |
| `memory_utilization` | used_memory / total_memory × 100 | > 85% |
| `memory_used_bytes` | Absolute memory consumption | Context-dependent |
| `network_in_bytes` | Inbound network traffic | Saturation-dependent |
| `network_out_bytes` | Outbound network traffic | Saturation-dependent |
| `disk_iops` | I/O operations per second | Queue depth > 1 |
| `disk_latency` | Average I/O latency | > 10ms (SSD), > 20ms (HDD) |

**Display Rules**:
- Show peak values, not just averages
- Include time-series for correlation with load pattern
- Flag sustained high utilization (> 70% for > 1 minute)
- For containerized workloads: show limits vs. actual usage

**Correlation Analysis**:
When latency degrades, check:
1. CPU saturation → compute bottleneck
2. Memory pressure → GC pauses, swapping
3. Network saturation → bandwidth limit
4. Disk I/O → database or logging bottleneck

---

### 2.6 Concurrency / Virtual Users

**Definition**: Number of simultaneous users or connections during test.

**Metrics**:

| Metric | Description |
|--------|-------------|
| `vus` | Current virtual users (point-in-time) |
| `vus_max` | Peak concurrent users during test |
| `vus_pattern` | Ramp-up profile (constant, ramp, stages) |

**Derived Metrics**:
```
requests_per_vu = total_requests / vus_max
think_time_effective = (test_duration × vus_max) / total_requests - avg_response_time
```

**Display Rules**:
- Always show alongside throughput (context)
- Describe the load pattern (e.g., "ramped from 0 to 100 VUs over 60s")
- Identify the breaking point if applicable

---

### 2.7 Test Context Metadata

**Required Context** (always include):

```yaml
test_metadata:
  test_name: string          # Identifier for the test
  test_type: enum            # load | stress | soak | spike | baseline
  start_time: ISO8601        # When test began
  end_time: ISO8601          # When test completed
  duration_seconds: number   # Total test duration
  target_system: string      # What was tested (URL, service name)
  environment: string        # prod | staging | dev | perf
  tool_version: string       # k6 version, etc.
  
load_profile:
  pattern: enum              # constant | ramping | staged | spike
  peak_vus: number           # Maximum concurrent users
  ramp_up_seconds: number    # Time to reach peak (if applicable)
  steady_state_seconds: number
  
thresholds_defined:
  - metric: string
    condition: string
    passed: boolean
```

---

## 3. DOMAIN-SPECIFIC KPIs

### 3.1 Frontend / Web (Core Web Vitals)

**Required when**: Testing web pages, SPAs, or browser-rendered content.

| Metric | Full Name | Good | Needs Improvement | Poor |
|--------|-----------|------|-------------------|------|
| `lcp` | Largest Contentful Paint | ≤ 2.5s | 2.5s - 4.0s | > 4.0s |
| `inp` | Interaction to Next Paint | ≤ 200ms | 200ms - 500ms | > 500ms |
| `cls` | Cumulative Layout Shift | ≤ 0.1 | 0.1 - 0.25 | > 0.25 |
| `fcp` | First Contentful Paint | ≤ 1.8s | 1.8s - 3.0s | > 3.0s |
| `ttfb` | Time to First Byte | ≤ 800ms | 800ms - 1800ms | > 1800ms |
| `fid` | First Input Delay (deprecated) | ≤ 100ms | 100ms - 300ms | > 300ms |

**Additional Frontend Metrics**:
- `speed_index`: How quickly content is visually displayed
- `total_blocking_time`: Sum of long task blocking periods
- `dom_content_loaded`: DOMContentLoaded event timing
- `page_load_time`: Full page load completion

**Display Rules**:
- Use 75th percentile for Core Web Vitals (Google standard)
- Color-code: green (good), yellow (needs improvement), red (poor)
- Show field data vs. lab data distinction if available

---

### 3.2 Mobile Applications

**Required when**: Testing iOS, Android, or cross-platform mobile apps.

| Metric | Description | Good Threshold |
|--------|-------------|----------------|
| `app_launch_cold` | Cold start time (from tap to interactive) | < 2s |
| `app_launch_warm` | Warm start time (app in background) | < 1s |
| `frame_rate` | Frames per second during interaction | ≥ 60 FPS |
| `dropped_frames` | Frames missed during rendering | < 1% |
| `memory_footprint` | App memory consumption | Context-dependent |
| `battery_drain` | Power consumption rate | Context-dependent |
| `network_payload` | Data transferred per session | Minimize |

---

### 3.3 AI / LLM Inference

**Required when**: Testing language models, generative AI, or ML inference endpoints.

| Metric | Formula / Description | Typical Good Value |
|--------|----------------------|-------------------|
| `ttft` | Time to First Token | < 500ms (streaming) |
| `tpot` | Time Per Output Token (inter-token latency) | < 50ms |
| `itl` | Inter-Token Latency (same as TPOT) | < 50ms |
| `total_generation_time` | TTFT + (TPOT × output_tokens) | Context-dependent |
| `tokens_per_second` | Output tokens / generation time | > 30 tok/s |
| `input_tps` | Input tokens processed per second | Batch-dependent |
| `output_tps` | Output tokens generated per second | Model-dependent |

**LLM-Specific Derived Metrics**:
```
goodput = requests_meeting_slo / total_requests × throughput
perceived_tps = output_tokens / (total_generation_time - ttft)
```

**Display Rules**:
- Separate TTFT from generation metrics (different optimization targets)
- Note model size, quantization, and hardware in context
- Include batch size / concurrency context
- Flag cold start scenarios separately

---

### 3.4 Database / Data Layer

**Required when**: Testing databases, caches, or data services directly.

| Metric | Description |
|--------|-------------|
| `query_latency_p95` | 95th percentile query execution time |
| `queries_per_second` | Query throughput |
| `connection_pool_usage` | Active / max connections |
| `cache_hit_ratio` | Cache hits / total lookups × 100 |
| `replication_lag` | Seconds behind primary (if replicated) |
| `lock_wait_time` | Time spent waiting for locks |

---

### 3.5 Message Queue / Event Streaming

**Required when**: Testing Kafka, RabbitMQ, SQS, or similar systems.

| Metric | Description |
|--------|-------------|
| `publish_latency` | Time to acknowledge message publish |
| `consume_latency` | Time from publish to consume |
| `messages_per_second` | Message throughput |
| `queue_depth` | Current messages pending consumption |
| `consumer_lag` | Messages behind real-time |

---

## 4. SLO/SLA COMPLIANCE SECTION

**Structure**:
```yaml
slo_compliance:
  overall_status: PASSED | FAILED | DEGRADED
  
  objectives:
    - name: "API Response Time"
      metric: http_req_duration_p95
      target: "< 500ms"
      actual: "342ms"
      status: PASSED
      margin: "+158ms headroom"
      
    - name: "Error Rate"
      metric: error_rate
      target: "< 1%"
      actual: "0.23%"
      status: PASSED
      
    - name: "Availability"
      metric: success_rate
      target: "> 99.9%"
      actual: "99.77%"
      status: FAILED
      breach: "-0.13%"

error_budget:
  budget_total: "0.1%"  # For 99.9% SLO
  budget_consumed: "0.23%"
  budget_remaining: "-0.13%"  # Negative = exceeded
  burn_rate: "2.3x normal"
```

**Display Rules**:
- Show pass/fail status prominently with color coding
- Calculate margin or breach amount
- If SLO failed, highlight in report header
- Include error budget consumption for SRE context

---

## 5. REPORT GENERATION RULES

### 5.1 Formatting Standards

1. **Numbers**: Use consistent precision
   - Latency: 1 decimal place (e.g., 142.3ms)
   - Percentages: 2 decimal places (e.g., 99.73%)
   - Large counts: Use thousand separators (e.g., 1,234,567)

2. **Units**: Always explicit
   - Time: ms (< 1s), s (≥ 1s), m (≥ 60s)
   - Data: B, KB, MB, GB (use appropriate scale)
   - Rate: /s suffix (e.g., req/s, tok/s)

3. **Comparisons**: Include delta when comparing to baseline
   ```
   p95: 245ms (↑12% vs baseline)
   ```

### 5.2 Conditional Sections

| Condition | Action |
|-----------|--------|
| Error rate = 0 | Still show "Error Rate: 0.00%" explicitly |
| No SLO defined | Omit SLO compliance section |
| Single request type | Omit per-endpoint breakdown |
| Test duration < 60s | Add warning about statistical significance |
| p99 > 5× p50 | Add latency distribution warning |

### 5.3 Bottleneck Identification Hints

When generating analysis, correlate:

| Symptom | Likely Cause | Check |
|---------|--------------|-------|
| Latency ↑ as VUs ↑ | Saturation | CPU, connection pool |
| Error rate spikes at VU threshold | Capacity limit | Memory, connection limits |
| Latency variance high | Resource contention | GC logs, lock contention |
| TTFB high, processing fast | Network or DNS | Network metrics, geographic distribution |
| p99 >> p95 | Outlier issues | Cold starts, cache misses, GC |

---

## 6. DATA SOURCE MAPPING

### 6.1 k6 Metrics → KPIs

| k6 Metric | Maps To |
|-----------|---------|
| `http_req_duration` | Response Time (use trend for percentiles) |
| `http_req_failed` | Error Rate calculation |
| `http_reqs` | Throughput (requests) |
| `iterations` | Throughput (iterations) |
| `vus` | Concurrency |
| `data_received` | Network throughput (in) |
| `data_sent` | Network throughput (out) |
| `http_req_waiting` | TTFB approximation |
| `http_req_connecting` | Connection time |

### 6.2 Prometheus Metrics → KPIs

| Prometheus Pattern | Maps To |
|--------------------|---------|
| `node_cpu_seconds_total` | CPU Utilization (derive rate) |
| `node_memory_MemAvailable_bytes` | Memory Utilization |
| `container_cpu_usage_seconds_total` | Container CPU |
| `container_memory_usage_bytes` | Container Memory |
| `process_cpu_seconds_total` | Process CPU |
| `http_request_duration_seconds` | Response Time (if instrumented) |
| `http_requests_total` | Request count (derive rate for RPS) |

### 6.3 Timestamp Alignment

When correlating k6 and Prometheus data:
1. Align on UTC timestamps
2. Use k6's `--out json` with timestamp per data point
3. Match Prometheus scrape interval to k6 reporting interval
4. Aggregate to common time buckets (e.g., 10s windows)

---

## 7. EXAMPLE REPORT HEADER

```markdown
# Performance Test Report: Payment API Load Test

**Status**: ✅ PASSED | **Environment**: staging | **Date**: 2024-12-06

## Summary

| Metric | Value | Status |
|--------|-------|--------|
| Response Time (p50) | 89ms | ✅ |
| Response Time (p95) | 187ms | ✅ |
| Response Time (p99) | 342ms | ✅ |
| Throughput | 1,247 req/s | — |
| Error Rate | 0.12% | ✅ |
| Apdex (T=200ms) | 0.94 | Excellent |

## Test Context

- **Duration**: 10 minutes
- **Peak VUs**: 200
- **Pattern**: Ramp 0→200 over 2min, hold 6min, ramp down 2min
- **Target**: https://api.staging.example.com/v2/payments

## Resource Utilization (Peak)

| Resource | Peak | Threshold | Status |
|----------|------|-----------|--------|
| CPU | 67% | 80% | ✅ |
| Memory | 4.2 GB / 8 GB | 85% | ✅ |
```

---

## 8. CHANGE LOG

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2024-12-06 | Initial specification |

---

*This specification should be treated as the source of truth for performance report generation. When in doubt, prioritize clarity and actionability over completeness.*
