# Heimr Testing & Validation Strategy

This document outlines the comprehensive testing and validation strategy for Heimr.ai.

## Test Environment Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        Minikube Cluster                                  │
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │                    Observability Stack                           │    │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────┐     │    │
│  │  │Prometheus│  │   Loki   │  │  Tempo   │  │   Grafana    │     │    │
│  │  │  :30909  │  │  :30310  │  │  :30320  │  │    :30300    │     │    │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────────┘     │    │
│  │  + node-exporter + nvidia-smi + postgres-exporter + promtail    │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │                     Test Application                             │    │
│  │  ┌──────────────────────────┐  ┌────────────────────────┐       │    │
│  │  │  FastAPI (2 replicas)    │  │     PostgreSQL         │       │    │
│  │  │  - OTel instrumentation  │  │  - users (indexed)     │       │    │
│  │  │  - Prometheus metrics    │  │  - audit_logs (1M rows │       │    │
│  │  │  - Chaos injection       │  │    NO INDEX - SLOW!)   │       │    │
│  │  │       :30808             │  │                        │       │    │
│  │  └──────────────────────────┘  └────────────────────────┘       │    │
│  └─────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────┘
                              │
                     Load Test Tools
              ┌───────┬───────┬───────┬───────┐
              │ JMeter│  k6   │Gatling│Locust │
              └───────┴───────┴───────┴───────┘
                              │
                         ┌────▼────┐
                         │  Heimr  │
                         │Analyzer │
                         └─────────┘
```

---

## Testing Phases

### Phase 1: Baseline Testing (No Chaos)

**Objective**: Establish baseline performance metrics.

```bash
# Deploy environment
./scripts/deploy-test-env.sh

# Verify all services
curl http://<minikube-ip>:30808/health

# Run k6 baseline test (8 minutes)
k6 run load-tests/k6/load-test.js -e BASE_URL=http://<minikube-ip>:30808
```

**Expected Baseline Metrics**:

| Metric | Target |
|--------|--------|
| P95 Latency (fast endpoints) | < 200ms |
| P95 Latency (audit_logs) | 1-5s (unindexed!) |
| Error Rate | < 0.1% |
| Throughput | > 50 req/s |

**Validation**:

- [ ] Prometheus shows HTTP metrics
- [ ] Loki collects application logs
- [ ] Tempo shows traces with spans
- [ ] Grafana dashboards display data

---

### Phase 2: Chaos Injection Testing

**Objective**: Validate Heimr detects anomalies under failure conditions.

#### Test 2.1: Latency Spike

```bash
# Inject slow responses (30% of requests, 3s delay)
./scripts/inject-chaos.sh slow --delay-ms 3000

# Run load test
k6 run load-tests/k6/load-test.js -e BASE_URL=http://...

# Disable chaos
./scripts/inject-chaos.sh disable
```

**Expected Detection**:

- Heimr identifies latency anomalies
- P95/P99 spike is flagged
- LLM explains potential causes (slow backend, resource contention)

#### Test 2.2: Error Rate Spike

```bash
# Inject random 500 errors (30% rate)
./scripts/inject-chaos.sh error --rate 0.3

# Run load test
locust -f load-tests/locust/locustfile.py --host=http://... -u 10 -t 5m --headless
```

**Expected Detection**:

- Heimr identifies high error rate
- Error patterns correlate with timestamps
- Logs show "CHAOS: Injected random error"

#### Test 2.3: Memory Leak

```bash
# Enable memory leak (1KB per request)
./scripts/inject-chaos.sh memory-leak

# Run sustained load test
k6 run load-tests/k6/load-test.js -e BASE_URL=http://... --duration 15m
```

**Expected Detection**:

- Prometheus shows increasing memory usage
- Eventually OOMKilled or degraded performance
- Heimr correlates latency with memory pressure

#### Test 2.4: Slow Database Queries

```bash
# Increase audit_logs query load
# The /api/audit-logs endpoint queries 1M unindexed rows

