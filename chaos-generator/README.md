# Chaos Generator - Kubernetes Performance Testing Lab

**Status:** Archived Component (Part of Heimr.ai project pivot)

## Overview

This is a production-grade chaos engineering platform that was built to generate synthetic training data for ML-based performance bottleneck detection. It includes:

- **50+ Failure Scenarios** across 8 categories (API, Database, Cache, Queue, GPU, Network, Security, Infrastructure)
- **6 Microservice Simulators** with full observability instrumentation
- **Prometheus + Loki + Tempo** observability stack
- **GKE Terraform** infrastructure as code
- **Parallel data generation pipeline** for creating labeled training datasets

## Architecture

### Simulator Topology (Per Namespace)

```
sim-service-agent (Gateway)
    ↓
├─ sim-db (PostgreSQL simulator)
├─ sim-cache (Redis simulator)
├─ sim-queue (Kafka simulator)
└─ sim-inference (GPU inference simulator)

Observability Stack:
- Prometheus (metrics)
- Loki (logs)  
- Tempo (traces)
- Promtail (log collection)
```

## Quick Start

### Deploy to GKE

```bash
cd terraform
terraform init
terraform apply

cd ../scripts
./deploy_to_gke.sh us-central1-a <your-gcp-project-id>
```

### Local Testing (Minikube)

```bash
./scripts/setup_minikube.sh
kubectl apply -f k8s/templates/category-namespace/
```

## Why This Was Archived

**Original goal:** Generate synthetic training data for ML anomaly detection

**Pivot rationale:**
1. Market research showed the real gap is **load test result analysis** (JMeter/k6/Gatling)
2. Synthetic data proved less valuable than real production datasets
3. Open-source opportunity is in load testing analysis, not chaos engineering

**New direction:** Build AI analyst for performance test results

See `/COMBINED_FEEDBACK.md` in root for full analysis.

## License

MIT License
