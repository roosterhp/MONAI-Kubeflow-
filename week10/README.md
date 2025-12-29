# Week 10: CI/CD & GitOps

## 🎯 Mục tiêu

Triển khai **CI/CD automation** và **GitOps** cho ML pipelines:
- ✅ **GitHub Actions**: Auto-build, test, security scan
- ✅ **ArgoCD**: GitOps continuous deployment
- ✅ **Docker Registry**: Auto-push images to GHCR
- ✅ **Release Management**: Automated versioning

---

## 📦 Kết quả đạt được

### CI/CD Pipelines (GitHub Actions)

| Workflow | Status | Mô tả |
|----------|--------|-------|
| Pipeline CI Tests | ✅ PASS | Lint, test, validation |
| Docker Build & Push | ✅ PASS | Auto-build và push images |
| Security Scan | ✅ PASS | Trivy vulnerability scan |
| Create Release | ✅ PASS | Auto-generate releases |

### GitOps Deployment (ArgoCD)

| Component | Status | Details |
|-----------|--------|---------|
| ArgoCD Server | ✅ Running | 7/7 pods healthy |
| Auto-sync | ✅ Enabled | Sync from GitHub |
| Applications | ✅ Deployed | simple-test app |

### Docker Images

```
ghcr.io/roosterhp/monai-kubeflow/demo-app:latest   # Latest build
ghcr.io/roosterhp/monai-kubeflow/demo-app:v1.0.1   # Release tags
ghcr.io/roosterhp/monai-kubeflow/demo-app:SHA      # Commit SHA
```

---

## 🗂️ Cấu trúc

```
week10/
├── README.md              # File này
├── argocd/               # ArgoCD configurations
│   ├── argocd-projects.yaml
│   └── simple-test-app.yaml
└── scripts/              # Automation scripts
    ├── create-release.sh
    └── test-argocd-comprehensive.sh
```

---

## 🚀 Quick Start

### 1. Kiểm tra GitHub Actions

**Xem workflows đang chạy:**
```bash
# Web UI
open https://github.com/roosterhp/MONAI-Kubeflow-/actions

# CLI (nếu đã cài gh)
gh run list --limit 5
```

**Workflows tự động trigger khi:**
- Push to `main` branch → Build & test
- Create tag `v*.*.*` → Build & release
- Pull request → Build test only (no push)

### 2. ArgoCD GitOps

**Check ArgoCD status:**
```bash
# Pods
kubectl get pods -n argocd

# Applications
kubectl get applications.argoproj.io -n argocd

# Deploy new app
kubectl apply -f argocd/simple-test-app.yaml
```

**Access ArgoCD UI:**
```bash
# Port forward
kubectl port-forward svc/argocd-server -n argocd 8080:443

# Open browser
open https://localhost:8080

# Get password
kubectl get secret argocd-initial-admin-secret -n argocd -o jsonpath="{.data.password}" | base64 -d
```

### 3. Tạo Release mới

**Sử dụng script:**
```bash
# Tạo release v1.0.2
./scripts/create-release.sh v1.0.2
```

**Manual:**
```bash
# Tạo và push tag
git tag -a v1.0.2 -m "Release v1.0.2"
git push origin v1.0.2

# GitHub Actions sẽ tự:
# 1. Build Docker image
# 2. Push to GHCR với tag v1.0.2
# 3. Create GitHub Release
# 4. Generate changelog
```

### 4. Pull Docker Images

```bash
# Latest version
docker pull ghcr.io/roosterhp/monai-kubeflow/demo-app:latest

# Specific version
docker pull ghcr.io/roosterhp/monai-kubeflow/demo-app:v1.0.1

# Run container
docker run --rm ghcr.io/roosterhp/monai-kubeflow/demo-app:latest
```

---

## 🔧 Workflows Configuration

### Pipeline CI Tests (`.github/workflows/pipeline-test.yml`)

**Triggers:** Push to main, Pull requests

**Jobs:**
- **lint**: Code quality checks
- **test**: Run tests
- **compile-pipeline**: Validate pipeline structure

**Runtime:** ~30 seconds

### Docker Build (`.github/workflows/docker-build.yml`)

**Triggers:** Push to main, tags `v*.*.*`, Pull requests

**Jobs:**
- **build-and-push** (main): Build + push to GHCR
- **build** (PR): Build only, no push

