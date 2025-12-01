#!/bin/bash
set -e

NAMESPACE=$1

if [ -z "$NAMESPACE" ]; then
    echo "Usage: $0 <NAMESPACE>"
    exit 1
fi

# Export PATH for gke-gcloud-auth-plugin
export PATH=$PATH:$(pwd)/google-cloud-sdk/bin

echo "Deploying simulation stack to namespace: $NAMESPACE"

# 1. Prepare Build Directory
BUILD_DIR="k8s/build/$NAMESPACE"
mkdir -p $BUILD_DIR
rm -rf $BUILD_DIR/*

echo "Preparing manifests in $BUILD_DIR..."

# Copy templates
cp k8s/templates/category-namespace/namespace.yaml $BUILD_DIR/
cp -r k8s/templates/category-namespace/configmaps $BUILD_DIR/
cp k8s/templates/category-namespace/chaos-rbac.yaml $BUILD_DIR/
cp k8s/templates/category-namespace/prometheus-rbac.yaml $BUILD_DIR/
cp k8s/templates/category-namespace/services.yaml $BUILD_DIR/

# Use GKE manifests if available (for image paths), otherwise templates
if [ -f "k8s/build/gke/sim-deployments.yaml" ]; then
    cp k8s/build/gke/sim-deployments.yaml $BUILD_DIR/
    cp k8s/build/gke/observability-pod.yaml $BUILD_DIR/
else
    cp k8s/templates/category-namespace/sim-deployments.yaml $BUILD_DIR/
    cp k8s/templates/category-namespace/observability-pod.yaml $BUILD_DIR/
fi

# Replace Namespace in all files
# We replace 'sim-api' with the target namespace.
# Note: namespace.yaml uses CATEGORY_NAME_PLACEHOLDER, others might use sim-api.
# We'll do both to be safe.
find $BUILD_DIR -type f -name "*.yaml" -exec sed -i "s/CATEGORY_NAME_PLACEHOLDER/$NAMESPACE/g" {} +
find $BUILD_DIR -type f -name "*.yaml" -exec sed -i "s/namespace: sim-api/namespace: $NAMESPACE/g" {} +

# 2. Apply Manifests
echo "Applying manifests..."
kubectl apply -f $BUILD_DIR/namespace.yaml
kubectl apply -f $BUILD_DIR/configmaps/ -n $NAMESPACE
kubectl apply -f $BUILD_DIR/chaos-rbac.yaml -n $NAMESPACE
kubectl apply -f $BUILD_DIR/prometheus-rbac.yaml -n $NAMESPACE
kubectl apply -f $BUILD_DIR/observability-pod.yaml -n $NAMESPACE
kubectl apply -f $BUILD_DIR/sim-deployments.yaml -n $NAMESPACE
kubectl apply -f $BUILD_DIR/services.yaml -n $NAMESPACE

# 3. Copy GCS Secret
echo "Copying GCS credentials..."
kubectl get secret gcs-credentials -n sim-api -o yaml | sed "s/namespace: sim-api/namespace: $NAMESPACE/" | kubectl apply -f -

# 4. Deploy Generator
echo "Deploying Data Generator..."
# We need to prepare the generator manifest too
cp k8s/templates/category-namespace/generator-deployment.yaml $BUILD_DIR/
# Replace placeholder if it exists, but we also rely on env vars. 
# However, the manifest has CATEGORY_NAME_PLACEHOLDER in metadata.namespace
sed -i "s/CATEGORY_NAME_PLACEHOLDER/$NAMESPACE/g" $BUILD_DIR/generator-deployment.yaml
kubectl apply -f $BUILD_DIR/generator-deployment.yaml -n $NAMESPACE

echo "Deployment to $NAMESPACE complete!"
kubectl get pods -n $NAMESPACE
