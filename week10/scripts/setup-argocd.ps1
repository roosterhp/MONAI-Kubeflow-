# ArgoCD Setup Script for Windows PowerShell
# Week 10: CI/CD for ML with GitOps

Write-Host "=== ArgoCD Setup Script ===" -ForegroundColor Green

# Step 1: Check prerequisites
Write-Host "`n[1/7] Checking prerequisites..." -ForegroundColor Cyan
$minikubeStatus = minikube status 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Minikube not running. Please start Minikube first." -ForegroundColor Red
    exit 1
}
Write-Host "✅ Minikube running" -ForegroundColor Green

# Step 2: Create ArgoCD namespace
Write-Host "`n[2/7] Creating ArgoCD namespace..." -ForegroundColor Cyan
kubectl create namespace argocd --dry-run=client -o yaml | kubectl apply -f -
Write-Host "✅ Namespace created" -ForegroundColor Green

# Step 3: Install ArgoCD
Write-Host "`n[3/7] Installing ArgoCD (this may take 2-3 minutes)..." -ForegroundColor Cyan
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml

# Step 4: Wait for pods to be ready
Write-Host "`n[4/7] Waiting for ArgoCD pods to be ready (timeout: 10 minutes)..." -ForegroundColor Cyan
kubectl wait --for=condition=ready pod --all -n argocd --timeout=600s
Write-Host "✅ All pods ready" -ForegroundColor Green

# Step 5: Get admin password
Write-Host "`n[5/7] Retrieving admin password..." -ForegroundColor Cyan
$password = kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}"
$decodedPassword = [System.Text.Encoding]::UTF8.GetString([System.Convert]::FromBase64String($password))
Write-Host "✅ Admin password retrieved" -ForegroundColor Green

# Step 6: Create projects
Write-Host "`n[6/7] Creating ArgoCD projects..." -ForegroundColor Cyan
kubectl apply -f week10/argocd-projects.yaml
Write-Host "✅ Projects created" -ForegroundColor Green

# Step 7: Display access info
Write-Host "`n[7/7] Setup complete!" -ForegroundColor Green
Write-Host "`n=== ArgoCD Access Information ===" -ForegroundColor Yellow
Write-Host "URL: https://localhost:8080" -ForegroundColor White
Write-Host "Username: admin" -ForegroundColor White
Write-Host "Password: $decodedPassword" -ForegroundColor White
Write-Host "`n⚠️  To access the UI, run in a separate terminal:" -ForegroundColor Yellow
Write-Host "kubectl port-forward svc/argocd-server -n argocd 8080:443" -ForegroundColor Cyan
Write-Host "`nPress Ctrl+C to exit port-forward when done.`n" -ForegroundColor Gray
