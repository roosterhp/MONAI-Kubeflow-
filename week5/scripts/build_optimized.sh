#!/bin/bash

# Optimized Docker Build Script
# Usage: ./build_optimized.sh [variant]
# Variants: optimized (default), ngc, ultrafast

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WEEK5_DIR="$(dirname "$SCRIPT_DIR")"
DOCKERFILE="$WEEK5_DIR/config/Dockerfile.optimized"
DEFAULT_TAG="covid-hospital-pipeline:optimized"

# Parse arguments
VARIANT=${1:-optimized}
case $VARIANT in
    "optimized")
        DOCKERFILE="$WEEK5_DIR/config/Dockerfile.optimized"
        TAG="covid-hospital-pipeline:optimized"
        ;;
    "ngc")
        DOCKERFILE="$WEEK5_DIR/config/Dockerfile.ngc"
        TAG="covid-hospital-pipeline:ngc"
        ;;
    "ultrafast")
        DOCKERFILE="$WEEK5_DIR/config/Dockerfile.ultrafast"
        TAG="covid-hospital-pipeline:ultrafast"
        ;;
    *)
        echo "Unknown variant: $VARIANT"
        echo "Usage: $0 [optimized|ngc|ultrafast]"
        exit 1
        ;;
esac

echo "🚀 Building COVID-19 Detection Pipeline Docker Image"
echo "📁 Directory: $WEEK5_DIR"
echo "🐳 Dockerfile: $DOCKERFILE"
echo "🏷️  Tag: $TAG"
echo "⚡ Variant: $VARIANT"
echo ""

# Ensure we're in the week5 directory
cd "$WEEK5_DIR"

# Enable Docker BuildKit for parallel builds
export DOCKER_BUILDKIT=1

echo "⏰ Starting optimized build..."
BUILD_START=$(date +%s)

# Build with BuildKit for parallelization
docker build \
    --file "$DOCKERFILE" \
    --tag "$TAG" \
    --build-arg BUILDKIT_INLINE_CACHE=1 \
    --progress=plain \
    .

BUILD_END=$(date +%s)
BUILD_TIME=$((BUILD_END - BUILD_START))

echo ""
echo "✅ Build completed in ${BUILD_TIME}s"
echo ""
echo "🐋 Built image: $TAG"
echo "📊 Size: $(docker images --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}" "$TAG" | tail -n 1)"
echo ""
echo "🚀 To push to registry:"
echo "   docker push $TAG"
echo ""
echo "🏥 To test locally:"
echo "   docker run --rm $TAG python components/lung_segment.py --help"

# Optional: Test the container
if [[ "${2:-}" == "--test" ]]; then
    echo ""
    echo "🧪 Testing container..."
    docker run --rm "$TAG" python -c "
import torch
import monai
import SimpleITK as sitk
import nibabel as nib
print('✅ All dependencies imported successfully')
print(f'🔥 PyTorch: {torch.__version__}')
print(f'🧠 MONAI: {monai.__version__}')
"
fi