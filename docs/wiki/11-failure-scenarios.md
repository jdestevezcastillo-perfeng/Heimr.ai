# Failure Scenarios

[← Back to Index](../WIKI.md)

Heimr is trained to recognize patterns across the following broad categories.

## 1. Performance & API

*Covers API endpoints, microservices, load balancers, and connection pooling.*

- **Latency Spike (Tail)**: p99 latency increases significantly (e.g., GC pauses, noisy neighbors).
- **Global Latency Shift**: All requests slow down due to resource saturation or code regression.
- **Error Spike (5xx)**: Sudden burst of server errors indicating bugs or downstream failures.
- **Rate Limiting (429)**: Client exceeds quota due to traffic surges or bad client behavior.
- **Bimodal Latency**: Fast and slow path distribution (e.g., cache misses, cold starts).
- **Memory Leak**: Gradual memory growth due to unreleased objects.
- **CPU Saturation**: CPU hits 100% from infinite loops or intensive tasks.
- **Thread Starvation**: No threads for new requests due to blocking I/O.
- **Large Payload**: Processing huge bodies causing network I/O spikes.
- **GraphQL N+1 Problem**: Excessive nested queries causing DB query explosions.
- **gRPC Stream Stall**: Bidirectional stream hangs due to network issues or deadlocks.
- **Retry Storm**: Cascading retries amplify load (Exponential request rate).
- **Circuit Breaker Open**: Fast failure after threshold due to downstream outage.
- **Cascading Failure**: One service kills others; lack of bulkheads/timeouts.
- **Distributed Deadlock**: Circular wait across services causing timeouts.
- **Service Mesh Misconfiguration**: Sidecar proxy misroutes traffic (unexpected latency, 502s).
- **Unhealthy Backend Pool**: All backends marked down due to missed health checks.
- **Sticky Session Failure**: Session affinity breaks, routing requests randomly.
- **PgBouncer Session State Leak**: Connections retain session state ("read-only transaction" errors).
- **Backend Connection Storm**: Pool restart overwhelms database with new connections.
- **NATS/Redis Consumer Stalls**: Consumers stop receiving data without errors (silent stalls).

## 2. Database & Data Store

*Covers Relational DBs, NoSQL, Storage, and Data Pipelines.*

- **Slow Query**: Missing index scan causing high DB latency.
- **Connection Pool Full**: App waits for connection (leak or small pool).
- **Replication Lag**: Replica data is stale due to network lag or heavy writes.
- **Deadlock**: Transactions blocking each other (locking order issues).
- **Disk I/O Saturation**: IOPS limit reached (high `iowait`).
- **Transaction Log Full**: Cannot write new data due to full disk or archival failure.
- **Schema Drift / Migration Conflict**: Services using different schema versions causing query failures.
- **Transaction ID Wraparound**: DB stops accepting writes to prevent data loss.
- **Integer Overflow**: Primary key sequence limit reached (use BIGINT!).
- **PV/PVC Mount Failure**: Volume fails to mount (CSI driver issues).
- **Read-Only Filesystem**: Cannot write to disk due to corruption or kernel panic.
- **Quota Exceeded**: Disk quota limit reached.
- **Cold Data Tiering Latency**: Data moved to cold tier causes slow reads.
- **Prometheus Compaction Failure**: Empty chunks or compactor halts.
- **Cardinality Explosion**: High-cardinality labels create millions of series (OOM).
- **Debezium Snapshot Interrupt**: CDC snapshot requires restart (binlog purged).

## 3. Caching & CDN

*Covers In-memory caches (Redis/Memcached) and Edge networks.*

- **Cache Stampede**: Mass re-computation on expiry (DB load spike).
- **Cache Penetration**: Querying non-existent keys (0% hit rate).
- **Cache Avalanche**: Large % of keys expire at once.
- **Hot Key**: One key gets all traffic (single node CPU spike).
- **Eviction Storm**: Cache full, evicting active keys (memory undersized).
- **Cache Invalidation Race**: Stale data served after update.
- **Cache Poisoning via Headers**: Unkeyed headers modify cached responses.
- **Edge Workers KV Failure**: Third-party storage failure cascades globally.
- **Rate Limiting Infinite Loop**: DDoS rule triggers handler infinite loop (100% CPU).

