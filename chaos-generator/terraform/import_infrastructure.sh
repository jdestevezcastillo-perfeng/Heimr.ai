#!/bin/bash
set -e

# Import existing GCP infrastructure into Terraform state
# This script imports resources that were created manually before Terraform

PROJECT_ID="tokyo-snow-479722-a2"
REGION="asia-northeast1"
ZONE="us-central1-a"
CLUSTER_NAME="heimr-cluster"
REPO_NAME="heimr"
BUCKET_NAME="heimr-data-tokyo-snow-479722-a2"

# Setup Authentication using active gcloud session
# We look for gcloud in the parent directory if not in PATH
if ! command -v gcloud &> /dev/null; then
    if [ -f "../google-cloud-sdk/bin/gcloud" ]; then
        export PATH=$PATH:$(pwd)/../google-cloud-sdk/bin
    else
        echo "⚠️  gcloud not found in PATH or ../google-cloud-sdk/bin. Assuming it's available or Terraform has credentials."
    fi
fi

if command -v gcloud &> /dev/null; then
    echo "🔑 Fetching access token from gcloud..."
    export GOOGLE_OAUTH_ACCESS_TOKEN=$(gcloud auth print-access-token)
else
    echo "⚠️  Could not find gcloud to fetch access token. Proceeding with standard Terraform auth..."
fi

echo "🔄 Importing existing GCP infrastructure into Terraform state..."
echo "Project: $PROJECT_ID"
echo ""

# Initialize Terraform if not already done
echo "📦 Initializing Terraform..."
terraform init

# Import GKE Cluster
echo "📥 Importing GKE cluster: $CLUSTER_NAME"
terraform import google_container_cluster.primary "projects/$PROJECT_ID/locations/$ZONE/clusters/$CLUSTER_NAME" || echo "⚠️  Cluster already imported or doesn't exist"

# Import GKE Node Pool
echo "📥 Importing GKE node pool: default-pool"
terraform import google_container_node_pool.primary_nodes "projects/$PROJECT_ID/locations/$ZONE/clusters/$CLUSTER_NAME/nodePools/default-pool" || echo "⚠️  Node pool already imported or doesn't exist"

# Import Artifact Registry Repository
echo "📥 Importing Artifact Registry repository: $REPO_NAME"
terraform import google_artifact_registry_repository.repo "projects/$PROJECT_ID/locations/$REGION/repositories/$REPO_NAME" || echo "⚠️  Repository already imported or doesn't exist"

# Import GCS Bucket
echo "📥 Importing GCS bucket: $BUCKET_NAME"
terraform import google_storage_bucket.data_bucket "$BUCKET_NAME" || echo "⚠️  Bucket already imported or doesn't exist"

echo ""
echo "✅ Import complete!"
echo ""
echo "🔍 Verifying state..."
terraform state list

echo ""
echo "📋 Running terraform plan to verify..."
terraform plan

echo ""
echo "✨ Done! Your infrastructure is now managed by Terraform."
echo ""
echo "Next steps:"
echo "  1. Review the plan output above"
echo "  2. If there are changes, review terraform.tfstate"
echo "  3. To test destroy: terraform plan -destroy"
echo "  4. To actually destroy: terraform destroy"