# Modify k6 script to increase weight of audit_logs requests
# Or directly hit: curl http://.../api/audit-logs?limit=500
```

**Expected Detection**:

- Heimr identifies slow database queries
- Traces show long DB spans
- Prometheus postgres-exporter shows high query time

---

### Phase 3: Multi-Tool Validation

**Objective**: Validate Heimr parses all 4 load test formats correctly.

| Tool | Command | Output |
|------|---------|--------|
| **k6** | `k6 run load-tests/k6/load-test.js` | `results/k6_results.json` |
| **Locust** | `locust -f locustfile.py --csv=results/locust` | `results/locust_stats.csv` |
| **JMeter** | `jmeter -n -t test-plan.jmx -l results/jmeter.jtl` | `results/jmeter.jtl` |
| **Gatling** | `gatling.sh -s heimr.TestAppSimulation` | `results/gatling/simulation.log` |

**Validation Matrix**:

| Format | Parse | Metrics | Anomalies | Report | LLM |
|--------|-------|---------|-----------|--------|-----|
| JTL | ☐ | ☐ | ☐ | ☐ | ☐ |
| k6 JSON | ☐ | ☐ | ☐ | ☐ | ☐ |
| Gatling | ☐ | ☐ | ☐ | ☐ | ☐ |
| Locust CSV | ☐ | ☐ | ☐ | ☐ | ☐ |

---

### Phase 4: Observability Integration

**Objective**: Validate Heimr fetches and correlates live observability data.

```bash
# Analyze with all observability sources
heimr analyze results/k6_results.json \
    --prometheus-url http://<ip>:30909 \
    --loki-url http://<ip>:30310 \
    --tempo-url http://<ip>:30320 \
    --explain \
    --llm-url http://localhost:11434/v1 \
    --llm-model llama3.1:8b \
    --output report.md
```

**Validation Checklist**:

- [ ] Prometheus metrics fetched (CPU, memory, request rates)
- [ ] Loki logs queried (error logs, slow query warnings)
- [ ] Tempo traces retrieved (request traces, DB spans)
- [ ] Data correlated with test timestamps
- [ ] LLM generates meaningful root cause analysis

---

## Success Criteria

### Functional Requirements

| Requirement | Test | Pass Criteria |
|-------------|------|---------------|
| Parse JMeter JTL | Phase 3 | Correct request count, latency |
| Parse k6 JSON | Phase 3 | Correct metrics extraction |
| Parse Gatling log | Phase 3 | Correct simulation stats |
| Parse Locust CSV | Phase 3 | Correct stats/failures |
| Detect latency anomalies | Phase 2.1 | P95 spike flagged |
| Detect error spikes | Phase 2.2 | Error rate > threshold |
| Fetch Prometheus | Phase 4 | System metrics in report |
| Fetch Loki logs | Phase 4 | Relevant logs in report |
| Fetch Tempo traces | Phase 4 | Traces in report |
| LLM explanation | Phase 4 | Coherent root cause |

### Performance Requirements

| Metric | Requirement |
|--------|-------------|
| Analysis time (1000 requests) | < 5 seconds |
| Analysis time (100k requests) | < 30 seconds |
| Memory usage | < 512MB |
| Observability fetch | < 10 seconds each |

---

## Test Execution Checklist

### Pre-Test Setup

- [ ] Minikube running with 4 CPU, 8GB RAM
- [ ] All pods in `heimr-test` namespace are `Running`
- [ ] Grafana accessible at :30300
- [ ] Test app health check passes
- [ ] Ollama running with llama3.1:8b model

### Test Execution

- [ ] Run Phase 1 baseline tests
- [ ] Run Phase 2 chaos tests (all 4 types)
- [ ] Run Phase 3 multi-tool tests
- [ ] Run Phase 4 integration tests
- [ ] Collect all results in `load-tests/results/`

### Post-Test Validation

- [ ] Review all generated Heimr reports
- [ ] Verify anomaly detection accuracy
- [ ] Verify LLM explanations are helpful
- [ ] Document any issues or improvements

---

## Rollback / Cleanup

```bash
# Disable all chaos
./scripts/inject-chaos.sh disable

# Delete test environment
kubectl delete namespace heimr-test

# Stop minikube (optional)
minikube stop
```

---

## Known Limitations

1. **nvidia-smi-exporter**: Only works if GPU + nvidia runtime configured
2. **Gatling**: Requires Scala/SBT setup, may skip in initial testing
3. **JMeter**: Requires Java + JMeter CLI installation
4. **Tempo traces**: May have delay before traces appear in queries
5. **1M audit_logs**: Initial PostgreSQL startup takes 2-5 minutes for data generation