**Tags generated:**
- `latest` (main branch)
- `v1.0.1` (release tags)
- `SHA` (commit hash)

**Runtime:** ~2-3 minutes (first build), ~30s (cached)

### Security Scan (`.github/workflows/security-scan.yml`)

**Triggers:** Push to main, Weekly (Monday 6am UTC), Manual

**Jobs:**
- Build image
- Run Trivy scanner
- Upload SARIF to GitHub Security
- Generate vulnerability report

**Runtime:** ~1-2 minutes

### Create Release (`.github/workflows/release.yml`)

**Triggers:** Tags `v*.*.*`, Manual dispatch

**Jobs:**
- Generate changelog from git commits
- Create GitHub Release
- Link Docker images

**Runtime:** ~10 seconds

---

## 📊 Demo Flow (10 phút)

### Demo 1: CI/CD Automation

```bash
# 1. Make a change
echo "# Demo $(date)" >> README.md

# 2. Commit and push
git add .
git commit -m "demo: Test CI/CD automation"
git push origin main

# 3. Watch workflows
open https://github.com/roosterhp/MONAI-Kubeflow-/actions
```

**Expected:**
- ✅ All 3 workflows trigger
- ✅ Complete in ~3 minutes
- ✅ Docker image pushed to GHCR

### Demo 2: GitOps Auto-sync

```bash
# 1. Update manifest
vim manifests/base/namespace.yaml

# 2. Commit and push
git add .
git commit -m "update: Namespace config"
git push origin main

# 3. Watch ArgoCD auto-sync
kubectl get applications.argoproj.io -n argocd --watch
```

**Expected:**
- ✅ ArgoCD detects change
- ✅ Auto-sync within 3 minutes
- ✅ Status: Synced + Healthy

### Demo 3: Release Creation

```bash
# 1. Create release
./scripts/create-release.sh v1.0.2

# 2. Watch workflows
open https://github.com/roosterhp/MONAI-Kubeflow-/actions

# 3. Check release
open https://github.com/roosterhp/MONAI-Kubeflow-/releases
```

**Expected:**
- ✅ Tag created: v1.0.2
- ✅ Docker image: demo-app:v1.0.2
- ✅ GitHub Release with changelog

---

## 🔍 Troubleshooting

### GitHub Actions không chạy?

```bash
# Check workflows
gh run list --limit 5

# View logs
gh run view <run-id> --log

# Re-run failed workflow
gh run rerun <run-id>
```

### Docker build fails?

```bash
# Test build locally
cd demo-app
docker build -t test:local .

# Check workflow logs
# Look for: invalid reference format, permission denied, etc.
```

### ArgoCD không sync?

```bash
# Restart ArgoCD
kubectl delete pods --all -n argocd

# Re-apply application
kubectl apply -f argocd/simple-test-app.yaml

# Force sync
kubectl patch application simple-test -n argocd --type merge -p '{"operation":{"sync":{}}}'
```

### Cannot access ArgoCD UI?

```bash
# Check pods
kubectl get pods -n argocd

# Port forward
kubectl port-forward svc/argocd-server -n argocd 8080:443

# Get admin password
kubectl get secret argocd-initial-admin-secret -n argocd -o jsonpath="{.data.password}" | base64 -d
```

---

## 📚 Học thêm

### GitHub Actions
- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Docker Build Action](https://github.com/docker/build-push-action)
- [Trivy Security Scanner](https://github.com/aquasecurity/trivy-action)

### ArgoCD
- [ArgoCD Documentation](https://argo-cd.readthedocs.io/)
- [GitOps Principles](https://opengitops.dev/)
- [Kubernetes GitOps](https://www.weave.works/technologies/gitops/)

### Docker Registry
- [GitHub Container Registry](https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry)
- [Docker Image Best Practices](https://docs.docker.com/develop/dev-best-practices/)

---

## ✅ Status Summary

| Component | Status | Notes |
|-----------|--------|-------|
| GitHub Actions | ✅ Working | All workflows passing |
| Docker Build | ✅ Working | Auto-push to GHCR |
| Security Scan | ✅ Working | Weekly + on-demand |
| ArgoCD | ✅ Running | Auto-sync enabled |
| Releases | ✅ Automated | Tag-based workflow |

**Week 10**: ✅ **COMPLETE**
**Demo Ready**: ✅ **YES**

---

**Last Updated**: 2025-12-29
**Version**: v1.0.1