## 4. Infrastructure & Cloud

*Covers Kubernetes, Serverless, Cloud Providers, and Resource Management.*

- **OOMKill**: Container killed by kernel (Memory leak).
- **CPU Throttling**: CFS quota enforcement (Low limits).
- **Node Pressure**: Node resources exhausted leading to pod evictions.
- **DNS Latency**: Slow name resolution (CoreDNS overload).
- **Ephemeral Storage Exhaustion**: Disk full on node (Log spam).
- **Image Pull BackOff**: Container fails to start (Registry rate limit/auth).
- **Liveness Probe Loop**: Pod restarts repeatedly (Probe timeout < startup time).
- **Cold Start**: Serverless container init latency.
- **Function Timeout**: Execution exceeds limit (Slow dependency).
- **DNS Control Plane Race**: Cloud DNS records deleted during management race.
- **IAM Propagation Delay**: Eventually consistent IAM causes auth failures.
- **Containerd Shim Leak**: Orphaned shim processes accumulate.
- **Sidecar Startup Race**: App starts before sidecar proxy is ready.
- **HPA Metric Staleness**: Deployment causes unnecessary scale-up.
- **Cluster Autoscaler Delay**: Provisioning delays (>15 mins).

## 5. Network & Security

*Covers L3/L4/L7 networking, certificates, and security incidents.*

- **Packet Loss**: Network drops (Retransmits, timeouts).
- **TCP SYN Flood**: SYN queue overflow (DDoS attack).
- **Connection Timeout**: TCP handshake timeout.
- **Network Partition**: Split-brain scenario (Link failure).
- **BGP Flap**: Route instability causing packet loss.
- **MTU Mismatch**: Packet fragmentation issues.
- **DDoS (Volumetric)**: Bandwidth saturation.
- **Credential Expiry**: Auth failures (401/403 spikes).
- **Bad Bot Traffic**: Scraping/Scanning (High 404s).
- **Supply-Chain Compromise**: Third-party library introduces vulnerability.
- **Certificate Chain Validation Fail**: Valid leaf cert rejected due to chain/root issues.
- **mTLS Health Check Failure**: Kubelet probes fail under strict mTLS.

## 6. Operations & Observability

*Covers Monitoring, Logging, Tracing, Config, and GitOps.*

- **Metrics Scrape Timeout**: Prometheus cannot scrape target.
- **Log Shipper Backpressure**: Logs buffering/dropping due to volume spike.
- **Trace Sampling Issues**: Missing critical traces (Low sampling rate).
- **Alert Fatigue**: Alert rate explosion for benign spikes.
- **Config Reload Failure**: App fails to load new config (Syntax error).
- **Feature Flag Issue**: Flag flip causes immediate breakage.
- **Canary Stuck**: Deployment halted because metrics failed threshold.
- **Secret Leakage**: Credentials exposed in logs/config.
- **ArgoCD Resource Pruning**: Critical resources deleted by sync.
- **Litmus/Chaos Mesh Issues**: Finalizers stuck or kernel-level blasts.
- **Async Context Loss**: Trace context not propagated to async tasks.
- **Elasticsearch Index Rollover Fail**: Indices stuck in hot phase (Growth unbounded).

## 7. AI/ML & Advanced

*Covers AI inference, GPU resources, and low-level kernel (eBPF) issues.*

- **VRAM Saturation**: OOM during inference (Batch size too big).
- **Thermal Throttling**: GPU slows down due to overheating.
- **PCIe Bottleneck**: Slow data transfer (Large inputs).
- **Token Latency**: Slow generation per token (Compute bound).
- **eBPF Verifier Register Bug**: Verifier allows arbitrary kernel memory access.
- **Cilium Datapath Kernel Panic**: Array-index-out-of-bounds in BPF.
- **eBPF Map Memory Leak**: Kernel memory grows 200-500MB+.
