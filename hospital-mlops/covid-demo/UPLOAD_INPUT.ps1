# Upload Input Data to Minikube
# Copy 4 patient CT scans from local input/ folder to Minikube

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "UPLOADING INPUT DATA TO MINIKUBE" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

$inputFolder = "E:\monai-kubeflow-demo\hospital-mlops\covid-demo\input"
$patients = @("lung_001.nii.gz", "lung_002.nii.gz", "lung_003.nii.gz", "lung_004.nii.gz")

# Step 1: Create directory in Minikube
Write-Host "[Step 1/3] Creating directory structure..." -ForegroundColor Yellow
minikube ssh "sudo mkdir -p /mnt/data/test_data/Task06_Lung/imagesTr && sudo chmod 777 -R /mnt/data"
Write-Host "Done!`n" -ForegroundColor Green

# Step 2: Upload files
Write-Host "[Step 2/3] Uploading files..." -ForegroundColor Yellow

$count = 1
foreach ($patient in $patients) {
    $srcFile = Join-Path $inputFolder $patient
    $size = (Get-Item $srcFile).Length / 1MB

    Write-Host "  [$count/4] Uploading $patient ($([math]::Round($size, 1)) MB) ..." -NoNewline

    # Copy via temp, then move to final location
    $tempPath = "/tmp/$patient"
    $finalPath = "/mnt/data/test_data/Task06_Lung/imagesTr/$patient"

    # Use base64 encoding to transfer binary file
    $base64 = [Convert]::ToBase64String([IO.File]::ReadAllBytes($srcFile))
    $base64 | minikube ssh "base64 -d > $tempPath"
    minikube ssh "sudo mv $tempPath $finalPath && sudo chmod 666 $finalPath" 2>$null

    Write-Host " Done!" -ForegroundColor Green
    $count++
}

Write-Host ""

# Step 3: Verify
Write-Host "[Step 3/3] Verifying uploaded files..." -ForegroundColor Yellow
minikube ssh "ls -lh /mnt/data/test_data/Task06_Lung/imagesTr/" | Out-String | Write-Host
Write-Host ""

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "UPLOAD COMPLETE!" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

Write-Host "Files uploaded to Minikube:" -ForegroundColor Yellow
Write-Host "  /mnt/data/test_data/Task06_Lung/imagesTr/"
Write-Host "    - lung_001.nii.gz"
Write-Host "    - lung_002.nii.gz"
Write-Host "    - lung_003.nii.gz"
Write-Host "    - lung_004.nii.gz"
Write-Host ""

Write-Host "Next step: Build Docker image" -ForegroundColor Yellow
Write-Host "  > .\BUILD_NOW.ps1`n"
