# Access ArgoCD UI Script
# Opens port-forward and displays login credentials

Write-Host "=== ArgoCD UI Access ===" -ForegroundColor Green

# Get admin password
Write-Host "`nRetrieving admin password..." -ForegroundColor Cyan
$password = kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}" 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Could not retrieve password. Is ArgoCD installed?" -ForegroundColor Red
    exit 1
}

$decodedPassword = [System.Text.Encoding]::UTF8.GetString([System.Convert]::FromBase64String($password))

Write-Host "`n=== Login Credentials ===" -ForegroundColor Yellow
Write-Host "URL: https://localhost:8080" -ForegroundColor White
Write-Host "Username: admin" -ForegroundColor White
Write-Host "Password: $decodedPassword" -ForegroundColor White

Write-Host "`n⚠️  Password copied to clipboard!" -ForegroundColor Green
Set-Clipboard -Value $decodedPassword

Write-Host "`nStarting port-forward (keep this terminal open)..." -ForegroundColor Cyan
Write-Host "Press Ctrl+C to stop port-forward`n" -ForegroundColor Gray

kubectl port-forward svc/argocd-server -n argocd 8080:443
