# Week 10: CI/CD & GitOps Demo

## Mục tiêu
Deploy CI/CD automation với GitHub Actions và GitOps với ArgoCD.

## Kết quả

### ✅ GitHub Actions CI/CD
- **Lint & Test**: Kiểm tra code quality, run tests
- **Docker Build**: Auto-build và push images khi commit
- **Security Scan**: Quét vulnerabilities với Trivy

### ✅ GitOps với ArgoCD
- ArgoCD auto-sync từ GitHub repository
- Deploy kubernetes manifests tự động
- Application status: Synced + Healthy

## Cấu trúc

```
week10/
├── README.md                    # File này
├── argocd/                      # ArgoCD configs
│   ├── argocd-projects.yaml
│   └── simple-test-app.yaml
└── scripts/                     # Test scripts
    └── test-argocd-comprehensive.sh
```

## Quick Start

### 1. Check GitHub Actions
```bash
# Xem workflows
open https://github.com/NT114DevSecOpsProject/MONAI-Kubeflow-/actions
```

### 2. Check ArgoCD
```bash
# ArgoCD pods
kubectl get pods -n argocd

# ArgoCD applications
kubectl get applications.argoproj.io -n argocd

# Deploy app
kubectl apply -f argocd/simple-test-app.yaml
```

## Status

| Component | Status |
|-----------|--------|
| GitHub Actions | ✅ CI/CD automated |
| Docker Build | ✅ Auto-push to GHCR |
| ArgoCD | ✅ Auto-sync enabled |
| Security Scan | ✅ Weekly scanning |

---

**Week 10**: ✅ Complete | **Demo**: ✅ Ready
