#!/bin/bash
set -e

PROJECT_ID="tokyo-snow-479722-a2"
REGION="us-central1"
REPO_NAME="heimr"
IMAGE_NAME="data-pipeline"
TAG="latest"
FULL_IMAGE="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO_NAME}/${IMAGE_NAME}:${TAG}"

echo "🔨 Building ${IMAGE_NAME}..."
docker build -t ${FULL_IMAGE} -f data-pipeline/Dockerfile .

echo "🔐 Configuring Docker authentication..."
export PATH=$PATH:/home/lostborion/Heimr.ai/google-cloud-sdk/bin
gcloud auth configure-docker ${REGION}-docker.pkg.dev --quiet

echo "🚀 Pushing ${FULL_IMAGE}..."
docker push ${FULL_IMAGE}

echo "✅ ${IMAGE_NAME} built and pushed successfully!"
