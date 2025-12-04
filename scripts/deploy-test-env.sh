#!/bin/bash
# Copyright (c) 2025 Juan Estevez Castillo
# Licensed under AGPL v3. Commercial licenses available.
# See LICENSE or https://www.gnu.org/licenses/agpl-3.0.html
#
# Deploy Heimr Test Environment to Minikube
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "================================================================"
echo "  Heimr Test Environment Deployment"
echo "================================================================"
echo ""

# Check prerequisites
echo "Checking prerequisites..."
if ! command -v minikube &> /dev/null; then
    echo "ERROR: minikube not found. Install it first."
    exit 1
fi

if ! command -v kubectl &> /dev/null; then
    echo "ERROR: kubectl not found. Install it first."
    exit 1
fi

# Check if minikube is running
if ! minikube status &> /dev/null; then
    echo "Starting minikube..."
    minikube start --cpus=4 --memory=8192 --driver=docker
fi

echo "Minikube is running."
echo ""

# Build test application image
echo "Building test application image..."
cd "$PROJECT_ROOT/k8s/test-app/app"
eval $(minikube docker-env)
docker build -t heimr-test-app:latest .
echo "Test application image built."
echo ""

# Deploy namespace
echo "Creating namespace..."
kubectl apply -f "$PROJECT_ROOT/k8s/observability/namespace.yaml"
echo ""

# Deploy PostgreSQL first (needs to initialize before app)
echo "Deploying PostgreSQL..."
kubectl apply -f "$PROJECT_ROOT/k8s/test-app/postgres.yaml"
echo "Waiting for PostgreSQL to be ready (this may take a while for data init)..."
kubectl wait --for=condition=ready pod -l app=postgres -n heimr-test --timeout=300s || true
echo ""

# Deploy observability stack
echo "Deploying observability stack..."
kubectl apply -f "$PROJECT_ROOT/k8s/observability/prometheus.yaml"
kubectl apply -f "$PROJECT_ROOT/k8s/observability/loki.yaml"
kubectl apply -f "$PROJECT_ROOT/k8s/observability/tempo.yaml"
kubectl apply -f "$PROJECT_ROOT/k8s/observability/grafana.yaml"
kubectl apply -f "$PROJECT_ROOT/k8s/observability/services.yaml"
echo ""

# Deploy test application
echo "Deploying test application..."
kubectl apply -f "$PROJECT_ROOT/k8s/test-app/testing_system.yaml"
echo ""

# Wait for all deployments
echo "Waiting for all deployments to be ready..."
kubectl wait --for=condition=available deployment --all -n heimr-test --timeout=180s || true
echo ""

# Show status
echo "================================================================"
echo "  Deployment Complete!"
echo "================================================================"
echo ""
kubectl get pods -n heimr-test
echo ""

# Get Minikube IP
MINIKUBE_IP=$(minikube ip)

echo "================================================================"
echo "  Access URLs (via NodePort):"
echo "================================================================"
echo "  Grafana:     http://$MINIKUBE_IP:30300 (admin/admin)"
echo "  Prometheus:  http://$MINIKUBE_IP:30909"
echo "  Loki:        http://$MINIKUBE_IP:30310"
echo "  Tempo:       http://$MINIKUBE_IP:30320"
echo "  Test App:    http://$MINIKUBE_IP:30808"
echo ""
echo "Alternatively, use 'minikube service <name> -n heimr-test'"
echo ""
echo "To run load tests:"
echo "  k6:      k6 run load-tests/k6/load-test.js -e BASE_URL=http://$MINIKUBE_IP:30808"
echo "  locust:  locust -f load-tests/locust/locustfile.py --host=http://$MINIKUBE_IP:30808"
echo ""
