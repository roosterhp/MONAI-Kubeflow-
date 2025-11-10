#!/bin/bash
# Prepare Input Data for COVID-19 Pipeline
# Copy 4 patient CT scans to Minikube

echo ""
echo "========================================"
echo "PREPARING INPUT DATA (4 PATIENTS)"
echo "========================================"
echo ""

SOURCE="E:/monai-kubeflow-demo/hospital-mlops/demo/sample-data/Task06_Lung/imagesTr"

# Step 1: Create directory in Minikube
echo "[Step 1/3] Creating directory in Minikube..."
minikube ssh "sudo mkdir -p /mnt/data/test_data/Task06_Lung/imagesTr && sudo chmod 777 -R /mnt/data/test_data"
echo "Done!"
echo ""

# Step 2: Copy files
echo "[Step 2/3] Copying 4 patient CT scans..."

declare -A patients=(
    ["$SOURCE/lung_001.nii.gz"]="lung_001.nii.gz"
    ["$SOURCE/lung_003.nii.gz"]="lung_002.nii.gz"
    ["$SOURCE/lung_004.nii.gz"]="lung_003.nii.gz"
    ["$SOURCE/lung_005.nii.gz"]="lung_004.nii.gz"
)

count=1
for src in "${!patients[@]}"; do
    dst="${patients[$src]}"
    echo "  [$count/4] Copying $(basename $src) -> $dst ..."

    # Copy via temp location
    cat "$src" | minikube ssh "sudo tee /mnt/data/test_data/Task06_Lung/imagesTr/$dst > /dev/null"

    echo "       Done!"
    ((count++))
done

echo ""

# Step 3: Verify
echo "[Step 3/3] Verifying files..."
minikube ssh "ls -lh /mnt/data/test_data/Task06_Lung/imagesTr/"
echo ""

echo "========================================"
echo "INPUT DATA READY!"
echo "========================================"
echo ""

echo "Prepared 4 patients:"
echo "  1. lung_001.nii.gz"
echo "  2. lung_002.nii.gz"
echo "  3. lung_003.nii.gz"
echo "  4. lung_004.nii.gz"
echo ""

echo "Next: Build Docker image"
echo "  $ ./BUILD_NOW.sh"
echo ""
