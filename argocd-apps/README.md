# ArgoCD Applications

Thư mục này chứa các ArgoCD Application definitions cho GitOps deployment của MONAI Kubeflow project.

---

## 🎯 Mục đích

Folder `argocd-apps/` định nghĩa tất cả các applications được quản lý bởi ArgoCD theo **App of Apps pattern**:
- **Parent App** (app-of-apps.yaml): Quản lý tất cả child applications
- **Child Apps**: Tự động được tạo và sync bởi parent app
- **Projects**: Phân quyền và whitelist repositories

---

## 📁 Cấu trúc File

```
argocd-apps/
├── README.md                    # File này
├── .argocdignore               # Ngăn app-of-apps tự quản lý chính nó
├── appprojects.yaml            # ArgoCD Projects (ml-pipelines, infrastructure)
├── app-of-apps.yaml            # Parent application (app-of-apps pattern)
├── covid-pipeline-app.yaml     # COVID detection pipeline application
├── infrastructure-app.yaml     # Infrastructure (MySQL) application
└── scaling-app.yaml            # HPA scaling application
```

---

## 📋 Chi tiết từng File

### 1. `app-of-apps.yaml` - Parent Application

**Mục đích:** Application chính quản lý tất cả child applications theo App of Apps pattern.

**Nội dung:**
```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: monai-kubeflow-master
  namespace: argocd
spec:
  project: ml-pipelines
  source:
    repoURL: https://github.com/roosterhp/MONAI-Kubeflow-.git
    targetRevision: main
    path: argocd-apps  # Sync tất cả files trong folder này
  destination:
    server: https://kubernetes.default.svc
    namespace: argocd
  syncPolicy:
    automated:
      prune: false  # Không tự động xóa apps
      selfHeal: true
```

**Hoạt động:**
1. ArgoCD sync `argocd-apps/` folder từ Git
2. Phát hiện các `*-app.yaml` files
3. Tự động tạo child applications
4. Sync và monitor chúng

**Lưu ý:**
- `.argocdignore` ngăn app này tự quản lý chính nó (circular dependency)
- `prune: false` để tránh xóa nhầm applications

### 2. `appprojects.yaml` - Projects Definition

**Mục đích:** Định nghĩa ArgoCD Projects để phân quyền và whitelist repositories.

**Projects:**

#### **ml-pipelines Project**
```yaml
sourceRepos:
  - 'https://github.com/roosterhp/MONAI-Kubeflow-.git'
destinations:
  - namespace: 'kubeflow'
    server: 'https://kubernetes.default.svc'
  - namespace: 'argocd'
    server: 'https://kubernetes.default.svc'
```

**Chức năng:**
- Chỉ cho phép sync từ repo `roosterhp/MONAI-Kubeflow-`
- Deploy vào namespaces: `kubeflow`, `argocd`
- Dùng cho: covid-pipeline, app-of-apps

#### **infrastructure Project**
```yaml
sourceRepos:
  - 'https://github.com/roosterhp/MONAI-Kubeflow-.git'
destinations:
  - namespace: 'kubeflow'
  - namespace: 'default'
```

**Chức năng:**
- Deploy infrastructure resources (MySQL, HPA)
- Namespaces: `kubeflow`, `default`

### 3. `.argocdignore` - Ignore File

**Mục đích:** Ngăn ArgoCD sync file `app-of-apps.yaml` khi parent app sync folder này.

**Nội dung:**
```
# Ignore app-of-apps.yaml to prevent self-management circular dependency
app-of-apps.yaml
```

**Tại sao cần:**
- App-of-apps sync folder `argocd-apps/`
- Nếu không ignore, nó sẽ cố tạo lại chính nó → circular dependency
- Dẫn đến status "Unknown" hoặc sync loop

### 4. `covid-pipeline-app.yaml` - COVID Pipeline

**Mục đích:** Deploy COVID-19 detection pipeline.

**Manifest:**
```yaml
metadata:
  name: covid-detection-pipeline
  labels:
    pipeline: covid-detection
    version: v1.0.0
spec:
  project: ml-pipelines
  source:
    repoURL: https://github.com/roosterhp/MONAI-Kubeflow-.git
    targetRevision: v1.0.0  # Git tag
    path: manifests/pipelines/covid-detection/versions/v1.0.0
  destination:
    namespace: kubeflow
  syncPolicy:
    automated:
      prune: true
      selfHeal: false  # Manual sync for production pipelines
```

**Đặc điểm:**
- Deploy từ **git tag** (`v1.0.0`) để đảm bảo versioning
- `selfHeal: false` để pipeline không tự động rollback
- Sync vào namespace `kubeflow`

### 5. `infrastructure-app.yaml` - MySQL Infrastructure

