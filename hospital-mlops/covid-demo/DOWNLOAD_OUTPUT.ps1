# Download Output from Minikube
# Retrieve result images from pipeline execution

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "DOWNLOADING OUTPUT FROM MINIKUBE" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

$outputFolder = "E:\monai-kubeflow-demo\hospital-mlops\covid-demo\output"
$patients = @("lung_001", "lung_002", "lung_003", "lung_004")

# Create output directory if not exists
if (!(Test-Path $outputFolder)) {
    New-Item -ItemType Directory -Path $outputFolder | Out-Null
}

Write-Host "Downloading results for 4 patients...`n" -ForegroundColor Yellow

$count = 1
$successCount = 0

foreach ($patient in $patients) {
    Write-Host "[$count/4] Patient: $patient" -ForegroundColor Cyan

    # Download visualization image
    $remotePath = "/mnt/data/covid_outputs/week_current/$patient/full_comparison_$patient.png"
    $localPath = Join-Path $outputFolder "full_comparison_$patient.png"

    Write-Host "  Checking for output..." -NoNewline

    # Check if file exists
    $exists = minikube ssh "test -f $remotePath && echo 'yes' || echo 'no'" 2>$null

    if ($exists -match "yes") {
        Write-Host " Found!" -ForegroundColor Green
        Write-Host "  Downloading..." -NoNewline

        # Download file
        minikube ssh "cat $remotePath" | Set-Content -Path $localPath -AsByteStream -Force

        $size = (Get-Item $localPath).Length / 1KB
        Write-Host " Done! ($([math]::Round($size, 1)) KB)" -ForegroundColor Green

        # Also download JSON results
        $jsonPath = "/mnt/data/covid_outputs/week_current/$patient/covid_results.json"
        $localJson = Join-Path $outputFolder "covid_results_$patient.json"

        minikube ssh "cat $jsonPath" 2>$null | Set-Content -Path $localJson -Force

        $successCount++
    } else {
        Write-Host " Not found" -ForegroundColor Red
        Write-Host "  (Pipeline may not have completed yet)" -ForegroundColor Yellow
    }

    Write-Host ""
    $count++
}

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "DOWNLOAD COMPLETE!" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

Write-Host "Downloaded $successCount/$($patients.Count) results to:" -ForegroundColor Yellow
Write-Host "  $outputFolder`n"

if ($successCount -gt 0) {
    Write-Host "Result files:" -ForegroundColor Green
    Get-ChildItem $outputFolder -Filter "*.png" | ForEach-Object {
        $size = $_.Length / 1KB
        Write-Host "  - $($_.Name) ($([math]::Round($size, 1)) KB)"
    }
    Write-Host ""
}

if ($successCount -lt $patients.Count) {
    Write-Host "Some results are missing. Please check:" -ForegroundColor Yellow
    Write-Host "  1. Pipeline has finished running in Kubeflow"
    Write-Host "  2. All pods completed successfully"
    Write-Host "  3. No errors in Kubeflow UI`n"
}
