#!/bin/bash
set -e

PROJECT_ID="tokyo-snow-479722-a2"
REGION="us-central1"
REPO_NAME="heimr"
REPO_PATH="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO_NAME}"

echo "🔐 Configuring Docker authentication..."
# Ensure gcloud is in PATH
export PATH=$PATH:/home/lostborion/Heimr.ai/google-cloud-sdk/bin
gcloud auth configure-docker ${REGION}-docker.pkg.dev --quiet

IMAGES=(
    "sim-service-agent:instrumented"
    "sim-db-agent:instrumented"
    "sim-cache-agent:instrumented"
    "sim-queue-agent:instrumented"
    "sim-inference:instrumented"
    "chaos-controller:instrumented"
)

echo "🚀 Pushing images to Artifact Registry..."

for IMAGE in "${IMAGES[@]}"; do
    FULL_IMAGE="${REPO_PATH}/${IMAGE}"
    echo "Pushing $FULL_IMAGE..."
    docker push "$FULL_IMAGE"
done

echo "✅ All images pushed successfully!"
