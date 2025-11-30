# Recovery Context: K8s Training Data Setup

**Date**: 2025-11-29  
**Status**: ✅ Phase 1 & 2 Complete - Ready for local testing (Phase 3A)  
**Commit**: 035bbc2

## Critical Issue: Antigravity Crashes

**Problem**: Running multiple Docker/K8s commands in parallel crashes the IDE.  
**Solution**: ✅ **ALWAYS run Docker and K8s commands sequentially, one at a time, in a single terminal.**

---

## Current State

### ✅ Phase 1 Complete: Docker Images Built
All 6 simulator images built and loaded into minikube:
1. ✅ `sim-service-agent:latest` (152MB)
2. ✅ `sim-db:latest` (374MB)
3. ✅ `sim-cache:latest` (153MB)
4. ✅ `sim-queue:latest` (156MB)
5. ✅ `sim-inference:latest` (7.61GB - PyTorch)
6. ✅ `chaos-controller:latest` (189MB)

### ✅ Phase 2 Complete: K8s Manifests Created
All manifests in: `k8s/templates/category-namespace/`
- ✅ `observability-pod.yaml` - Multi-container pod (Prometheus, Loki, Tempo, Promtail, OTel, Grafana)
- ✅ `sim-deployments.yaml` - 6 simulation deployments
- ✅ `services.yaml` - 8 services (7 ClusterIP + 1 LoadBalancer)
- ✅ `configmaps/` - 7 ConfigMaps for observability tools
- ✅ `namespace.yaml` - Template (replace CATEGORY_NAME_PLACEHOLDER)
- ✅ `README.md` - Deployment instructions

### 🔄 Phase 3A: Local Testing (NEXT)
Deploy test namespace (`sim-api`) on minikube to validate everything works.

---

## Architecture (Per Category Namespace)

**7 Pods Total:**

### Simulation Pods (6 Core Archetypes)
1. **sim-service-agent** - API/services/security/LB/observability/config
2. **sim-db** - Database/storage/connection pools (PostgreSQL + sidecar)
3. **sim-cache** - Caching/CDN (Redis + sidecar)
4. **sim-queue** - Event-driven/messaging/streaming (Kafka/NATS)
5. **sim-inference** - AI/ML inference/GPU (PyTorch stub)
6. **chaos-controller** - Applies faults (does NOT generate traffic)

### Observability Pod (1 Multi-Container Pod)
**6 containers in one pod:**
- Prometheus (scrapes metrics from all 6 sim pods)
- Loki (log aggregation)
- Tempo (distributed tracing)
- Promtail (log shipper)
- OpenTelemetry Collector (receives OTLP traces → Tempo)
- Grafana (dashboards - **ONLY externally exposed component**)

**Network**: All internal ClusterIP services, only Grafana LoadBalancer

**Resources per namespace**: ~1.35GB RAM, ~1 core (fits t3.small!)

## Strategy: 28 Namespaces (Not 156)

Deploy **28 namespaces** (one per category), run scenarios sequentially within each:
- `sim-api` (16 scenarios), `sim-db` (9 scenarios), `sim-inf` (11 scenarios), etc.
- Each namespace stays up# Recovery Context

## Current Status

### Phase 3B: Add Production Metrics (Completed)

- **Status**: Completed
- **Changes**:
  - Implemented comprehensive application-level metrics for `sim-db` (PostgreSQL), `sim-cache` (Redis), `sim-queue` (Kafka), and `sim-inference` (NVIDIA GPU).
  - `sim-inference` now exposes GPU metrics using `DCGM_FI_DEV_*` (Enterprise), `nvidia_smi_*` (Consumer), and `nvidia_gpu_*` (Standard) naming conventions.
  - Updated `chaos-controller` to support `compute-load` and `vram-fill` actions for GPU simulation.
  - Created "Training Data Inspection (Mega Dashboard)" in Grafana to visualize all new metrics.
  - Verified end-to-end flow with `gpu-overheat` chaos scenario.
- **Next Steps**:
  - Proceed to Phase 4: GCP Deployment Preparation.
  - Configure Parquet export for training data.

## Architecture

- **Namespace**: `sim-api`
- **Pods**: 7 (6 simulators + 1 observability stack)
- **Observability**: Prometheus, Loki, Tempo, Promtail, Grafana
- **Metrics**:
  - **System**: node-exporter (CPU, Mem, Disk, Net)
  - **K8s**: kube-state-metrics, cAdvisor
  - **App**: Custom metrics from all simulators (PostgreSQL, Redis, Kafka, GPU)

    - **Container**: cAdvisor (Per-container resources)
    - **K8s**: kube-state-metrics (Pod/Deployment status)
    - **PostgreSQL**: 25+ metrics (Connections, Transactions, Queries, Locks, Cache, Replication)
    - **Redis**: 20+ metrics (Commands, Hits/Misses, Memory, Keys, Evictions)
    - **Kafka**: 20+ metrics (Producer/Consumer rates, Lag, Partitions, Brokers)
    - **NVIDIA GPU**: 25+ metrics (Util, Memory, Power, Temp, Clocks, PCIe, NVLink)

## Next Steps
1. **Grafana Dashboards**: Create/Update dashboards to visualize these new metrics.
2. **Chaos Scenarios**: Test how chaos injection affects these specific metrics.
3. **Data Export**: Verify Parquet export includes all these new metric columns.
 (API-001)

**Deployment commands:**
```bash
# Navigate to template directory
cd k8s/templates/category-namespace

# Create namespace
cat namespace.yaml | sed 's/CATEGORY_NAME_PLACEHOLDER/sim-api/g' | kubectl apply -f -

# Apply ConfigMaps
kubectl apply -f configmaps/ -n sim-api

# Deploy observability
kubectl apply -f observability-pod.yaml -n sim-api

# Deploy simulations
kubectl apply -f sim-deployments.yaml -n sim-api

# Create services
kubectl apply -f services.yaml -n sim-api

# Check pods
kubectl get pods -n sim-api -w

# Port-forward Grafana
kubectl port-forward svc/grafana 3000:3000 -n sim-api
```

---

## Key Files

### Documentation
- `docs/DATA_GENERATION_STRATEGY.md` - Core architecture (6 archetypes)
- `docs/K8S_MIGRATION_PLAN.md` - Migration strategy
- `docs/data/failure_scenarios.yaml` - 156 scenarios, 28 categories
- `RECOVERY_CONTEXT.md` - This file (keep updated!)

### K8s Manifests
- `k8s/templates/category-namespace/` - Complete namespace template
- All manifests ready to deploy

### Data Collection
- `data-pipeline/generate_training_data.py` - Needs update for new architecture

---

## Important Notes

- **Data Retention**: Observability stack is ephemeral (2-hour retention)
- **Dataset**: All metrics exported to Parquet after scenario completes
- **Clean Up**: Delete namespace after data collection
- **No VictoriaMetrics needed**: Raw metrics deleted after export
- **Traffic Generation**: `sim-service-agent` calls other services (chaos-controller only applies faults)

---

## Remember

- **NEVER run Docker/K8s commands in parallel**
- All images already in minikube Docker environment
- Only Grafana exposed externally per namespace
- Resource efficient: 1 namespace per t3.small instance
