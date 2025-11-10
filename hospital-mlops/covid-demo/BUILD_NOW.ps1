# Quick build script - Build Docker image in Minikube

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "BUILDING DOCKER IMAGE IN MINIKUBE" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

Write-Host "NOTE: This will take 5-10 minutes on first build" -ForegroundColor Yellow
Write-Host "      Installing PyTorch, MONAI, LungMask, etc.`n" -ForegroundColor Yellow

# Set Minikube Docker environment
Write-Host "[1/4] Setting Minikube Docker environment..." -ForegroundColor Yellow
& minikube docker-env | Invoke-Expression
Write-Host "Done!`n" -ForegroundColor Green

# Show Dockerfile info
Write-Host "[2/4] Dockerfile info..." -ForegroundColor Yellow
Write-Host "  Base image: python:3.10-slim"
Write-Host "  Packages: PyTorch (CPU), MONAI, LungMask, SimpleITK"
Write-Host "  Components: 5 pipeline stages`n"

# Build Docker image
Write-Host "[3/4] Building Docker image..." -ForegroundColor Yellow
Write-Host "  (This may take several minutes...)`n" -ForegroundColor Yellow

$startTime = Get-Date
docker build -t covid-pipeline:v1 . --progress=plain

$buildTime = ((Get-Date) - $startTime).TotalSeconds

if ($LASTEXITCODE -eq 0) {
    Write-Host "`nBuild completed in $([math]::Round($buildTime, 1)) seconds!`n" -ForegroundColor Green
} else {
    Write-Host "`nBuild failed!`n" -ForegroundColor Red
    Write-Host "Common issues:" -ForegroundColor Yellow
    Write-Host "  1. Network timeout - Try again"
    Write-Host "  2. Docker memory - Increase Docker memory limit"
    Write-Host "  3. Minikube not running - Run 'minikube start'`n"
    exit 1
}

# Verify image
Write-Host "[4/4] Verifying image..." -ForegroundColor Yellow
docker images | Select-String "covid-pipeline"
Write-Host ""

# Get image size
$imageSize = docker images covid-pipeline:v1 --format "{{.Size}}"
Write-Host "  Image size: $imageSize" -ForegroundColor Cyan

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "BUILD COMPLETE!" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

Write-Host "Image ready: covid-pipeline:v1" -ForegroundColor Green
Write-Host "Build time: $([math]::Round($buildTime, 1)) seconds`n" -ForegroundColor Green

Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "1. If pipeline already running in Kubeflow:"
Write-Host "   - Delete the failed run"
Write-Host "   - Create a NEW run"
Write-Host ""
Write-Host "2. If not yet started:"
Write-Host "   - Upload covid_pipeline.yaml to Kubeflow UI"
Write-Host "   - Create and start run`n"
