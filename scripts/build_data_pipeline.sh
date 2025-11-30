#!/bin/bash
set -e

PROJECT_ID="tokyo-snow-479722-a2"
REGION="asia-northeast1"
IMAGE_NAME="${REGION}-docker.pkg.dev/${PROJECT_ID}/heimr/data-pipeline:latest"

echo "📦 Building data-pipeline..."
docker build -t $IMAGE_NAME -f data-pipeline/Dockerfile .

echo "⬆️  Pushing data-pipeline..."
docker push $IMAGE_NAME

echo "✅ Data pipeline image pushed: $IMAGE_NAME"
