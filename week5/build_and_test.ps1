# Build and Test Script for Hospital COVID Detection Pipeline (PowerShell)
# This script builds the Docker image and tests the pipeline locally

Write-Host "=== Hospital COVID Detection Pipeline - Build and Test ===" -ForegroundColor Green
Write-Host "Date: $(Get-Date)" -ForegroundColor Cyan
Write-Host "Working Directory: $(Get-Location)" -ForegroundColor Cyan
Write-Host ""

# Configuration
$PIPELINE_NAME = "hospital-covid-complete-pipeline"
$DOCKER_IMAGE = "covid-hospital-pipeline:latest"
$NAMESPACE = "kubeflow"

# Step 1: Check Prerequisites
Write-Host "Step 1: Checking prerequisites..." -ForegroundColor Yellow
Write-Host ""

# Check if Docker is available
try {
    $dockerVersion = docker --version 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✓ Docker found: $dockerVersion" -ForegroundColor Green
    } else {
        throw "Docker not found"
    }
} catch {
    Write-Host "❌ Docker is not installed or not in PATH" -ForegroundColor Red
    exit 1
}

# Check if kubectl is available
try {
    $kubectlVersion = kubectl version --client --short 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✓ kubectl found: $kubectlVersion" -ForegroundColor Green
        $KUBECTL_AVAILABLE = $true
    } else {
        throw "kubectl not found"
    }
} catch {
    Write-Host "⚠️  kubectl is not available - cannot test Kubernetes deployment" -ForegroundColor Yellow
    $KUBECTL_AVAILABLE = $false
}

# Check if Docker daemon is running
try {
    docker info 2>$null | Out-Null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✓ Docker daemon is running" -ForegroundColor Green
    } else {
        throw "Docker daemon not running"
    }
} catch {
    Write-Host "❌ Docker daemon is not running" -ForegroundColor Red
    exit 1
}

Write-Host ""

# Step 2: Build Docker Image
Write-Host "Step 2: Building Docker image..." -ForegroundColor Yellow
Write-Host ""

Write-Host "Building $DOCKER_IMAGE from config/Dockerfile..." -ForegroundColor Cyan
docker build -f config/Dockerfile -t $DOCKER_IMAGE .

if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ Docker image built successfully" -ForegroundColor Green
    docker images | grep covid-hospital-pipeline
} else {
    Write-Host "❌ Docker image build failed" -ForegroundColor Red
    exit 1
}

Write-Host ""

# Step 3: Test Docker Image
Write-Host "Step 3: Testing Docker image..." -ForegroundColor Yellow
Write-Host ""

Write-Host "Running quick container health check..." -ForegroundColor Cyan
docker run --rm $DOCKER_IMAGE python -c "
import sys
try:
    import torch
    import monai
    import numpy as np
    import nibabel as nib
    print('All required packages imported successfully')
    print(f'PyTorch version: {torch.__version__}')
    print(f'MONAI version: {monai.__version__}')
except ImportError as e:
    print(f'Import error: {e}')
    sys.exit(1)
"

if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ Docker image health check passed" -ForegroundColor Green
} else {
    Write-Host "❌ Docker image health check failed" -ForegroundColor Red
    exit 1
}

Write-Host ""

# Step 4: Validate YAML File
Write-Host "Step 4: Validating pipeline YAML..." -ForegroundColor Yellow
Write-Host ""

$yamlValidation = python -c "
import yaml
import sys

try:
    with open('hospital_covid_complete_pipeline.yaml', 'r', encoding='utf-8') as f:
        content = yaml.safe_load(f)

    # Check required fields
    required_fields = ['apiVersion', 'kind', 'metadata', 'spec']
    for field in required_fields:
        if field not in content:
            print(f'Missing required field: {field}')
            sys.exit(1)

    # Check templates
    if 'templates' not in content['spec']:
        print('Missing templates in spec')
        sys.exit(1)

    templates = content['spec']['templates']
    required_templates = ['hospital-covid-pipeline', 'load-data-template', 'process-patient-parallel']

    for template in templates:
        if 'name' in template and template['name'] in required_templates:
            required_templates.remove(template['name'])

    if required_templates:
        print(f'Missing required templates: {required_templates}')
        sys.exit(1)

    print('YAML validation passed')
    print(f'Pipeline: {content[\"metadata\"][\"name\"]}')
    print(f'Namespace: {content[\"metadata\"][\"namespace\"]}')
    print(f'Templates: {len(templates)}')

except Exception as e:
    print(f'YAML validation failed: {e}')
    sys.exit(1)
"

if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ Pipeline YAML validation passed" -ForegroundColor Green
    $yamlValidation
} else {
    Write-Host "❌ Pipeline YAML validation failed" -ForegroundColor Red
    exit 1
}

Write-Host ""

# Step 5: Prepare Test Data
Write-Host "Step 5: Preparing test data..." -ForegroundColor Yellow
Write-Host ""

