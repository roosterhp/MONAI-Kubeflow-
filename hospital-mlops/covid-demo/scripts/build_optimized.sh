#!/bin/bash
# Optimized build script with performance monitoring

set -e

echo "=========================================="
echo "Optimized COVID-19 Detection Pipeline Build"
echo "=========================================="

# Configuration
IMAGE_NAME="covid-pipeline"
IMAGE_TAG="v1-optimized"
DOCKERFILE="config/Dockerfile.optimized"

# Check which Dockerfile to use
echo "Selecting Dockerfile strategy:"
if [[ "$1" == "ngc" ]]; then
    DOCKERFILE="config/Dockerfile.ngc"
    IMAGE_TAG="v1-ngc"
    echo "✓ Using NGC-based Dockerfile (GPU optimized)"
elif [[ "$1" == "ultrafast" ]]; then
    DOCKERFILE="config/Dockerfile.ultrafast"
    IMAGE_TAG="v1-ultrafast"
    echo "✓ Using ultra-fast cached Dockerfile"
else
    echo "✓ Using multi-stage optimized Dockerfile"
fi

# Start build timer
START_TIME=$(date +%s)

# Step 1: Enable BuildKit for better performance
echo "[Step 1/5] Enabling Docker BuildKit..."
export DOCKER_BUILDKIT=1

# Step 2: Set Minikube Docker environment
echo "[Step 2/5] Setting Minikube Docker environment..."
eval $(minikube docker-env)
echo "✓ Using Minikube Docker daemon"

# Step 3: Clear Docker build cache (optional - comment out for cached builds)
if [[ "$2" == "clean" ]]; then
    echo "[Step 3/5] Cleaning Docker build cache..."
    docker builder prune -f
    echo "✓ Build cache cleared"
else
    echo "[Step 3/5] Skipping cache cleanup (use 'clean' arg to clear)"
fi

# Step 4: Build optimized Docker image
echo "[Step 4/5] Building optimized Docker image..."
docker build \
    --tag "${IMAGE_NAME}:${IMAGE_TAG}" \
    --file "${DOCKERFILE}" \
    --progress=plain \
    .
echo "✓ Image built: ${IMAGE_NAME}:${IMAGE_TAG}"

# Step 5: Performance reporting
END_TIME=$(date +%s)
BUILD_TIME=$((END_TIME - START_TIME))
echo "[Step 5/5] Build completed in ${BUILD_TIME} seconds"

# Verify image size
IMAGE_SIZE=$(docker images --format "table {{.Repository}}:{{.Tag}}\t{{.Size}}" | grep "${IMAGE_NAME}:${IMAGE_TAG}" | awk '{print $2}')
echo "✓ Image size: ${IMAGE_SIZE}"

# Step 6: Compile pipeline (if requested)
if [[ "$3" == "compile" ]]; then
    echo "[Step 6/6] Compiling Kubeflow pipeline..."
    python pipeline.py
    echo "✓ Pipeline compiled: covid_pipeline.yaml"
fi

echo ""
echo "=========================================="
echo "Optimized Build Complete!"
echo "=========================================="
echo ""
echo "Performance Summary:"
echo "- Build time: ${BUILD_TIME} seconds"
echo "- Image: ${IMAGE_NAME}:${IMAGE_TAG}"
echo "- Size: ${IMAGE_SIZE}"
echo ""
echo "Next steps:"
echo "1. kubectl apply -f kubernetes/pv.yaml"
echo "2. kubectl apply -f kubernetes/pvc.yaml"
echo "3. Update pipeline.py to use: BASE_IMAGE = '${IMAGE_NAME}:${IMAGE_TAG}'"
echo "4. Upload covid_pipeline.yaml to Kubeflow UI"
echo ""
echo "Build options:"
echo "- Clean build: ./scripts/build_optimized.sh <strategy> clean"
echo "- Compile pipeline: ./scripts/build_optimized.sh <strategy> '' compile"
echo "- NGC GPU: ./scripts/build_optimized.sh ngc"
echo "- Ultra-fast: ./scripts/build_optimized.sh ultrafast"
echo ""