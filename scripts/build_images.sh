#!/bin/bash
set -e

echo "🐳 Building Docker images into Minikube..."

REGISTRY="heimr-registry:5000"

# Define images and their paths
# Format: "image_name:path"
IMAGES=(
    "sim-service-agent:error-generator/simulators/sim-service-agent"
    "sim-db-agent:error-generator/simulators/sim-db-agent"
    "sim-cache-agent:error-generator/simulators/sim-cache-agent"
    "sim-queue-agent:error-generator/simulators/sim-queue-agent"
    "sim-inference:error-generator/simulators/sim-inference"
    "chaos-controller:error-generator/controllers/chaos-controller"
    "data-pipeline:data-pipeline"
)

# Point Docker to Minikube (Optional, but minikube image build handles this)
# eval $(minikube docker-env)

for entry in "${IMAGES[@]}"; do
    NAME="${entry%%:*}"
    PATH="${entry#*:}"
    
    FULL_IMAGE="$NAME:latest"
    
    echo "🔨 Building $FULL_IMAGE from $PATH..."
    /usr/local/bin/minikube image build -t "$FULL_IMAGE" "$PATH"
done

echo "✅ All images built successfully!"
