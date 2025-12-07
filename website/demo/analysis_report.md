```text

 █████   █████           ███                           
░░███   ░░███           ░░░                            
 ░███    ░███   ██████  ████  █████████████   ████████ 
 ░███████████  ███░░███░░███ ░░███░░███░░███ ░░███░░███
 ░███░░░░░███ ░███████  ░███  ░███ ░███ ░███  ░███ ░░░ 
 ░███    ░███ ░███░░░   ░███  ░███ ░███ ░███  ░███     
 █████   █████░░██████  █████ █████░███ █████ █████    
░░░░░   ░░░░░  ░░░░░░  ░░░░░ ░░░░░ ░░░ ░░░░░ ░░░░░     
```

# ❌ FAILED
**Reasons**: Anomalies: 108, Error/Warn Logs: 7

## Level 1: Primary KPIs
| Metric | Value | Reference |
|---|---|---|
| P95 Latency | 150.00 ms | < 500ms (API) |
| Error Rate | 0.00% | < 1.0% |
| Throughput | 10.00 req/s | 25.15 KB/s |

## Level 2: Summary
- **Concurrency**: Max 5 VUs, Avg 5.0 VUs
- **Anomalies**: 108 detected (Avg 4021.31 ms)
- **Prometheus**: Fetched 2 metric types
- **Loki**: Fetched 60 error logs
- **Tempo**: Fetched 1 slow traces

## Level 3: Per Endpoint Breakdown
| Endpoint | Requests | RPS | Error % | Avg (ms) | P95 (ms) | P99 (ms) |
|---|---|---|---|---|---|---|
| HTTP Request - /api/checkout | 602 | 2.02 | 0.00% | 304.56 | 2886.95 | 4129.39 |
| HTTP Request - /api/inventory | 589 | 1.96 | 0.00% | 187.00 | 149.00 | 3618.20 |
| HTTP Request - /api/orders | 617 | 2.06 | 0.00% | 228.38 | 148.20 | 4335.92 |
| HTTP Request - /api/products | 588 | 1.96 | 0.00% | 275.53 | 150.00 | 4608.99 |
| HTTP Request - /api/users | 604 | 2.02 | 0.00% | 285.47 | 149.00 | 4804.70 |
| **TOTAL** | **3000** | **10.00** | **0.00%** | **256.28** | **150.00** | **4456.00** |

## Level 4: Observability Data
### Loki Error Logs (Sample)
- `level=info msg="Request processed" duration=92ms status=200 endpoint="/api/users" scenario="memory-pressure-demo"`
- `level=info msg="Request processed" duration=83ms status=200 endpoint="/api/products" scenario="memory-pressure-demo"`
- `level=info msg="Request processed" duration=125ms status=200 endpoint="/api/orders" scenario="memory-pressure-demo"`
- `level=info msg="Request processed" duration=149ms status=200 endpoint="/api/users" scenario="memory-pressure-demo"`
- `level=info msg="Request processed" duration=139ms status=200 endpoint="/api/products" scenario="memory-pressure-demo"`

### Tempo Slow Traces (Sample)
- TraceID: `c55a2d6af3764081a50ba33ccb2954f6` (Nonems)



