# Week 10 CI/CD & GitOps - Script Demo Nhanh

**Thời gian demo**: 10-15 phút
**Mục tiêu**: Chứng minh CI/CD tự động cho ML pipeline

---

## Chuẩn bị trước demo (5 phút)

### 1. Khởi động môi trường

```bash
# Terminal 1: Start Docker Desktop (manual)
# Mở Docker Desktop app, đợi icon xanh

# Terminal 2: Start services
cd E:/monai-kubeflow-demo
minikube start --driver=docker --cpus=4 --memory=6144
kubectl config use-context minikube

# Verify all running
kubectl get pods -n argocd
kubectl get pods -n kubeflow
```

### 2. Port-forward các UI

```bash
# Terminal 3: ArgoCD UI
kubectl port-forward -n argocd svc/argocd-server 8080:443

# Terminal 4: Kubeflow UI
kubectl port-forward -n kubeflow svc/ml-pipeline-ui 8081:80
```

### 3. Lấy ArgoCD password

```bash
kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}" | base64 -d
# Copy password này
```

---

## Demo Flow (10 phút)

### Part 1: Giới thiệu kiến trúc (2 phút)

**Mở PowerPoint/Slides** với diagram:

```
Developer → GitHub → GitHub Actions → Docker Image → GHCR
                ↓
            ArgoCD ← Git manifests
                ↓
            Kubernetes (Minikube)
                ↓
            Kubeflow Pipeline (ML Workload)
```

**Giải thích**:
- Developer push code → Tự động build Docker image
- ArgoCD theo dõi Git repository → Tự động deploy vào Kubernetes
- Kubeflow chạy ML pipeline với image mới nhất
- Rollback = đổi Git tag (v1.0.0 ↔ v0.9.0)

### Part 2: Show GitHub Actions (2 phút)

**Browser Tab 1**: https://github.com/roosterhp/MONAI-Kubeflow-/actions

1. Click vào workflow run gần nhất
2. Show 3 jobs:
   - ✅ **Build and Push Docker Image** (~5 phút)
   - ✅ **Pipeline CI Tests** (~2 phút)
   - ✅ **Security Scan** (~3 phút)

3. Click vào "Build and Push Docker Image"
   - Show steps: Checkout → Build → Push to GHCR
   - Show image tags: `latest`, `main-abc1234`, `v1.0.0`

**Key point**: "Mỗi lần push code, hệ thống tự động build image mới trong 5 phút"

### Part 3: Show ArgoCD UI (2 phút)

**Browser Tab 2**: https://localhost:8080

Login:
- Username: `admin`
- Password: (đã copy ở bước chuẩn bị)

1. Show 4 applications:
   - `monai-kubeflow-master` (App-of-apps)
   - `infrastructure-mysql` (Database)
   - `scaling-hpa` (Autoscaling)
   - `covid-detection-pipeline` (ML Pipeline)

2. Click vào `covid-detection-pipeline`:
   - Show **Sync Status**: Synced
   - Show **Health Status**: Healthy
   - Show **Target Revision**: v1.0.0 (Git tag)

3. Click "App Details":
   - Show **Repo URL**: https://github.com/roosterhp/MONAI-Kubeflow-
   - Show **Path**: manifests/pipelines/covid-detection/versions/v1.0.0

**Key point**: "ArgoCD tự động sync từ Git. Git = source of truth"

### Part 4: Demo tự động build khi push code (3 phút)

**Terminal window**:

```bash
cd E:/monai-kubeflow-demo

# 1. Make a small code change
echo "# CI/CD test $(date +%Y%m%d-%H%M%S)" >> hospital-mlops/covid-demo/README.md

# 2. Commit and push
git add .
git commit -m "test: Demo CI/CD auto-build"
git push origin main

# 3. Show GitHub Actions triggered
echo "Open: https://github.com/roosterhp/MONAI-Kubeflow-/actions"
```

**Trong GitHub Actions**:
- Refresh page → New workflow run appeared!
- Click vào run → Show "in progress"

**Giải thích**:
"Chỉ cần push code, sau 5 phút sẽ có Docker image mới.
ArgoCD sẽ tự động phát hiện image mới và deploy."

### Part 5: Demo rollback (1 phút)

**ArgoCD UI**:

```bash
# Method 1: Qua UI
# 1. Click vào covid-detection-pipeline app
# 2. Click "App Details"
# 3. Sửa "Target Revision" từ v1.0.0 → v0.9.0
# 4. Click "Sync"
# → Hệ thống rollback về version cũ trong 30 giây

# Method 2: Qua CLI
kubectl patch application covid-detection-pipeline -n argocd \
  --type merge \
  -p '{"spec":{"source":{"targetRevision":"v0.9.0"}}}'

# Sync
kubectl get applications -n argocd covid-detection-pipeline
```

**Show kết quả**:
- ArgoCD UI: Target Revision = v0.9.0
- Status: Synced (màu xanh)

**Key point**: "Rollback = đổi Git tag. Không cần rebuild image"

---

