#!/bin/bash

# Build and Test Script for Hospital COVID Detection Pipeline
# This script builds the Docker image and tests the pipeline locally

set -e

echo "=== Hospital COVID Detection Pipeline - Build and Test ==="
echo "Date: $(date)"
echo "Working Directory: $(pwd)"
echo

# Configuration
PIPELINE_NAME="hospital-covid-complete-pipeline"
DOCKER_IMAGE="covid-hospital-pipeline:latest"
NAMESPACE="kubeflow"

# Step 1: Check Prerequisites
echo "Step 1: Checking prerequisites..."
echo

# Check if Docker is available
if ! command -v docker &> /dev/null; then
    echo "Error: Docker is not installed or not in PATH"
    exit 1
fi

# Check if kubectl is available
if ! command -v kubectl &> /dev/null; then
    echo "Warning: kubectl is not available - cannot test Kubernetes deployment"
    KUBECTL_AVAILABLE=false
else
    KUBECTL_AVAILABLE=true
    echo "kubectl found: $(kubectl version --client --short 2>/dev/null || kubectl version --client)"
fi

# Check if Docker daemon is running
if ! docker info &> /dev/null; then
    echo "Error: Docker daemon is not running"
    exit 1
fi

echo "✓ Prerequisites checked"
echo

# Step 2: Build Docker Image
echo "Step 2: Building Docker image..."
echo

echo "Building $DOCKER_IMAGE from config/Dockerfile..."
docker build -f config/Dockerfile -t $DOCKER_IMAGE .

if [ $? -eq 0 ]; then
    echo "✓ Docker image built successfully"
    docker images | grep covid-hospital-pipeline
else
    echo "❌ Docker image build failed"
    exit 1
fi

echo

# Step 3: Test Docker Image
echo "Step 3: Testing Docker image..."
echo

echo "Running quick container health check..."
docker run --rm $DOCKER_IMAGE python -c "
import sys
try:
    import torch
    import monai
    import numpy as np
    import nibabel as nib
    print('✓ All required packages imported successfully')
    print(f'PyTorch version: {torch.__version__}')
    print(f'MONAI version: {monai.__version__}')
except ImportError as e:
    print(f'❌ Import error: {e}')
    sys.exit(1)
"

if [ $? -eq 0 ]; then
    echo "✓ Docker image health check passed"
else
    echo "❌ Docker image health check failed"
    exit 1
fi

echo

# Step 4: Validate YAML File
echo "Step 4: Validating pipeline YAML..."
echo

python -c "
import yaml
import sys

try:
    with open('hospital_covid_complete_pipeline.yaml', 'r', encoding='utf-8') as f:
        content = yaml.safe_load(f)

    # Check required fields
    required_fields = ['apiVersion', 'kind', 'metadata', 'spec']
    for field in required_fields:
        if field not in content:
            print(f'❌ Missing required field: {field}')
            sys.exit(1)

    # Check templates
    if 'templates' not in content['spec']:
        print('❌ Missing templates in spec')
        sys.exit(1)

    templates = content['spec']['templates']
    required_templates = ['hospital-covid-pipeline', 'load-data-template', 'process-patient-parallel']

    for template in templates:
        if 'name' in template and template['name'] in required_templates:
            required_templates.remove(template['name'])

    if required_templates:
        print(f'❌ Missing required templates: {required_templates}')
        sys.exit(1)

    print('✓ YAML validation passed')
    print(f'✓ Pipeline: {content[\"metadata\"][\"name\"]}')
    print(f'✓ Namespace: {content[\"metadata\"][\"namespace\"]}')
    print(f'✓ Templates: {len(templates)}')

except Exception as e:
    print(f'❌ YAML validation failed: {e}')
    sys.exit(1)
"

if [ $? -eq 0 ]; then
    echo "✓ Pipeline YAML validation passed"
else
    echo "❌ Pipeline YAML validation failed"
    exit 1
fi

echo

# Step 5: Prepare Test Data
echo "Step 5: Preparing test data..."
echo

# Check if test data exists
if [ -d "data/weekly_input" ] && [ "$(ls -A data/weekly_input/*.nii.gz 2>/dev/null | wc -l)" -gt 0 ]; then
    echo "✓ Test data found in data/weekly_input/"
    echo "Files found:"
    ls -la data/weekly_input/*.nii.gz 2>/dev/null || echo "No .nii.gz files found"
else
    echo "⚠️  No test data found in data/weekly_input/"
    echo "Creating test data structure..."
    mkdir -p data/weekly_input
    echo "# Test data placeholder" > data/weekly_input/README.txt
    echo "✓ Test data structure created"
fi

echo

# Step 6: Kubernetes Test (if available)
if [ "$KUBECTL_AVAILABLE" = true ]; then
    echo "Step 6: Testing Kubernetes deployment..."
    echo

    # Check if cluster is accessible
    if kubectl cluster-info &> /dev/null; then
        echo "✓ Kubernetes cluster is accessible"

        # Check if namespace exists
        if kubectl get namespace $NAMESPACE &> /dev/null; then
            echo "✓ Namespace '$NAMESPACE' exists"
        else
            echo "⚠️  Namespace '$NAMESPACE' does not exist"
            echo "Creating namespace..."
            kubectl create namespace $NAMESPACE
            echo "✓ Namespace '$NAMESPACE' created"
        fi

        # Test if we can create the workflow (dry-run)
        echo "Testing workflow creation (dry-run)..."
        if kubectl apply -f hospital_covid_complete_pipeline.yaml --dry-run=client -n $NAMESPACE; then
            echo "✓ Workflow can be created successfully"
        else
            echo "❌ Workflow creation failed"
        fi
    else
        echo "⚠️  Kubernetes cluster is not accessible"
    fi
else
    echo "Step 6: Skipping Kubernetes test (kubectl not available)"
fi

echo

# Step 7: Summary
echo "=== Build and Test Summary ==="
echo
echo "✓ Docker image built: $DOCKER_IMAGE"
echo "✓ YAML validated: hospital_covid_complete_pipeline.yaml"
echo "✓ Components available:"
ls -la components/ 2>/dev/null | grep -E '\.(py)$' | wc -l | xargs echo "  - Python files:"
echo

if [ "$KUBECTL_AVAILABLE" = true ] && kubectl cluster-info &> /dev/null; then
    echo "✓ Kubernetes cluster ready"
    echo
    echo "Next steps:"
    echo "1. Deploy to Kubernetes:"
    echo "   kubectl apply -f hospital_covid_complete_pipeline.yaml -n $NAMESPACE"
    echo
    echo "2. Or upload to Kubeflow UI:"
    echo "   - Open Kubeflow UI"
    echo "   - Upload hospital_covid_complete_pipeline.yaml"
    echo "   - Configure pipeline parameters:"
    echo "     * input-dir: /mnt/data/weekly_input"
    echo "     * output-dir: /mnt/data/hospital_output"
    echo "   - Run pipeline"
else
    echo "⚠️  Kubernetes not configured"
    echo
    echo "Next steps:"
    echo "1. Set up Kubernetes cluster (Minikube, GKE, etc.)"
    echo "2. Install Kubeflow Pipelines"
    echo "3. Run this script again to test deployment"
fi

echo
echo "=== Build and Test Complete ==="