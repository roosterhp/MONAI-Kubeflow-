#!/bin/bash
# Quick build script - Run this NOW to fix ImagePullBackOff

echo ""
echo "========================================"
echo "BUILDING DOCKER IMAGE IN MINIKUBE"
echo "========================================"
echo ""

# Set Minikube Docker environment
echo "[1/3] Setting Minikube Docker environment..."
eval $(minikube docker-env)
echo "Done!"
echo ""

# Build Docker image
echo "[2/3] Building Docker image (this may take 2-5 minutes)..."
docker build -t covid-pipeline:v1 .

if [ $? -eq 0 ]; then
    echo "Done!"
    echo ""
else
    echo "Build failed!"
    exit 1
fi

# Verify image
echo "[3/3] Verifying image..."
docker images | grep covid-pipeline
echo ""

echo "========================================"
echo "BUILD COMPLETE!"
echo "========================================"
echo ""

echo "Next steps:"
echo "1. Go back to Kubeflow UI"
echo "2. Delete the failed pipeline run"
echo "3. Create a NEW run"
echo "4. Pipeline should now work!"
echo ""
