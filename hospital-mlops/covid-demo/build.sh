#!/bin/bash
# Build script for COVID-19 Detection Pipeline (Linux/Mac)

set -e

echo "=========================================="
echo "Building COVID-19 Detection Pipeline"
echo "=========================================="

# Step 1: Set Minikube Docker environment
echo "[Step 1/4] Setting Minikube Docker environment..."
eval $(minikube docker-env)
echo "✓ Using Minikube Docker daemon"

# Step 2: Build Docker image
echo "[Step 2/4] Building Docker image..."
docker build -t covid-pipeline:v1 .
echo "✓ Image built: covid-pipeline:v1"

# Step 3: Verify image
echo "[Step 3/4] Verifying image..."
docker images | grep covid-pipeline
echo "✓ Image verified"

# Step 4: Compile pipeline
echo "[Step 4/4] Compiling Kubeflow pipeline..."
python pipeline.py
echo "✓ Pipeline compiled: covid_pipeline.yaml"

echo ""
echo "=========================================="
echo "Build complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. kubectl apply -f kubernetes/pv.yaml"
echo "2. kubectl apply -f kubernetes/pvc.yaml"
echo "3. Upload covid_pipeline.yaml to Kubeflow UI"
echo ""
