#!/bin/bash
set -e

# Configuration
PROJECT_ID=$1
REGION=$2
CLUSTER_NAME=$3
ZONE=$4
REPO_NAME="heimr-sim-images"

if [ -z "$PROJECT_ID" ] || [ -z "$REGION" ] || [ -z "$CLUSTER_NAME" ] || [ -z "$ZONE" ]; then
    echo "Usage: $0 <PROJECT_ID> <REGION> <CLUSTER_NAME> <ZONE>"
    exit 1
fi

# Point Docker to Minikube daemon
eval $(minikube -p minikube docker-env)

# Export PATH for gke-gcloud-auth-plugin
export PATH=$PATH:$(pwd)/google-cloud-sdk/bin

echo "Deploying to GKE with:"
echo "  Project: $PROJECT_ID"
echo "  Region: $REGION"
echo "  Zone: $ZONE"
echo "  Cluster: $CLUSTER_NAME"
echo "  Repo: $REPO_NAME"

# 1. Configure gcloud
echo "Configuring gcloud..."
./google-cloud-sdk/bin/gcloud config set project $PROJECT_ID
./google-cloud-sdk/bin/gcloud config set compute/region $REGION
./google-cloud-sdk/bin/gcloud config set compute/zone $ZONE

# 2. Get Cluster Credentials
echo "Getting cluster credentials..."
./google-cloud-sdk/bin/gcloud container clusters get-credentials $CLUSTER_NAME --zone $ZONE

# 3. Create Artifact Registry Repository (if not exists)
echo "Creating Artifact Registry repository..."
if ! ./google-cloud-sdk/bin/gcloud artifacts repositories describe $REPO_NAME --location=$REGION > /dev/null 2>&1; then
    ./google-cloud-sdk/bin/gcloud artifacts repositories create $REPO_NAME \
        --repository-format=docker \
        --location=$REGION \
        --description="Heimr.ai Simulation Images"
else
    echo "Repository $REPO_NAME already exists."
fi

# 4. Configure Docker Auth
echo "Configuring Docker authentication..."
./google-cloud-sdk/bin/gcloud auth configure-docker ${REGION}-docker.pkg.dev

# 5. Tag and Push Images
IMAGES=(
    "sim-service-agent"
    "sim-db"
    "sim-cache"
    "sim-queue"
    "sim-inference"
    "chaos-controller"
)

REPO_PATH="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO_NAME}"

for IMAGE in "${IMAGES[@]}"; do
    echo "Processing $IMAGE..."
    # Retag
    docker tag ${IMAGE}:latest ${REPO_PATH}/${IMAGE}:latest
    # Push
    docker push ${REPO_PATH}/${IMAGE}:latest
done

# 6. Update Manifests
echo "Updating manifests..."
# Create a temporary directory for modified manifests
mkdir -p k8s/build/gke
cp -r k8s/templates/category-namespace/* k8s/build/gke/

# Update image paths in sim-deployments.yaml
# We use a loop to replace each image
for IMAGE in "${IMAGES[@]}"; do
    sed -i "s|image: ${IMAGE}:latest|image: ${REPO_PATH}/${IMAGE}:latest|g" k8s/build/gke/sim-deployments.yaml
done

# Update ImagePullPolicy to Always (or IfNotPresent)
sed -i 's|imagePullPolicy: Never|imagePullPolicy: Always|g' k8s/build/gke/sim-deployments.yaml

# 7. Deploy
echo "Deploying to GKE..."
# Create namespace
cat k8s/build/gke/namespace.yaml | sed 's/CATEGORY_NAME_PLACEHOLDER/sim-api/g' | kubectl apply -f -

# Apply ConfigMaps
kubectl apply -f k8s/build/gke/configmaps/ -n sim-api

# Apply RBAC (Chaos Controller & Prometheus)
kubectl apply -f k8s/build/gke/chaos-rbac.yaml
# Note: We need to ensure prometheus-rbac.yaml is also copied/applied if it exists in templates
if [ -f "k8s/templates/category-namespace/prometheus-rbac.yaml" ]; then
    kubectl apply -f k8s/templates/category-namespace/prometheus-rbac.yaml
fi

# Apply CRD
kubectl apply -f k8s/base/controller/crd.yaml

# Deploy Observability
kubectl apply -f k8s/build/gke/observability-pod.yaml -n sim-api

# Deploy Simulations
kubectl apply -f k8s/build/gke/sim-deployments.yaml -n sim-api

# Create Services
kubectl apply -f k8s/build/gke/services.yaml -n sim-api

echo "Deployment complete! Checking pods..."
kubectl get pods -n sim-api
