# Category Namespace Template

This directory contains Kubernetes manifest templates for deploying a training data collection namespace.

## Structure

Each category namespace contains:

- **1 observability pod** (6 containers: Prometheus, Loki, Tempo, Promtail, OTel Collector, Grafana)
- **6 simulation pods** (sim-service-agent, sim-db, sim-cache, sim-queue, sim-inference, chaos-controller)

## Files

- `namespace.yaml` - Namespace definition (replace CATEGORY_NAME_PLACEHOLDER)
- `observability-pod.yaml` - Multi-container observability pod
- `sim-deployments.yaml` - All 6 simulation deployments
- `services.yaml` - ClusterIP services for sims, LoadBalancer for Grafana
- `configmaps/` - Configuration for all observability components

## Usage

To deploy a category namespace (e.g., `sim-api`):

```bash
# 1. Create namespace
cat namespace.yaml | sed 's/CATEGORY_NAME_PLACEHOLDER/sim-api/g' | kubectl apply -f -

# 2. Apply ConfigMaps
kubectl apply -f configmaps/ -n sim-api

# 3. Deploy observability
kubectl apply -f observability-pod.yaml -n sim-api

# 4. Deploy simulations
kubectl apply -f sim-deployments.yaml -n sim-api

# 5. Create services
kubectl apply -f services.yaml -n sim-api
```

## Access Grafana

```bash
# Get the LoadBalancer IP
kubectl get svc grafana -n sim-api

# Port-forward (if using minikube)
kubectl port-forward svc/grafana 3000:3000 -n sim-api
```

Then access at: http://localhost:3000 (admin/admin)

## Resource Requirements

Per namespace:
- **Observability pod**: ~650MB RAM, ~0.5 cores
- **Simulation pods**: ~700MB RAM, ~0.5 cores
- **Total**: ~1.35GB RAM, ~1 core

Fits comfortably on **t3.small (2 vCPU, 2 GB RAM)**
