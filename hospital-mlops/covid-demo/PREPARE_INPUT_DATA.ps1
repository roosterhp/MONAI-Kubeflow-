# Prepare Input Data for COVID-19 Pipeline
# Copy 4 patient CT scans to Minikube

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "PREPARING INPUT DATA (4 PATIENTS)" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

$source = "E:\monai-kubeflow-demo\hospital-mlops\demo\sample-data\Task06_Lung\imagesTr"
$patients = @(
    @{src="lung_001.nii.gz"; dst="lung_001.nii.gz"},
    @{src="lung_003.nii.gz"; dst="lung_002.nii.gz"},
    @{src="lung_004.nii.gz"; dst="lung_003.nii.gz"},
    @{src="lung_005.nii.gz"; dst="lung_004.nii.gz"}
)

# Step 1: Create directory in Minikube
Write-Host "[Step 1/3] Creating directory in Minikube..." -ForegroundColor Yellow
minikube ssh "sudo mkdir -p /mnt/data/test_data/Task06_Lung/imagesTr && sudo chmod 777 -R /mnt/data/test_data"
Write-Host "Done!`n" -ForegroundColor Green

# Step 2: Copy files
Write-Host "[Step 2/3] Copying 4 patient CT scans..." -ForegroundColor Yellow

$count = 1
foreach ($patient in $patients) {
    $srcFile = Join-Path $source $patient.src
    $dstName = $patient.dst

    Write-Host "  [$count/4] Copying $($patient.src) -> $dstName ..." -NoNewline

    # Create temp file in Minikube
    $tempPath = "/tmp/$dstName"
    $finalPath = "/mnt/data/test_data/Task06_Lung/imagesTr/$dstName"

    # Copy to temp then move (workaround for Windows path issue)
    Get-Content $srcFile -Raw -AsByteStream | minikube ssh "cat > $tempPath"
    minikube ssh "sudo mv $tempPath $finalPath && sudo chmod 666 $finalPath"

    Write-Host " Done!" -ForegroundColor Green
    $count++
}

Write-Host ""

# Step 3: Verify
Write-Host "[Step 3/3] Verifying files..." -ForegroundColor Yellow
minikube ssh "ls -lh /mnt/data/test_data/Task06_Lung/imagesTr/"
Write-Host ""

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "INPUT DATA READY!" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

Write-Host "Prepared 4 patients:" -ForegroundColor Yellow
Write-Host "  1. lung_001.nii.gz"
Write-Host "  2. lung_002.nii.gz"
Write-Host "  3. lung_003.nii.gz"
Write-Host "  4. lung_004.nii.gz"
Write-Host ""

Write-Host "Next: Build Docker image" -ForegroundColor Yellow
Write-Host "  > .\BUILD_NOW.ps1`n"