## Screenshots cần chuẩn bị (cho slides)

### 1. GitHub Actions Workflow
- File: `screenshots/01-github-actions-workflows.png`
- Capture: List of 3 workflows (docker-build, pipeline-test, security-scan)

### 2. GitHub Actions Build Success
- File: `screenshots/02-docker-build-success.png`
- Capture: Green checkmark với steps completed

### 3. GitHub Container Registry
- File: `screenshots/03-ghcr-image-tags.png`
- Capture: https://github.com/roosterhp/MONAI-Kubeflow-/pkgs/container/monai-kubeflow-%2Fcovid-pipeline
- Show: Multiple tags (latest, v1.0.0, main-xxx)

### 4. ArgoCD Applications Dashboard
- File: `screenshots/04-argocd-dashboard.png`
- Capture: 4 apps all Synced + Healthy

### 5. ArgoCD Application Details
- File: `screenshots/05-argocd-app-details.png`
- Capture: covid-detection-pipeline với Git repo info

### 6. ArgoCD Sync History
- File: `screenshots/06-argocd-sync-history.png`
- Capture: History tab showing multiple syncs

### 7. Kubernetes Resources
- File: `screenshots/07-kubernetes-pods.png`
```bash
kubectl get pods -n kubeflow -o wide > screenshots/07-pods-list.txt
```

### 8. Kubeflow Pipeline UI
- File: `screenshots/08-kubeflow-pipeline.png`
- Capture: http://localhost:8081 → Pipelines page

---

## Metrics để collect (cho report)

### Build Metrics
```bash
# Lấy từ GitHub Actions run logs
- Build time: ~5 phút
- Image size: ~1.2 GB (multi-stage optimized)
- Cache hit rate: ~80% (after first build)
```

### Deployment Metrics
```bash
# Time từ code push → deployed
- GitHub Actions: 5 phút
- ArgoCD sync: 30 giây - 2 phút
- Total: ~7 phút từ push code → production

# Rollback time
- Change Git tag: 5 giây
- ArgoCD sync: 30 giây
- Total: <1 phút
```

### Resource Usage
```bash
kubectl top nodes
kubectl top pods -n kubeflow
# Capture vào screenshots/09-resource-usage.txt
```

---

## Q&A Preparation

### Q: "Có test tự động không?"
**A**: Có 3 levels:
1. GitHub Actions: Lint + unit tests
2. Integration test: `tests/integration/test_cicd_flow.sh`
3. E2E test: Manual verification trong Kubeflow UI

### Q: "Build time 5 phút có nhanh không?"
**A**:
- First build: 10-15 phút (download base images)
- Subsequent builds: 5 phút (với layer caching)
- Production có thể optimize thêm với pre-built base images

### Q: "GitOps khác gì traditional CI/CD?"
**A**:
- Traditional: Jenkins push to production
- GitOps: Git = source of truth, ArgoCD pull from Git
- Benefit: Audit trail, easy rollback, disaster recovery

### Q: "Có support multi-environment không (dev/staging/prod)?"
**A**: Có, dùng Kustomize overlays:
```
manifests/
  base/           # Common configs
  overlays/
    dev/          # Dev-specific (1 replica)
    prod/         # Prod-specific (3 replicas, more memory)
```

### Q: "Security scanning bắt được gì?"
**A**: Trivy scan for:
- OS vulnerabilities (CVEs)
- Python package vulnerabilities
- Dockerfile best practices
- Exposed secrets

---

## Backup Plan (nếu live demo fail)

### Plan A: Show pre-recorded video
- Record demo trước 1 ngày
- Prepare video file: `demo-recording.mp4`

### Plan B: Show screenshots only
- Prepare full screenshot deck
- Walk through từng screenshot

### Plan C: Show logs/outputs
```bash
# Pre-save command outputs
kubectl get pods -n argocd > outputs/argocd-pods.txt
kubectl get pods -n kubeflow > outputs/kubeflow-pods.txt
kubectl get applications -n argocd > outputs/argocd-apps.txt

# Show pre-saved outputs nếu live commands fail
```

---

## Post-Demo Deliverables

### 1. Demo Report (Vietnamese)
File: `week10/DEMO-RESULTS-VN.md`

Sections:
- Tổng quan demo
- Screenshots với captions
- Metrics collected
- Lessons learned
- Next steps

### 2. Technical Documentation
File: `docs/runbooks/cicd-workflow-guide.md`

Content:
- Architecture diagram
- Step-by-step workflow
- Troubleshooting guide
- Rollback procedures

### 3. Presentation Slides
File: `week10/Week10-CICD-GitOps-Presentation.pptx`

Slides:
1. Title: "ML CI/CD với GitHub Actions + ArgoCD"
2. Architecture Overview
3. Demo: Auto-build on code push
4. Demo: GitOps deployment
5. Demo: Rollback capability
6. Metrics & Results
7. Q&A

---

**Created**: 2025-12-29
**For**: Week 10 CI/CD & GitOps Demo
**Estimated demo time**: 10-15 phút
**Preparation time**: 30 phút
