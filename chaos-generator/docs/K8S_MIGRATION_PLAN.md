# Kubernetes Migration Plan

## Objective
Migrate the entire Heimr.ai stack (Data Pipeline, Observability, Dashboard, and Error Generator) from local scripts and Docker Compose to a production-ready Kubernetes cluster.

## 1. Architecture Overview

### Current State
- **Data Pipeline**: Python scripts running locally (`scripts/`).
- **Observability**: Docker Compose (`prometheus`, `grafana`, `loki`, `tempo`).
- **Error Generator**: Helm Chart (`chaos-generator/charts/simulation-topology`) + Controller.
- **Dashboard**: Next.js app running locally.

### Target State (Kubernetes)
- **Namespace: `heimr-core`**
  - **Dashboard**: Deployment + Service + Ingress.
  - **Observability**: Prometheus Operator stack (Prometheus, Grafana, Alertmanager).
  - **Data Pipeline**: Kubernetes Jobs / CronJobs for training and data generation.
- **Namespace: `heimr-chaos`**
  - **Controller**: `chaos-controller` Deployment.
  - **Simulations**: Ephemeral namespaces (`sim-xxx`) created by the generator script.

## 2. Migration Phases

### Phase 1: Containerization (Complete)
- [x] Error Generator Archetypes.
- [x] Chaos Controller.
- [ ] **Data Pipeline**: Need Dockerfile for `scripts/generate_training_data.py` and training scripts.
- [ ] **Dashboard**: Need Dockerfile for the Next.js app.

### Phase 2: Manifests & Helm Charts
- **Observability**: Use `kube-prometheus-stack` Helm chart.
- **Dashboard**: Create `charts/heimr-dashboard`.
- **Data Pipeline**: Create `charts/heimr-pipeline` (Jobs).
- **Error Generator**: Already has `charts/simulation-topology`.

### Phase 3: Storage & Persistence
- **Prometheus/Loki**: Configure PersistentVolumeClaims (PVCs).
- **Training Data**: Use a shared ReadWriteMany (RWX) volume or S3-compatible object storage (MinIO) for the pipeline to store datasets.

### Phase 4: Ingress & Networking
- Set up NGINX Ingress Controller.
- Expose Dashboard at `dashboard.heimr.local`.
- Expose Grafana at `grafana.heimr.local`.

## 3. Directory Structure
We will organize Kubernetes resources in a new `k8s/` directory:

```
k8s/
├── base/                   # Plain manifests
│   ├── dashboard/
│   ├── pipeline/
│   └── rbac/
├── overlays/               # Kustomize overlays (dev, prod)
│   ├── dev/
│   └── prod/
└── charts/                 # Custom Helm charts
    ├── simulation-topology/ (moved from chaos-generator)
    └── heimr-dashboard/
```

## 4. Execution Steps
1.  Create `k8s/` directory structure.
2.  Dockerize Dashboard and Data Pipeline.
3.  Deploy Observability Stack (Prometheus/Grafana).
4.  Deploy Dashboard.
5.  Run Data Generation as a K8s Job.
