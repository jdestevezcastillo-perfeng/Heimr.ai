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
    # We need to update the namespace in the RBAC file dynamically or use sed
    cat k8s/templates/category-namespace/rbac-sim-api.yaml | \
        sed "s/namespace: sim-api/namespace: $NS/g" | \
        sed "s/name: chaos-controller-binding-sim-api/name: chaos-controller-binding-$NS/g" | \
        kubectl apply -f -
    
    # Deploy Simulators
    kubectl apply -f k8s/templates/category-namespace/sim-deployments.yaml -n $NS
    
    # Deploy Services
    kubectl apply -f k8s/templates/category-namespace/services.yaml -n $NS
done

echo "✅ Deployed $REPLICAS topologies."
