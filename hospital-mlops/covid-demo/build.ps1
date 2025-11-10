# Build script for COVID-19 Detection Pipeline (Windows PowerShell)

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Building COVID-19 Detection Pipeline" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan

# Step 1: Set Minikube Docker environment
Write-Host "`n[Step 1/4] Setting Minikube Docker environment..." -ForegroundColor Yellow
& minikube docker-env | Invoke-Expression
Write-Host "✓ Using Minikube Docker daemon" -ForegroundColor Green

# Step 2: Build Docker image
Write-Host "`n[Step 2/4] Building Docker image..." -ForegroundColor Yellow
docker build -t covid-pipeline:v1 .
if ($LASTEXITCODE -ne 0) {
    Write-Host "✗ Docker build failed!" -ForegroundColor Red
    exit 1
}
Write-Host "✓ Image built: covid-pipeline:v1" -ForegroundColor Green

# Step 3: Verify image
Write-Host "`n[Step 3/4] Verifying image..." -ForegroundColor Yellow
docker images | Select-String "covid-pipeline"
Write-Host "✓ Image verified" -ForegroundColor Green

# Step 4: Compile pipeline
Write-Host "`n[Step 4/4] Compiling Kubeflow pipeline..." -ForegroundColor Yellow
python pipeline.py
if ($LASTEXITCODE -ne 0) {
    Write-Host "✗ Pipeline compilation failed!" -ForegroundColor Red
    exit 1
}
Write-Host "✓ Pipeline compiled: covid_pipeline.yaml" -ForegroundColor Green

Write-Host "`n==========================================" -ForegroundColor Cyan
Write-Host "Build complete!" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan

Write-Host "`nNext steps:" -ForegroundColor Yellow
Write-Host "1. kubectl apply -f kubernetes/pv.yaml"
Write-Host "2. kubectl apply -f kubernetes/pvc.yaml"
Write-Host "3. Upload covid_pipeline.yaml to Kubeflow UI"
Write-Host ""
