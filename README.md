# Heimr.ai - AI-Powered Performance Bottleneck Analyzer

[![Status](https://img.shields.io/badge/status-in%20development-yellow)](https://github.com/jdestevezcastillo-perfeng/Heimr.ai)
[![GKE](https://img.shields.io/badge/deployed-GKE-blue)](https://cloud.google.com/kubernetes-engine)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

**Heimr.ai** is an AI-powered system that analyzes performance metrics from distributed systems and automatically detects, explains, and recommends fixes for performance bottlenecks.

## 🎯 What We've Built

### Phase 0-1: Chaos Engineering & Data Generation (✅ Complete)

We've created a **production-grade chaos engineering platform** that generates high-fidelity training data for our ML models:

#### Chaos Generator Infrastructure
-   **50+ Failure Scenarios** across 8 categories (API, Database, Cache, Queue, GPU, Network, Security, Infrastructure)
-   **6 Microservice Simulators**:
    -   `sim-service` (HTTP/gRPC API simulator)
    -   `sim-db` (PostgreSQL simulator with 25+ metrics)
    -   `sim-cache` (Redis simulator with 20+ metrics)
    -   `sim-queue` (Kafka simulator with 20+ metrics)
    -   `sim-inference` (GPU inference simulator with NVIDIA DCGM metrics)
    -   `chaos-controller` (CRD-based chaos injection)

#### Observability Stack
-   **Prometheus** - 650+ metrics per scenario
-   **Loki** - Centralized logging
-   **Tempo** - Distributed tracing
-   **Grafana** - Real-time dashboards (Chaos Dashboard, GPU Metrics, System Metrics)

#### Massive Scale Data Generation (GKE)
-   **15 Parallel Streams** generating data on Google Cloud Platform
-   **3 `e2-standard-4` nodes** (~$0.40/hour)
-   **650+ metrics per Parquet file** (880KB each)
-   **~150 scenarios/hour throughput**
-   **50/50 healthy-to-failure ratio** for balanced training

## 📊 Current Data Status

### Current Data Status
*   **Generation Status:** Active (Local Generation with Port-Forwarding)
*   **Storage:** `gs://heimr-data-tokyo-snow-479722-a2`
*   **Format:** Parquet (Snappy compression)
*   **Schema Version:** v1.1 (Includes high-fidelity logs and traces)
*   **Validation:** Verified for Healthy, Latency Spike, Memory Leak, and Error Spike scenarios.

### Validation Scripts
Ad-hoc validation scripts are located in the `testing/` directory:
*   `verify_scenario_content.py`: Deep content verification for specific scenarios.
*   `validate_sample_detailed.py`: Schema and basic content validation.
*   `deep_inspect.py`: Manual inspection of log and trace samples.
*   `search_logs.py`: Search for keywords in the `log_context` column.
*   `dump_raw_logs.py`: Dump raw log content for debugging.

## 🏗️ Architecture

### Training Data Pipeline

```
Kubernetes (GKE)
  ├─ 15x Simulation Namespaces (sim-api, sim-api-2...15)
  │   ├─ Chaos Scenarios (API-001 to GPU-004)
  │   ├─ Prometheus (650+ metrics)
  │   └─ Data Generator (Python)
  │
  └─ Google Cloud Storage
      └─ Parquet Files (balanced dataset)
```

### Planned Inference Architecture (Phase 2)

```
Prometheus Metrics
    ↓
XGBoost Detector (Fast Classification)
    ↓
Llama-3.1-8B Explainer (Root Cause Analysis)
    ↓
Actionable Recommendations
```

## 🚀 What We're Building Next

### Phase 2: Hybrid AI Model Training

**Approach**: XGBoost + Fine-tuned Llama-3.1-8B (Option C - Hybrid)

1.  **XGBoost Bottleneck Detector**
    -   Fast binary classification (healthy vs failure)
    -   Input: 650+ aggregated metrics
    -   Target: >85% accuracy, <10ms inference
    -   Purpose: Real-time detection

2.  **Llama-3.1-8B Explainer** (LoRA Fine-tuned)
    -   Root cause analysis
    -   Actionable recommendations
    -   Human-readable explanations
    -   Target: <2s inference with 4-bit quantization

### Phase 3: Production Deployment

-   FastAPI inference service
-   Prometheus integration
-   Real-time alerting
-   Grafana dashboard integration

## 📂 Project Structure

```
Heimr.ai/
├── data-pipeline/          # Data generation & processing
│   ├── collectors/         # Prometheus exporters
│   ├── storage/            # Dataset builders & schemas
│   ├── run_gke_generation.py # GKE data generator
│   └── Dockerfile          # Containerized generator
│
├── k8s/                    # Kubernetes manifests
│   ├── templates/          # Namespace templates
│   └── build/              # Generated configs (15 namespaces)
│
├── model-training/         # ML training pipeline
│   ├── quick_validation.py # Pipeline validation
│   └── sample_data/        # 20 sample Parquet files
│
├── chaos-generator/        # Chaos engineering stack
│   ├── services/           # 6 microservice simulators
│   ├── chaos_controller/   # CRD-based chaos injection
│   └── grafana/            # Dashboards
│
├── scripts/                # Deployment automation
│   ├── deploy_to_gke.sh    # GKE deployment script
│   └── deploy_namespace.sh # Namespace deployment
│
└── docs/                   # Documentation
    └── data/               # Scenario definitions
```

## 🔧 Quick Start

### Prerequisites
-   Python 3.11+
-   Docker & Kubernetes (Minikube for local, GKE for scale)
-   Google Cloud SDK (for GCP deployment)
-   NVIDIA GPU (for model training - 3090 24GB recommended)

### Local Development (Minikube)

```bash
# Start Minikube
minikube start --driver=docker --cpus=4 --memory=8192

# Deploy chaos stack
kubectl apply -f k8s/templates/category-namespace/

# Access Grafana
kubectl port-forward svc/grafana 3000:3000 -n sim-api
# Visit http://localhost:3000 (admin/admin)
```

### GCP Deployment (15 Parallel Streams)

```bash
# Set up GCP infrastructure
./scripts/setup_gcp_infra.sh

# Deploy to GKE
./scripts/deploy_to_gke.sh us-central1-a tokyo-snow-479722-a2

# Deploy 15 namespaces
for i in {2..15}; do
    ./scripts/deploy_namespace.sh sim-api-$i us-central1-a
done

# Monitor data generation
gsutil ls -l gs://heimr-data-tokyo-snow-479722-a2 | wc -l
```

### Model Training Validation

```bash
# Install dependencies
cd model-training
python -m venv venv
source venv/bin/activate
pip install pandas pyarrow scikit-learn

# Download sample data
gsutil cp "gs://heimr-data-tokyo-snow-479722-a2/*.parquet" sample_data/

# Run validation
python quick_validation.py
```

## 📈 Metrics Collected

### Application Metrics
-   Request rates, latency percentiles (p50, p95, p99, p999)
-   Error rates (5xx, 429, total)
-   Concurrent requests

### Database Metrics (PostgreSQL)
-   Connections, transactions, query duration
-   Cache hits/misses, locks, replication lag

### Cache Metrics (Redis)
-   Command latency, memory usage
-   Hit/miss ratios, evictions, key counts

### Message Queue (Kafka)
-   Producer/consumer rates, lag
-   Partition metrics, broker health

### GPU Metrics (NVIDIA DCGM)
-   Utilization, temperature, power draw
-   VRAM usage, clocks, PCIe throughput

### Kubernetes Metrics
-   Pod/container resource usage (CPU, memory, network)
-   Node metrics, autoscaling events

## 🎓 Key Learnings

### Data Quality
✅ **No data leakage detected** (validated with mutual information analysis)  
✅ **Zero NULL values** across 650+ metrics  
✅ **91% non-zero metrics** (9% all-zero are expected - scenario-specific)  
✅ **50/50 class balance** achieved through interleaving
✅ **High-Fidelity Logs & Traces**: Pipeline v1.1 filters observability noise and actively captures error traces.

### Validation Results (Random Forest Baseline)
-   **Test Accuracy**: 91.67%
-   **Precision (Failure)**: 96%
-   **Recall (Failure)**: 93%
-   **Feature Importance**: Scrape durations, latency buckets, query durations, GPU temp

### Infrastructure Insights
-   **Cost**: ~$10/day for 15 parallel streams (~3,600 scenarios)
-   **Throughput**: 150 scenarios/hour
-   **File Size**: ~880KB per Parquet file (650+ columns, 6 time-series rows)

## 🗺️ Roadmap

- [x] **Phase 0**: Chaos Generator (50+ scenarios)
- [x] **Phase 1**: Data Pipeline (650+ metrics, GKE deployment)
- [ ] **Phase 2**: Model Training (XGBoost + Llama-3.1-8B)
- [ ] **Phase 3**: Inference Engine (FastAPI service)
- [ ] **Phase 4**: Production Deployment (Prometheus integration)

## 🤝 Contributing

This is currently a research project. Documentation and examples will be added as the project matures.

## 📝 License

MIT License - See [LICENSE](LICENSE) for details.

## 📚 Source of Truth
These files in the root directory define the authoritative state of the project:

-   [**PROJECT_STATE.md**](PROJECT_STATE.md) - Current status, infrastructure, and active tasks.
-   [**SYSTEM_MANIFEST.yaml**](SYSTEM_MANIFEST.yaml) - Architecture definition (services, ports, dependencies).
-   [**DATA_SCHEMA.yaml**](DATA_SCHEMA.yaml) - Training data schema (metrics, labels).
-   [**ENV_CONFIG.yaml**](ENV_CONFIG.yaml) - Centralized environment variable configuration.
-   [**FAILURE_SCENARIOS.yaml**](FAILURE_SCENARIOS.yaml) - Complete list of 50+ chaos scenarios.

## 🔗 Other Resources
-   [Training Data Schema (Python)](data-pipeline/storage/schema.py) - Implementation of the schema
-   [Grafana Dashboards](chaos-generator/grafana/dashboards/) - Real-time monitoring

---

**Status**: Currently generating training data on GKE. Model training pipeline development in progress.

**Next Milestone**: Reach 10,000 training examples, then begin XGBoost + LLM training.
