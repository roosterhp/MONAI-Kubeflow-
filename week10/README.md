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

## 📦 ArgoCD Installation Guide

### Prerequisites

Trước khi cài đặt ArgoCD, đảm bảo bạn có:
- Kubernetes cluster đang chạy (Minikube, kind, hoặc production cluster)
- `kubectl` đã cài đặt và configured
- Quyền admin trên cluster

### Bước 1: Cài đặt ArgoCD

Có 2 cách cài đặt ArgoCD: **kubectl apply** (nhanh) hoặc **Helm** (production, highly available). Chọn một trong hai:

#### Option 1: Kubectl Apply (Recommended cho Dev/Test)

**1.1. Tạo namespace cho ArgoCD:**
```bash
kubectl create namespace argocd
```

**1.2. Cài đặt ArgoCD (sử dụng manifest chính thức):**
```bash
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml
```

**1.3. Đợi tất cả pods sẵn sàng (3-5 phút):**
```bash
# Watch pods cho đến khi tất cả Running
kubectl get pods -n argocd --watch

# Hoặc check một lần
kubectl get pods -n argocd
```

**Expected output:**
```
NAME                                  READY   STATUS    RESTARTS   AGE
argocd-application-controller-0       1/1     Running   0          2m
argocd-applicationset-controller-x    1/1     Running   0          2m
argocd-dex-server-x                   1/1     Running   0          2m
argocd-notifications-controller-x     1/1     Running   0          2m
argocd-redis-x                        1/1     Running   0          2m
argocd-repo-server-x                  1/1     Running   0          2m
argocd-server-x                       1/1     Running   0          2m
```

#### Option 2: Helm Install (Recommended cho Production)

**1.1. Add Argo Helm repository:**
```bash
helm repo add argo https://argoproj.github.io/argo-helm
helm repo update
```

**1.2. Tạo values file cho High Availability (optional):**

Tạo file mới hoặc dùng file reference có sẵn tại `week10/argocd-values.yaml`:

```bash
cat > argocd-values.yaml <<EOF
# High Availability Configuration
redis:
  enabled: true

controller:
  replicas: 2
  args:
    statusProcessors: "50"
    operationProcessors: "25"

repoServer:
  replicas: 2

server:
  replicas: 2
  service:
    type: ClusterIP  # Hoặc LoadBalancer nếu có cloud provider

# Enable metrics
metrics:
  enabled: true

# Notifications
notifications:
  enabled: true
EOF
```

**1.3. Install ArgoCD với Helm:**
```bash
# Cài đặt với HA configuration
helm install argocd argo/argo-cd \
  -n argocd \
  --create-namespace \
  -f argocd-values.yaml

# Hoặc install đơn giản (single replica)
helm install argocd argo/argo-cd \
  -n argocd \
  --create-namespace
```

**1.4. Verify installation:**
```bash
# Check Helm release
helm list -n argocd

# Check pods
kubectl get pods -n argocd
```

**Expected output (HA setup):**
```
NAME                                  READY   STATUS    RESTARTS   AGE
argocd-application-controller-0       1/1     Running   0          2m
argocd-application-controller-1       1/1     Running   0          2m
argocd-applicationset-controller-x    1/1     Running   0          2m
argocd-dex-server-x                   1/1     Running   0          2m
argocd-notifications-controller-x     1/1     Running   0          2m
argocd-redis-x                        1/1     Running   0          2m
argocd-repo-server-0                  1/1     Running   0          2m
argocd-repo-server-1                  1/1     Running   0          2m
argocd-server-0                       1/1     Running   0          2m
argocd-server-1                       1/1     Running   0          2m
```

### Bước 2: Truy cập ArgoCD UI

**2.1. Port forward ArgoCD server:**
```bash
# Mở terminal riêng và giữ command này chạy
kubectl port-forward svc/argocd-server -n argocd 8080:443
```

**2.2. Lấy admin password:**
```bash
# Get password
kubectl get secret argocd-initial-admin-secret -n argocd -o jsonpath="{.data.password}" | base64 -d && echo

# Lưu password này lại!
```

**2.3. Login vào UI:**
```bash
# Mở browser
open https://localhost:8080

# Hoặc nếu dùng Linux
xdg-open https://localhost:8080
```

**Credentials:**
- **Username**: `admin`
- **Password**: (password từ bước 2.2)

**Lưu ý:** Browser có thể cảnh báo về certificate không hợp lệ, chọn "Proceed" hoặc "Advanced → Accept the Risk".

### Bước 3: Cấu hình Projects

**3.1. Tạo AppProjects (ml-pipelines và infrastructure):**
```bash
kubectl apply -f /root/MONAI-Kubeflow-/argocd-apps/appprojects.yaml
```

**3.2. Verify projects được tạo:**
```bash
kubectl get appproject -n argocd
```

**Expected output:**
```
NAME              AGE
infrastructure    10s
ml-pipelines      10s
```

### Bước 4: Deploy Applications

**4.1. Deploy app-of-apps (master application):**
```bash
kubectl apply -f /root/MONAI-Kubeflow-/argocd-apps/app-of-apps.yaml
```

**4.2. Đợi child applications được tạo tự động (30-60 giây):**
```bash
kubectl get applications.argoproj.io -n argocd --watch
```

**Expected output:**
```
NAME                       SYNC STATUS   HEALTH STATUS
covid-detection-pipeline   Synced        Healthy
infrastructure-mysql       Synced        Healthy
monai-kubeflow-master      Synced        Healthy
scaling-hpa                Synced        Healthy
```

