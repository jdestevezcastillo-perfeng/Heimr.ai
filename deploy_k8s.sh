#!/bin/bash
set -e

echo "🚀 Starting Heimr.ai Kubernetes Deployment..."

# 1. Create Namespaces
echo "Creating namespaces..."
kubectl create namespace heimr-core --dry-run=client -o yaml | kubectl apply -f -
kubectl create namespace heimr-chaos --dry-run=client -o yaml | kubectl apply -f -

# 2. Deploy Observability Stack
echo "Deploying Observability Stack (Prometheus/Grafana)..."
echo "First pass: Installing CRDs (errors expected)..."
kubectl kustomize --enable-helm k8s/base/observability | kubectl apply --server-side --force-conflicts -f - || true
echo "Waiting for CRDs to be established..."
sleep 15
echo "Second pass: Deploying full stack..."
kubectl kustomize --enable-helm k8s/base/observability | kubectl apply --server-side --force-conflicts -f -

# 3. Create ConfigMap for Scenarios
echo "Creating Failure Scenarios ConfigMap..."
kubectl create configmap failure-scenarios \
    --from-file=docs/data/failure_scenarios.yaml \
    -n heimr-core \
    --dry-run=client -o yaml | kubectl apply -f -

# 4. Deploy Data Pipeline RBAC & CronJob
echo "Deploying Data Pipeline..."
kubectl apply -f k8s/base/pipeline/rbac.yaml
kubectl apply -f k8s/base/pipeline/pvc.yaml
kubectl apply -f k8s/base/pipeline/cronjob.yaml

# 5. Deploy Chaos Controller
echo "📦 Applying Chaos Controller CRDs..."
kubectl apply -f k8s/base/controller/crd.yaml

echo "🤖 Deploying Chaos Controller..."
kubectl apply -f k8s/base/controller/rbac.yaml
kubectl apply -f k8s/base/controller/deployment.yaml

echo "✅ Deployment Complete!"
echo "Check status with: kubectl get pods -n heimr-core"
