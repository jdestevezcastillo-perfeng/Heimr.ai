#!/bin/bash
set -e

echo "🚀 Starting Minikube..."
minikube start --driver=docker --cpus=4 --memory=8192 --addons=metrics-server,ingress

echo "✅ Minikube started!"
echo "💡 To point your shell to Minikube's Docker daemon, run:"
echo "   eval \$(minikube -p minikube docker-env)"
