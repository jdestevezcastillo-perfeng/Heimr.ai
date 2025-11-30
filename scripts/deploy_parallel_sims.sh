#!/bin/bash
set -e

REPLICAS=20

echo "🚀 Deploying $REPLICAS parallel simulator topologies..."

for ((i=0; i<REPLICAS; i++)); do
    NS="sim-api-$i"
    echo "Processing namespace: $NS"
    
    # Create namespace if not exists
    kubectl create namespace $NS --dry-run=client -o yaml | kubectl apply -f -
    
    # Apply RBAC (Chaos Controller)
    cat k8s/templates/category-namespace/rbac-sim-api.yaml | \
        sed "s/namespace: sim-api/namespace: $NS/g" | \
        sed "s/name: chaos-controller-binding-sim-api/name: chaos-controller-binding-$NS/g" | \
        kubectl apply -f -
    
    # Apply Prometheus RBAC
    kubectl apply -f k8s/templates/category-namespace/prometheus-rbac.yaml -n $NS
    
    # Deploy ConfigMaps
    kubectl apply -f k8s/templates/category-namespace/configmaps/ -n $NS 2>/dev/null || true
    
    # Deploy Observability Pod
    kubectl apply -f k8s/templates/category-namespace/observability-pod.yaml -n $NS
    
    # Deploy Simulators
    kubectl apply -f k8s/templates/category-namespace/sim-deployments.yaml -n $NS
    
    # Deploy Services
    kubectl apply -f k8s/templates/category-namespace/services.yaml -n $NS
done

echo "✅ Deployed $REPLICAS topologies."