### Bước 5: Verify Deployment

**5.1. Check tất cả applications đã sync:**
```bash
kubectl get applications.argoproj.io -n argocd
```

**5.2. Verify resources trong kubeflow namespace:**
```bash
# Check MySQL StatefulSet
kubectl get statefulset mysql-statefulset -n kubeflow

# Check HPA resources
kubectl get hpa -n kubeflow
```

**5.3. Check trong ArgoCD UI:**
- Vào https://localhost:8080
- Bạn sẽ thấy 4 applications
- Tất cả phải có status "Synced" và "Healthy"

### Troubleshooting Common Issues

#### Issue 1: Kustomize Deprecated Syntax Errors

**Error:**
```
Error: no matches for Id StatefulSet.v1.apps/mysql-statefulset.[noNs]
Warning: 'bases' is deprecated. Please use 'resources' instead.
```

**Fix:**
```bash
# Update kustomization.yaml files
# Replace 'bases' → 'resources'
# Replace 'commonLabels' → 'labels'
# Replace 'patchesStrategicMerge' → 'patches'

# Example fix in manifests/infrastructure/overlays/prod/kustomization.yaml:
resources:
  - ../../base

patches:
  - path: mysql-replicas-patch.yaml
    target:
      kind: StatefulSet
      name: mysql-statefulset

labels:
  - pairs:
      environment: production
```

#### Issue 2: Repository Permission Error

**Error:**
```
InvalidSpecError: application repo https://github.com/OLD-REPO/MONAI-Kubeflow-.git
is not permitted in project 'ml-pipelines'
```

**Root cause:** Application YAML files có repo URL cũ không match với AppProject whitelist.

**Fix:**
```bash
# 1. Update all application YAMLs với repo đúng
# argocd-apps/*.yaml phải có:
source:
  repoURL: https://github.com/roosterhp/MONAI-Kubeflow-.git

# 2. Commit và push
git add argocd-apps/*.yaml
git commit -m "fix: Update repo URLs"
git push origin main

# 3. Delete và recreate applications
kubectl delete application.argoproj.io --all -n argocd
kubectl apply -f argocd-apps/app-of-apps.yaml

# 4. Verify
kubectl get applications.argoproj.io -n argocd
```

#### Issue 3: PersistentVolume Immutable Field Error

**Error:**
```
PersistentVolume "mysql-statefulset-pv" is invalid:
nodeAffinity: Invalid value: field is immutable
```

**Fix:**
```bash
# Remove PV from kustomization (PVs already exist and bound)
# manifests/infrastructure/base/kustomization.yaml:
resources:
  - mysql-secret.yaml
  - mysql-statefulset.yaml
  # Removed: - mysql-pvc.yaml

# StatefulSet volumeClaimTemplates will handle storage
```

#### Issue 4: App-of-apps Self-Management Loop

**Error:** `monai-kubeflow-master` status stuck at "Unknown".

**Fix:**
```bash
# Create .argocdignore to exclude app-of-apps.yaml
# argocd-apps/.argocdignore:
app-of-apps.yaml

# This prevents circular dependency
```

#### Issue 5: ArgoCD Controller Not Syncing

**Symptoms:** Applications stuck at "Unknown" status.

**Fix:**
```bash
# Restart ArgoCD application controller
kubectl rollout restart statefulset argocd-application-controller -n argocd

# Wait for rollout to complete
kubectl rollout status statefulset argocd-application-controller -n argocd

# Verify
kubectl get applications.argoproj.io -n argocd
```

### Verification Checklist

Sau khi cài đặt, verify các items sau:

- [ ] **ArgoCD Pods**: Tất cả 7-8 pods ở trạng thái Running
- [ ] **ArgoCD UI**: Có thể truy cập qua https://localhost:8080
- [ ] **AppProjects**: ml-pipelines và infrastructure projects tồn tại
- [ ] **Applications**: 4 apps (master + 3 child apps) đều Synced + Healthy
- [ ] **Kubeflow Resources**: MySQL StatefulSet, HPAs đang chạy
- [ ] **Repository URLs**: Tất cả apps dùng repo đúng (không có NT114 hay repo cũ)

### ArgoCD CLI (Optional)

**Cài đặt ArgoCD CLI:**
```bash
# Linux
curl -sSL -o argocd-linux-amd64 https://github.com/argoproj/argo-cd/releases/latest/download/argocd-linux-amd64
sudo install -m 555 argocd-linux-amd64 /usr/local/bin/argocd
rm argocd-linux-amd64

# Mac
brew install argocd
```

**Login qua CLI:**
```bash
# Login (sử dụng password từ bước 2.2)
argocd login localhost:8080

# List applications
argocd app list

# Sync specific app
argocd app sync infrastructure-mysql

# Get app details
argocd app get infrastructure-mysql
```

### Uninstall ArgoCD (Nếu cần)

**Nếu cài bằng kubectl apply:**
```bash
# Delete all applications first
kubectl delete applications.argoproj.io --all -n argocd

# Delete ArgoCD
kubectl delete -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml

# Delete namespace
kubectl delete namespace argocd
```

**Nếu cài bằng Helm:**
```bash
# Delete all applications first
kubectl delete applications.argoproj.io --all -n argocd

# Uninstall Helm release
helm uninstall argocd -n argocd

# Delete namespace
kubectl delete namespace argocd

# Cleanup any PVCs (if using persistent storage)
kubectl delete pvc --all -n argocd
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

**Last Updated**: 2026-01-05
**Version**: v1.1.0 (Added ArgoCD Installation Guide)