# Check if test data exists
if (Test-Path "data/weekly_input") {
    $niftiFiles = Get-ChildItem "data/weekly_input/*.nii.gz" -ErrorAction SilentlyContinue
    if ($niftiFiles.Count -gt 0) {
        Write-Host "✓ Test data found in data/weekly_input/" -ForegroundColor Green
        Write-Host "Files found:" -ForegroundColor Cyan
        $niftiFiles | ForEach-Object { Write-Host "  $($_.Name)" }
    } else {
        Write-Host "⚠️  No .nii.gz files found in data/weekly_input/" -ForegroundColor Yellow
    }
} else {
    Write-Host "⚠️  Test data directory not found, creating structure..." -ForegroundColor Yellow
    New-Item -ItemType Directory -Force -Path "data/weekly_input" | Out-Null
    "# Test data placeholder" | Out-File -FilePath "data/weekly_input/README.txt"
    Write-Host "✓ Test data structure created" -ForegroundColor Green
}

Write-Host ""

# Step 6: Kubernetes Test (if available)
if ($KUBECTL_AVAILABLE) {
    Write-Host "Step 6: Testing Kubernetes deployment..." -ForegroundColor Yellow
    Write-Host ""

    # Check if cluster is accessible
    try {
        kubectl cluster-info 2>$null | Out-Null
        if ($LASTEXITCODE -eq 0) {
            Write-Host "✓ Kubernetes cluster is accessible" -ForegroundColor Green

            # Check if namespace exists
            $namespaceExists = kubectl get namespace $NAMESPACE 2>$null
            if ($LASTEXITCODE -eq 0) {
                Write-Host "✓ Namespace '$NAMESPACE' exists" -ForegroundColor Green
            } else {
                Write-Host "⚠️  Namespace '$NAMESPACE' does not exist" -ForegroundColor Yellow
                Write-Host "Creating namespace..." -ForegroundColor Cyan
                kubectl create namespace $NAMESPACE
                Write-Host "✓ Namespace '$NAMESPACE' created" -ForegroundColor Green
            }

            # Test if we can create the workflow (dry-run)
            Write-Host "Testing workflow creation (dry-run)..." -ForegroundColor Cyan
            kubectl apply -f hospital_covid_complete_pipeline.yaml --dry-run=client -n $NAMESPACE
            if ($LASTEXITCODE -eq 0) {
                Write-Host "✓ Workflow can be created successfully" -ForegroundColor Green
            } else {
                Write-Host "❌ Workflow creation failed" -ForegroundColor Red
            }
        } else {
            throw "Cluster not accessible"
        }
    } catch {
        Write-Host "⚠️  Kubernetes cluster is not accessible" -ForegroundColor Yellow
    }
} else {
    Write-Host "Step 6: Skipping Kubernetes test (kubectl not available)" -ForegroundColor Yellow
}

Write-Host ""

# Step 7: Summary
Write-Host "=== Build and Test Summary ===" -ForegroundColor Green
Write-Host ""
Write-Host "✓ Docker image built: $DOCKER_IMAGE" -ForegroundColor Green
Write-Host "✓ YAML validated: hospital_covid_complete_pipeline.yaml" -ForegroundColor Green

if (Test-Path "components") {
    $pyFiles = Get-ChildItem "components/*.py" -ErrorAction SilentlyContinue
    Write-Host "✓ Components available: $($pyFiles.Count) Python files" -ForegroundColor Green
}

Write-Host ""

if ($KUBECTL_AVAILABLE -and (kubectl cluster-info 2>$null)) {
    Write-Host "✓ Kubernetes cluster ready" -ForegroundColor Green
    Write-Host ""
    Write-Host "Next steps:" -ForegroundColor Cyan
    Write-Host "1. Deploy to Kubernetes:" -ForegroundColor White
    Write-Host "   kubectl apply -f hospital_covid_complete_pipeline.yaml -n $NAMESPACE" -ForegroundColor Gray
    Write-Host ""
    Write-Host "2. Or upload to Kubeflow UI:" -ForegroundColor White
    Write-Host "   - Open Kubeflow UI" -ForegroundColor Gray
    Write-Host "   - Upload hospital_covid_complete_pipeline.yaml" -ForegroundColor Gray
    Write-Host "   - Configure pipeline parameters:" -ForegroundColor Gray
    Write-Host "     * input-dir: /mnt/data/weekly_input" -ForegroundColor Gray
    Write-Host "     * output-dir: /mnt/data/hospital_output" -ForegroundColor Gray
    Write-Host "   - Run pipeline" -ForegroundColor Gray
} else {
    Write-Host "⚠️  Kubernetes not configured" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Next steps:" -ForegroundColor Cyan
    Write-Host "1. Set up Kubernetes cluster (Minikube, GKE, etc.)" -ForegroundColor White
    Write-Host "2. Install Kubeflow Pipelines" -ForegroundColor White
    Write-Host "3. Run this script again to test deployment" -ForegroundColor White
}

Write-Host ""
Write-Host "=== Build and Test Complete ===" -ForegroundColor Green