**Mục đích:** Deploy MySQL StatefulSet cho Kubeflow metadata storage.

**Manifest:**
```yaml
metadata:
  name: infrastructure-mysql
  labels:
    component: infrastructure
    week: week6
spec:
  project: infrastructure
  source:
    path: manifests/infrastructure/overlays/prod
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
    retry:
      limit: 5
      backoff:
        duration: 5s
        factor: 2
        maxDuration: 3m
```

**Resources deployed:**
- MySQL StatefulSet (3 replicas HA)
- MySQL Secret (credentials)
- Headless Service
- PVCs (via volumeClaimTemplates)

**Đặc điểm:**
- `selfHeal: true` để tự động fix drift
- Retry logic với backoff
- Kustomize overlays: `base` + `prod`

### 6. `scaling-app.yaml` - HPA Autoscaling

**Mục đích:** Deploy HorizontalPodAutoscalers cho Kubeflow components.

**Manifest:**
```yaml
metadata:
  name: scaling-hpa
  labels:
    component: scaling
    week: week7
spec:
  project: infrastructure
  source:
    path: manifests/scaling/overlays/prod
  syncPolicy:
    automated:
      prune: true
      selfHeal: false  # HPA quản lý replicas
  ignoreDifferences:
    - group: apps
      kind: Deployment
      jsonPointers:
        - /spec/replicas  # Ignore HPA-managed replicas
```

**Resources deployed:**
- `ml-pipeline-hpa` (2-10 replicas, CPU 70%)
- `workflow-controller-hpa` (2-8 replicas, CPU 70%, Memory 80%)
- 5 HPAs khác cho Kubeflow services

**Đặc điểm:**
- `ignoreDifferences` để không conflict với HPA
- HPA tự động scale based on metrics
- `selfHeal: false` để không override HPA decisions

---

## 🚀 Usage Guide

### Deploy Applications

**Bước 1: Apply Projects (chỉ cần 1 lần)**
```bash
kubectl apply -f argocd-apps/appprojects.yaml

# Verify
kubectl get appproject -n argocd
```

**Bước 2: Deploy App-of-Apps**
```bash
kubectl apply -f argocd-apps/app-of-apps.yaml

# Wait for child apps to be created
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

### Update Applications

**Để update một application:**

1. **Sửa file YAML trong folder này**
   ```bash
   vim argocd-apps/infrastructure-app.yaml
   ```

2. **Commit và push lên Git**
   ```bash
   git add argocd-apps/infrastructure-app.yaml
   git commit -m "update: Infrastructure app configuration"
   git push origin main
   ```

3. **ArgoCD tự động sync** (nếu có `automated.selfHeal: true`)
   ```bash
   # Hoặc manual sync
   kubectl patch application infrastructure-mysql -n argocd \
     --type merge -p '{"operation":{"sync":{}}}'
   ```

### Thêm Application Mới

**Tạo file mới theo template:**

```bash
cat > argocd-apps/my-new-app.yaml <<EOF
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: my-new-app
  namespace: argocd
  labels:
    component: my-component
spec:
  project: infrastructure  # hoặc ml-pipelines
  source:
    repoURL: https://github.com/roosterhp/MONAI-Kubeflow-.git
    targetRevision: main
    path: manifests/my-component/overlays/prod
  destination:
    server: https://kubernetes.default.svc
    namespace: kubeflow
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
    syncOptions:
      - CreateNamespace=true
EOF

# Commit và push
git add argocd-apps/my-new-app.yaml
git commit -m "feat: Add my-new-app application"
git push origin main

# App-of-apps sẽ tự động phát hiện và tạo app mới
```

---

## 🔍 Troubleshooting

### Issue 1: Application Status "Unknown"

**Symptoms:**
```
NAME                    SYNC STATUS   HEALTH STATUS
monai-kubeflow-master   Unknown       Unknown
```

**Root cause:** App-of-apps tự quản lý chính nó (missing `.argocdignore`)

**Fix:**
```bash
# Verify .argocdignore exists
cat argocd-apps/.argocdignore
# Should contain: app-of-apps.yaml

# Refresh app
kubectl annotate application monai-kubeflow-master -n argocd \
  argocd.argoproj.io/refresh=hard --overwrite
```

### Issue 2: InvalidSpecError - Repository Not Permitted

**Error:**
```
InvalidSpecError: application repo https://github.com/OLD-REPO/...
is not permitted in project 'ml-pipelines'
```

**Root cause:** Repo URL trong application YAML không match với AppProject whitelist.

**Fix:**
```bash
# 1. Check AppProject sourceRepos
kubectl get appproject ml-pipelines -n argocd -o yaml | grep -A 5 sourceRepos

# 2. Update application YAML với repo đúng
# Tất cả *-app.yaml phải có:
source:
  repoURL: https://github.com/roosterhp/MONAI-Kubeflow-.git

