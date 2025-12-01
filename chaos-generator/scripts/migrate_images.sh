#!/bin/bash
set -e

OLD_REPO="asia-northeast1-docker.pkg.dev/tokyo-snow-479722-a2/heimr"
NEW_REPO="us-central1-docker.pkg.dev/tokyo-snow-479722-a2/heimr"

IMAGES=(
    "sim-service-agent:instrumented"
    "sim-db-agent:instrumented"
    "sim-cache-agent:instrumented"
    "sim-queue-agent:instrumented"
    "sim-inference:instrumented"
    "chaos-controller:instrumented"
)

for img in "${IMAGES[@]}"; do
    echo "Processing $img..."
    
    # Retag
    docker tag "$OLD_REPO/$img" "$NEW_REPO/$img"
    
    # Push
    echo "Pushing $NEW_REPO/$img..."
    docker push "$NEW_REPO/$img"
done

echo "All images migrated to $NEW_REPO"
