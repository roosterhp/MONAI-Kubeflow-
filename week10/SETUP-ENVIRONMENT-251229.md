# Week 10 CI/CD Demo - Environment Setup Guide

**Date**: 2025-12-29
**Status**: ENVIRONMENT NOT READY - Need manual fixes

## Current Issues Detected

### Issue 1: Docker Desktop Not Running ❌
**Error**: `error during connect: open //./pipe/dockerDesktopLinuxEngine: The system cannot find the file specified`

**Solution**:
1. Mở Docker Desktop application
2. Đợi cho đến khi Docker whale icon ở system tray chuyển sang màu xanh
3. Verify: `docker ps` (should return container list, not error)

### Issue 2: kubectl Context Wrong ❌
**Error**: `Unable to connect to the server: dial tcp: lookup 2E875FF0073BD42B30FA544895513E2E.gr7.us-east-1.eks.amazonaws.com`

kubectl hiện đang point tới AWS EKS cluster thay vì Minikube local.

**Solution**:
```bash
# Xem available contexts
kubectl config get-contexts

# Switch to Minikube context
kubectl config use-context minikube

# Verify
kubectl config current-context
# Should output: minikube
```

---

## Step-by-Step Setup Instructions

### Step 1: Start Docker Desktop

```powershell
# Mở Docker Desktop from Start Menu
# Or run from PowerShell:
# start "C:\Program Files\Docker\Docker\Docker Desktop.exe"

# Wait 30-60 seconds for Docker to start

# Verify Docker running
docker ps
# Should show: CONTAINER ID   IMAGE   COMMAND   CREATED   STATUS   PORTS   NAMES
```

### Step 2: Start Minikube

```bash
# Start Minikube with Docker driver
minikube start --driver=docker --cpus=4 --memory=6144 --disk-size=20g

# This will take 2-5 minutes

# Verify Minikube running
minikube status
# Expected output:
# minikube
# type: Control Plane
# host: Running
# kubelet: Running
# apiserver: Running
# kubeconfig: Configured
```

### Step 3: Switch kubectl Context

```bash
# Set kubectl to use Minikube
kubectl config use-context minikube

# Verify current context
kubectl config current-context
# Output: minikube

# Test connection
kubectl get nodes
# Should show: NAME       STATUS   ROLES           AGE   VERSION
#              minikube   Ready    control-plane   XXm   v1.xx.x
```

### Step 4: Verify ArgoCD Installation

```bash
# Check ArgoCD namespace exists
kubectl get namespace argocd

# If NOT exists, install ArgoCD:
kubectl create namespace argocd
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml

# Wait for all pods to be Running (2-5 minutes)
kubectl get pods -n argocd --watch
# Press Ctrl+C when all pods show STATUS: Running

# Expected: 7 pods total
# - argocd-application-controller
# - argocd-applicationset-controller
# - argocd-dex-server
# - argocd-notifications-controller
# - argocd-redis
# - argocd-repo-server
# - argocd-server
```

### Step 5: Verify Kubeflow Installation

```bash
# Check Kubeflow namespace
kubectl get namespace kubeflow

# If NOT exists, install Kubeflow Pipelines:
export PIPELINE_VERSION="2.0.5"
kubectl apply -k "github.com/kubeflow/pipelines/manifests/kustomize/cluster-scoped-resources?ref=$PIPELINE_VERSION"
kubectl wait --for condition=established --timeout=60s crd/applications.app.k8s.io
kubectl apply -k "github.com/kubeflow/pipelines/manifests/kustomize/env/platform-agnostic?ref=$PIPELINE_VERSION"

# Wait for pods (5-10 minutes)
kubectl get pods -n kubeflow --watch

# Expected key pods:
# - ml-pipeline-xxx (Running)
# - ml-pipeline-ui-xxx (Running)
# - mysql-xxx (Running)
# - minio-xxx (Running)
```

### Step 6: Configure GitHub Secrets

Truy cập: https://github.com/roosterhp/MONAI-Kubeflow-/settings/secrets/actions

**Secret 1: GHCR_TOKEN** (Already configured via GITHUB_TOKEN)
- GitHub Actions automatically has `GITHUB_TOKEN` với packages:write permission
- Không cần config thêm nếu sử dụng GHCR (GitHub Container Registry)

Verify permissions:
1. Settings > Actions > General
2. Scroll to "Workflow permissions"
3. Select: ✅ "Read and write permissions"
4. Click "Save"

### Step 7: Test GitHub Actions Locally (Optional)

```bash
# Install act (GitHub Actions local runner)
# Windows: Download from https://github.com/nektos/act/releases

# Test workflow syntax
cd E:/monai-kubeflow-demo
act -l

# Dry-run docker-build workflow
act push --dry-run -W .github/workflows/docker-build.yml
```

---

## Verification Checklist

Run these commands to verify environment ready:

```bash
# 1. Docker
docker ps
# ✅ Should list containers (may be empty)

# 2. Minikube
minikube status
# ✅ All components: Running

# 3. kubectl context
kubectl config current-context
# ✅ Output: minikube

# 4. Kubernetes connection
kubectl get nodes
# ✅ Should show minikube node Ready

# 5. ArgoCD
kubectl get pods -n argocd
# ✅ All 7 pods STATUS: Running

# 6. Kubeflow
kubectl get pods -n kubeflow | grep -E "(ml-pipeline|mysql|minio)"
# ✅ Key pods Running

# 7. GitHub repo access
cd E:/monai-kubeflow-demo
git status
# ✅ Should show branch status (not error)

# 8. Docker registry login
docker login ghcr.io -u YOUR_GITHUB_USERNAME
# Password: Use GitHub Personal Access Token with packages:write
# ✅ Login Succeeded
```

---

## Quick Start Commands (Copy-Paste Ready)

```bash
# Complete setup in one go (after Docker Desktop started)
cd E:/monai-kubeflow-demo

# Start Minikube
minikube start --driver=docker --cpus=4 --memory=6144

# Switch kubectl context
kubectl config use-context minikube

# Check ArgoCD
kubectl get pods -n argocd

# Check Kubeflow
kubectl get pods -n kubeflow

# If all green, proceed to Phase 1 implementation
bash week10/test-argocd-comprehensive.sh
```

---

## Troubleshooting

### Docker Desktop won't start
- Restart computer
- Check Windows Virtualization enabled: `systeminfo | findstr Hyper-V`
- Check WSL2 installed: `wsl --list --verbose`

### Minikube won't start
```bash
# Delete and recreate
minikube delete
minikube start --driver=docker --cpus=4 --memory=6144
```

### ArgoCD pods CrashLoopBackOff
```bash
# Reinstall ArgoCD
kubectl delete namespace argocd
kubectl create namespace argocd
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml
```

### Kubeflow pods stuck Pending
```bash
# Check node resources
kubectl describe nodes

# May need more memory
minikube stop
minikube start --memory=8192 --cpus=6
```

---

## Next Steps

After environment verified (all checkboxes ✅):

1. Apply ArgoCD projects: `kubectl apply -f week10/argocd-projects.yaml`
2. Run comprehensive test: `bash week10/test-argocd-comprehensive.sh`
3. Proceed to implementation plan: `./plans/251229-cicd-gitops-demo/plan.md`

---

**Last Updated**: 2025-12-29
**Plan**: E:\monai-kubeflow-demo\plans\251229-cicd-gitops-demo\plan.md
