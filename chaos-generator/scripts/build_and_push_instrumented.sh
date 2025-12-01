#!/bin/bash
set -e

PROJECT_ID="tokyo-snow-479722-a2"
REGION="asia-northeast1"
GCLOUD="./google-cloud-sdk/bin/gcloud"

echo "🔨 Building and pushing instrumented Docker images..."

# Authenticate with GCR
echo "Authenticating with GCR..."
# $GCLOUD auth configure-docker ${REGION}-docker.pkg.dev --quiet

# Build and push simulators
SIMULATORS=(
    "sim-service-agent"
    "sim-cache-agent"
    "sim-db-agent"
    "sim-queue-agent"
    "sim-inference"
)

for sim in "${SIMULATORS[@]}"; do
    echo ""
    echo "📦 Building $sim..."
    cd chaos-generator/simulators/$sim
    
    IMAGE_NAME="${REGION}-docker.pkg.dev/${PROJECT_ID}/heimr/${sim}:instrumented"
    
    docker build -t $IMAGE_NAME .
    
    echo "⬆️  Pushing $sim..."
    docker push $IMAGE_NAME
    
    cd ../../..
done

# Build and push chaos-controller
echo ""
echo "📦 Building chaos-controller..."
cd chaos-generator/controllers/chaos-controller

IMAGE_NAME="${REGION}-docker.pkg.dev/${PROJECT_ID}/heimr/chaos-controller:instrumented"

docker build -t $IMAGE_NAME .

echo "⬆️  Pushing chaos-controller..."
docker push $IMAGE_NAME

cd ../../..

echo ""
echo "✅ All images built and pushed successfully!"
echo ""
echo "Images pushed:"
for sim in "${SIMULATORS[@]}"; do
    echo "  - ${REGION}-docker.pkg.dev/${PROJECT_ID}/heimr/${sim}:instrumented"
done
echo "  - ${REGION}-docker.pkg.dev/${PROJECT_ID}/heimr/chaos-controller:instrumented"
