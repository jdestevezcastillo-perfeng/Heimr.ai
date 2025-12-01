#!/bin/bash
set -e

# Configuration
PROJECT_ID=$1
REGION="us-central1"
ZONE="us-central1-a"
CLUSTER_NAME="heimr-cluster"

if [ -z "$PROJECT_ID" ]; then
    echo "Usage: $0 <PROJECT_ID>"
    exit 1
fi

echo "Setting up GCP Infrastructure for Project: $PROJECT_ID"

# 1. Set Project
echo "Setting project..."
./google-cloud-sdk/bin/gcloud config set project $PROJECT_ID

# 2. Enable APIs
echo "Enabling necessary APIs (this may take a minute)..."
./google-cloud-sdk/bin/gcloud services enable container.googleapis.com artifactregistry.googleapis.com

# 3. Create GKE Cluster
echo "Creating GKE Cluster '$CLUSTER_NAME' in $ZONE..."
if ! ./google-cloud-sdk/bin/gcloud container clusters describe $CLUSTER_NAME --zone $ZONE > /dev/null 2>&1; then
    ./google-cloud-sdk/bin/gcloud container clusters create $CLUSTER_NAME \
        --zone $ZONE \
        --num-nodes 1 \
        --machine-type e2-standard-4 \
        --disk-size 50GB \
        --enable-autoscaling --min-nodes 1 --max-nodes 3 \
        --scopes "https://www.googleapis.com/auth/cloud-platform"
else
    echo "Cluster '$CLUSTER_NAME' already exists."
fi

# 4. Get Credentials
echo "Getting cluster credentials..."
./google-cloud-sdk/bin/gcloud container clusters get-credentials $CLUSTER_NAME --zone $ZONE

echo "Infrastructure setup complete!"
echo "You can now run: ./scripts/deploy_to_gke.sh $PROJECT_ID $REGION $CLUSTER_NAME"
