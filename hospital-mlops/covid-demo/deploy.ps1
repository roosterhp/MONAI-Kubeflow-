# Quick deploy script for COVID-19 Detection Pipeline (Windows PowerShell)

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Deploying COVID-19 Detection Pipeline" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan

# Step 1: Apply Kubernetes resources
Write-Host "`n[Step 1/2] Deploying Kubernetes resources..." -ForegroundColor Yellow
kubectl apply -f kubernetes/pv.yaml
kubectl apply -f kubernetes/pvc.yaml
Write-Host "✓ PV and PVC deployed" -ForegroundColor Green

# Step 2: Verify PVC is bound
Write-Host "`n[Step 2/2] Verifying PVC status..." -ForegroundColor Yellow
kubectl get pvc -n kubeflow | Select-String "covid-data-pvc"
Write-Host "✓ PVC status checked" -ForegroundColor Green

Write-Host "`n==========================================" -ForegroundColor Cyan
Write-Host "Deployment complete!" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan

Write-Host "`nNext steps:" -ForegroundColor Yellow
Write-Host "1. Upload covid_pipeline.yaml to Kubeflow UI"
Write-Host "2. Create a new experiment in Kubeflow"
Write-Host "3. Create a run and monitor progress"
Write-Host ""
Write-Host "Pipeline outputs will be in:" -ForegroundColor Yellow
Write-Host "  /mnt/data/covid_outputs/week_current/{patient_id}/"
Write-Host "  - covid_results.json"
Write-Host "  - features.json"
Write-Host "  - full_comparison_{patient_id}.png"
Write-Host ""