# 3. Commit, push, recreate
git add argocd-apps/*.yaml
git commit -m "fix: Update repo URLs"
git push origin main

kubectl delete application.argoproj.io --all -n argocd
kubectl apply -f argocd-apps/app-of-apps.yaml
```

### Issue 3: Child Apps Not Created

**Symptoms:** Chỉ có `monai-kubeflow-master`, không có child apps.

**Possible causes:**
1. `.argocdignore` đang ignore tất cả files
2. Sync chưa hoàn thành
3. YAML syntax errors

**Fix:**
```bash
# Check .argocdignore (chỉ nên ignore app-of-apps.yaml)
cat argocd-apps/.argocdignore

# Check app-of-apps status
kubectl get application monai-kubeflow-master -n argocd -o yaml

# Check managed resources
kubectl get application monai-kubeflow-master -n argocd \
  -o jsonpath='{.status.resources[*].name}'

# Force sync
kubectl patch application monai-kubeflow-master -n argocd \
  --type merge -p '{"operation":{"sync":{}}}'
```

### Issue 4: Sync Fails - Kustomize Errors

**Error:**
```
Error: no matches for Id StatefulSet.v1.apps/mysql-statefulset.[noNs]
Warning: 'bases' is deprecated
```

**Fix:** Update manifests (xem `manifests/README.md` để biết chi tiết)

---

## 📊 Application Status Reference

### Sync Status

| Status | Meaning | Action |
|--------|---------|--------|
| **Synced** | ✅ Git == Cluster | No action needed |
| **OutOfSync** | ⚠️ Git ≠ Cluster | ArgoCD sẽ auto-sync hoặc manual sync |
| **Unknown** | ❓ Không thể determine | Check conditions, refresh app |

### Health Status

| Status | Meaning | Example |
|--------|---------|---------|
| **Healthy** | ✅ All resources healthy | Pods Running, Services ready |
| **Progressing** | 🔄 Deploying | Pods Creating, Rolling update |
| **Degraded** | ⚠️ Some issues | Pods CrashLoopBackOff |
| **Missing** | ❌ Resource not found | Deployment deleted |
| **Unknown** | ❓ Cannot determine | Custom resources |

---

## 📚 Best Practices

### 1. Git Workflow

**Mọi changes phải qua Git:**
```bash
# ❌ KHÔNG SỬA trực tiếp trong cluster
kubectl edit application infrastructure-mysql -n argocd

# ✅ SỬA trong Git
vim argocd-apps/infrastructure-app.yaml
git add . && git commit -m "update: ..." && git push
```

### 2. Application Naming

**Đặt tên rõ ràng, có prefix:**
- `infrastructure-mysql` (component-service)
- `scaling-hpa` (component-purpose)
- `covid-detection-pipeline` (project-type)

### 3. Labels và Annotations

**Luôn thêm labels để dễ quản lý:**
```yaml
metadata:
  labels:
    component: infrastructure
    week: week6
    team: ml-ops
    environment: production
```

### 4. Sync Policies

**Chọn sync policy phù hợp:**

- **Production databases**: `selfHeal: true`, `prune: true`
- **ML pipelines**: `selfHeal: false`, `prune: true` (manual approval)
- **HPA-managed**: `selfHeal: false`, `ignoreDifferences` for replicas

### 5. Security

**Bảo mật repository access:**
```yaml
# AppProject với repo whitelist
sourceRepos:
  - 'https://github.com/roosterhp/MONAI-Kubeflow-.git'  # Chỉ repo này

# KHÔNG dùng wildcard trong production
# sourceRepos:
#   - '*'  # ❌ KHÔNG AN TOÀN
```

---

## ✅ Verification Checklist

Sau khi deploy, verify:

- [ ] **AppProjects**: 2 projects (ml-pipelines, infrastructure) tồn tại
- [ ] **App-of-Apps**: monai-kubeflow-master Synced + Healthy
- [ ] **Child Apps**: 3 apps (covid, infrastructure, scaling) Synced + Healthy
- [ ] **Resources**: MySQL StatefulSet, HPAs đang chạy trong kubeflow namespace
- [ ] **Repo URLs**: Tất cả apps dùng repo `roosterhp` (không phải NT114)
- [ ] **.argocdignore**: File tồn tại và chỉ ignore `app-of-apps.yaml`

---

## 📖 Related Documentation

- **ArgoCD Installation**: `week10/README.md`
- **Manifests Structure**: `manifests/README.md`
- **Kustomize Troubleshooting**: `week10/README.md` → Troubleshooting section
- **ArgoCD Official Docs**: https://argo-cd.readthedocs.io/

---

**Last Updated**: 2026-01-05
**Version**: 1.0.0
