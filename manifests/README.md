# Kubernetes Manifests

Thư mục này chứa tất cả Kubernetes manifest files được quản lý bởi ArgoCD theo GitOps workflow.

---

## 🎯 Mục đích

Folder `manifests/` chứa các Kubernetes resource definitions cho:
- **Infrastructure**: MySQL database, storage
- **Scaling**: HorizontalPodAutoscalers (HPA)
- **Pipelines**: ML pipeline configurations
- **Base**: Shared resources (namespaces, storage classes)

Tất cả manifests sử dụng **Kustomize** để manage configurations cho nhiều environments.

---

## 📁 Cấu trúc

```
manifests/
├── README.md                           # File này
├── base/                              # Shared base resources
│   ├── namespace.yaml                 # Kubeflow namespace
│   └── storage-class.yaml             # Storage class definitions
├── infrastructure/                    # Infrastructure components
│   ├── base/                         # Base MySQL configuration
│   │   ├── kustomization.yaml
│   │   ├── mysql-secret.yaml         # Database credentials
│   │   ├── mysql-pvc.yaml            # PersistentVolume (reference only)
│   │   └── mysql-statefulset.yaml    # MySQL StatefulSet
│   └── overlays/
│       └── prod/                     # Production overrides
│           ├── kustomization.yaml
│           └── mysql-replicas-patch.yaml  # 3 replicas for HA
├── scaling/                           # Autoscaling configurations
│   ├── base/
│   │   ├── kustomization.yaml
│   │   └── kubeflow-hpa.yaml         # HPA definitions
│   └── overlays/
│       └── prod/
│           ├── kustomization.yaml
│           └── hpa-thresholds-patch.yaml  # Production thresholds
└── pipelines/                         # ML pipeline manifests
    └── covid-detection/
        └── versions/
            └── v1.0.0/               # Versioned pipeline configs
```

---

## 📦 Components Detail

### 1. Base Resources (`base/`)

**Shared resources cho tất cả components.**

#### `namespace.yaml`
```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: kubeflow
  labels:
    name: kubeflow
    environment: production
```

**Mục đích:**
- Tạo namespace `kubeflow` cho tất cả ML workloads
- Isolate resources khỏi default namespace

#### `storage-class.yaml`
```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: kubeflow-storage
provisioner: kubernetes.io/no-provisioner
volumeBindingMode: WaitForFirstConsumer
```

**Mục đích:**
- StorageClass cho local storage (hostPath)
- `WaitForFirstConsumer`: PV binding chờ pod được scheduled

---

### 2. Infrastructure (`infrastructure/`)

**MySQL database infrastructure cho Kubeflow metadata storage.**

#### Base Configuration (`infrastructure/base/`)

**File: `kustomization.yaml`**
```yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization

namespace: kubeflow

resources:
  - mysql-secret.yaml
  - mysql-statefulset.yaml
  # NOT including mysql-pvc.yaml (PVs already exist)

labels:
  - pairs:
      app: mysql
      component: infrastructure
      version: week6
```

**Lưu ý quan trọng:**
- ❌ KHÔNG include `mysql-pvc.yaml` trong resources
- ✅ PersistentVolumes đã tồn tại trong cluster
- ✅ StatefulSet `volumeClaimTemplates` sẽ tự động tạo PVCs

**File: `mysql-secret.yaml`**
```yaml
apiVersion: v1
kind: Secret
metadata:
  name: mysql-secret
stringData:
  root-password: kubeflow123
  database: kubeflow_db
  user: kubeflow
  password: kubeflow123
```

**Chứa:**
- MySQL root password
- Database name
- Application user credentials

**File: `mysql-statefulset.yaml`**

**Deployed resources:**
- **Headless Service** (`mysql-headless`): Cho StatefulSet DNS
- **Regular Service** (`mysql-statefulset-service`): Cho applications
- **StatefulSet** (`mysql-statefulset`): MySQL pods

**StatefulSet spec:**
```yaml
spec:
  serviceName: mysql-headless
  replicas: 1  # Base: single replica (prod overlay = 3)
  volumeClaimTemplates:
    - metadata:
        name: data
      spec:
        accessModes: ["ReadWriteOnce"]
        storageClassName: kubeflow-storage
        resources:
          requests:
            storage: 20Gi
```

**Resources:**
- CPU: 1-2 cores
- Memory: 2-4 Gi
- Storage: 20Gi per replica

**Probes:**
- **Liveness**: `mysqladmin ping` every 10s
- **Readiness**: `mysqladmin ping` every 5s

#### Production Overlay (`infrastructure/overlays/prod/`)

**File: `kustomization.yaml`**
```yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization

namespace: kubeflow

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

**Features:**
- Extends base configuration
- Patches replicas to 3 for HA
- Adds production labels

**File: `mysql-replicas-patch.yaml`**
```yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: mysql-statefulset
  namespace: kubeflow
spec:
  replicas: 3  # Production: 3 replicas for HA
```

**High Availability:**
- 3 replicas cho fault tolerance
- Mỗi replica có PVC riêng (20Gi each)
- Total storage: 60Gi

---

### 3. Scaling (`scaling/`)

**HorizontalPodAutoscalers cho Kubeflow components.**

#### Base Configuration (`scaling/base/`)

**File: `kustomization.yaml`**
```yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization

namespace: kubeflow

resources:
  - kubeflow-hpa.yaml

labels:
  - pairs:
      component: scaling
      version: week7
```

**File: `kubeflow-hpa.yaml`**

**Deployed HPAs (7 autoscalers):**

1. **ml-pipeline-hpa**
   - Target: `ml-pipeline` deployment
   - Min/Max: 2-10 replicas
   - Metrics: CPU 70%, Memory 80%
   - Scale up: 50% every 15s (max 2 pods)
   - Scale down: 50% every 60s (5min stabilization)

2. **workflow-controller-hpa**
   - Target: `workflow-controller` deployment
   - Min/Max: 2-8 replicas
   - Metrics: CPU 70%, Memory 80%

3. **cache-server-hpa**
4. **ml-pipeline-persistenceagent-hpa**
5. **ml-pipeline-scheduledworkflow-hpa**
6. **ml-pipeline-ui-hpa**
7. **ml-pipeline-visualizationserver-hpa**

**Behavior configuration:**
```yaml
behavior:
  scaleUp:
    policies:
      - type: Percent
        value: 50
        periodSeconds: 15
      - type: Pods
        value: 2
        periodSeconds: 15
    selectPolicy: Max
    stabilizationWindowSeconds: 0
  scaleDown:
    policies:
      - type: Percent
        value: 50
        periodSeconds: 60
    selectPolicy: Min
    stabilizationWindowSeconds: 300
```

**Ý nghĩa:**
- **Scale up nhanh**: Thêm 50% hoặc 2 pods (lấy max) mỗi 15s
- **Scale down chậm**: Giảm 50% mỗi 60s, đợi 5 phút để stable

#### Production Overlay (`scaling/overlays/prod/`)

**File: `kustomization.yaml`**
```yaml
resources:
  - ../../base

patches:
  - path: hpa-thresholds-patch.yaml
    target:
      kind: HorizontalPodAutoscaler
      name: ml-pipeline-hpa
```

**File: `hpa-thresholds-patch.yaml`**
```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: ml-pipeline-hpa
  namespace: kubeflow
spec:
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70  # Production: Lower threshold
```

**Production tuning:**
- CPU threshold: 70% (base có thể là 75%)
- Scale sớm hơn để handle traffic spikes
- Avoid saturation

---

### 4. Pipelines (`pipelines/`)

**ML pipeline configurations (versioned).**

#### COVID Detection Pipeline (`pipelines/covid-detection/versions/v1.0.0/`)

**Structure:**
```
versions/
└── v1.0.0/
    ├── kustomization.yaml
    ├── pipeline-config.yaml
    └── ... (other pipeline resources)
```

**Versioning strategy:**
- Mỗi version trong folder riêng (`v1.0.0`, `v1.0.1`, etc.)
- ArgoCD deploy từ specific version tag
- Rollback dễ dàng bằng cách point to older version

---

## 🔧 Kustomize Usage

### Build Manifests

**Infrastructure (production):**
```bash
# Build manifests
kubectl kustomize manifests/infrastructure/overlays/prod

# Apply directly
kubectl apply -k manifests/infrastructure/overlays/prod

# View resources
kubectl kustomize manifests/infrastructure/overlays/prod > /tmp/infra.yaml
cat /tmp/infra.yaml
```

**Scaling (production):**
```bash
kubectl kustomize manifests/scaling/overlays/prod
kubectl apply -k manifests/scaling/overlays/prod
```

### Verify Kustomization

**Check syntax:**
```bash
kubectl kustomize manifests/infrastructure/overlays/prod --enable-alpha-plugins

# Should not have errors or warnings
```

**Common warnings (đã fix):**
- ❌ `'bases' is deprecated` → ✅ Use `resources`
- ❌ `'commonLabels' is deprecated` → ✅ Use `labels`
- ❌ `'patchesStrategicMerge' is deprecated` → ✅ Use `patches`

---

## 🚀 Deployment via ArgoCD

### Infrastructure Deployment

**ArgoCD Application:**
```yaml
# argocd-apps/infrastructure-app.yaml
spec:
  source:
    path: manifests/infrastructure/overlays/prod
  destination:
    namespace: kubeflow
```

**Deployed resources:**
```bash
# Check deployment
kubectl get statefulset mysql-statefulset -n kubeflow
kubectl get pods -n kubeflow -l app=mysql
kubectl get pvc -n kubeflow
kubectl get svc -n kubeflow -l app=mysql
```

**Expected:**
```
StatefulSet: mysql-statefulset (3/3 replicas)
Pods:
  - mysql-statefulset-0 (Running)
  - mysql-statefulset-1 (Running)
  - mysql-statefulset-2 (Running)
PVCs:
  - data-mysql-statefulset-0 (Bound, 20Gi)
  - data-mysql-statefulset-1 (Bound, 20Gi)
  - data-mysql-statefulset-2 (Bound, 20Gi)
Services:
  - mysql-headless (ClusterIP: None)
  - mysql-statefulset-service (ClusterIP)
```

### Scaling Deployment

**ArgoCD Application:**
```yaml
# argocd-apps/scaling-app.yaml
spec:
  source:
    path: manifests/scaling/overlays/prod
  destination:
    namespace: kubeflow
```

**Deployed resources:**
```bash
# Check HPAs
kubectl get hpa -n kubeflow

# Watch autoscaling in action
kubectl get hpa ml-pipeline-hpa -n kubeflow --watch
```

**Expected:**
```
NAME                      REFERENCE                 TARGETS        MINPODS   MAXPODS   REPLICAS
ml-pipeline-hpa           Deployment/ml-pipeline    2%/70%         2         10        2
workflow-controller-hpa   Deployment/workflow-...   2%/70%, 20%/80% 2         8         2
```

---

## 🔍 Troubleshooting

### Issue 1: Kustomize Build Errors

**Error:**
```
Error: no matches for Id StatefulSet.v1.apps/mysql-statefulset.[noNs]
failed to find unique target for patch
```

**Root cause:** Patch không có namespace, kustomize không match được target.

**Fix:**
```yaml
# mysql-replicas-patch.yaml PHẢI có namespace
metadata:
  name: mysql-statefulset
  namespace: kubeflow  # ← REQUIRED
```

### Issue 2: Deprecated Kustomize Syntax

**Warnings:**
```
Warning: 'bases' is deprecated. Please use 'resources' instead.
Warning: 'commonLabels' is deprecated. Please use 'labels' instead.
Warning: 'patchesStrategicMerge' is deprecated. Please use 'patches' instead.
```

**Fix:** Tất cả đã được update trong project này.

**Old syntax → New syntax:**
```yaml
# OLD (deprecated)
bases:
  - ../../base
commonLabels:
  app: mysql
patchesStrategicMerge:
  - patch.yaml

# NEW (current)
resources:
  - ../../base
labels:
  - pairs:
      app: mysql
patches:
  - path: patch.yaml
    target:
      kind: StatefulSet
      name: mysql-statefulset
```

### Issue 3: PersistentVolume Immutable Field Error

**Error:**
```
PersistentVolume "mysql-statefulset-pv" is invalid:
nodeAffinity: Invalid value: field is immutable
```

**Root cause:** PVs đã tồn tại, ArgoCD cố update immutable fields.

**Fix:**
```yaml
# kustomization.yaml - KHÔNG include PVC
resources:
  - mysql-secret.yaml
  - mysql-statefulset.yaml
  # ❌ REMOVED: - mysql-pvc.yaml
```

**Explanation:**
- PVs already exist and bound to PVCs
- StatefulSet `volumeClaimTemplates` handles PVC creation
- Manual PV definitions conflict with existing resources

### Issue 4: HPA Not Scaling

**Symptoms:** HPA shows `<unknown>` for targets.

**Check:**
```bash
# Metrics server installed?
kubectl get deployment metrics-server -n kube-system

# HPA status
kubectl describe hpa ml-pipeline-hpa -n kubeflow
```

**Common causes:**
1. Metrics server not installed
2. Resource requests not set on pods
3. Target deployment not exist

**Fix:**
```bash
# Install metrics server
kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml

# Verify
kubectl top nodes
kubectl top pods -n kubeflow
```

### Issue 5: MySQL Pods CrashLoopBackOff

**Check logs:**
```bash
kubectl logs mysql-statefulset-0 -n kubeflow

# Common issues:
# - Insufficient resources
# - PVC not bound
# - Secret missing
```

**Fix:**
```bash
# Check PVCs
kubectl get pvc -n kubeflow

# Check secret
kubectl get secret mysql-secret -n kubeflow -o yaml

# Check resources on node
kubectl describe node

# Increase resources if needed (edit statefulset via Git)
```

---

## 📚 Best Practices

### 1. Kustomize Structure

**Organize theo môi trường:**
```
component/
├── base/              # Common configuration
│   ├── kustomization.yaml
│   └── resources.yaml
└── overlays/
    ├── dev/          # Development overrides
    ├── staging/      # Staging overrides
    └── prod/         # Production overrides
```

### 2. Patching Strategy

**Strategic Merge Patch (recommended):**
```yaml
patches:
  - path: patch.yaml
    target:
      kind: StatefulSet
      name: mysql-statefulset
```

**JSON Patch (for complex changes):**
```yaml
patches:
  - target:
      kind: Deployment
      name: app
    patch: |-
      - op: replace
        path: /spec/replicas
        value: 3
```

### 3. Labels và Selectors

**Luôn dùng consistent labels:**
```yaml
labels:
  - pairs:
      app: mysql
      component: infrastructure
      environment: production
      version: week6
      managed-by: argocd
```

**Tránh thay đổi selector labels:**
- StatefulSet selectors are immutable
- Changing requires delete/recreate

### 4. Resource Management

**Luôn set requests và limits:**
```yaml
resources:
  requests:
    cpu: "1"
    memory: "2Gi"
  limits:
    cpu: "2"
    memory: "4Gi"
```

**Guidelines:**
- Requests: Minimum resources needed
- Limits: Maximum allowed (prevent resource hogging)
- For production: requests = 70-80% of limits

### 5. Storage

**PersistentVolume best practices:**
- Use StorageClass for dynamic provisioning
- Set `reclaimPolicy: Retain` for important data
- Backup PVs regularly

**For StatefulSets:**
- Use `volumeClaimTemplates` (auto PVC creation)
- Don't manage PVs manually in GitOps
- Let StatefulSet controller handle lifecycle

---

## ✅ Verification Commands

### Infrastructure

```bash
# MySQL StatefulSet
kubectl get statefulset mysql-statefulset -n kubeflow
kubectl get pods -n kubeflow -l app=mysql
kubectl get pvc -n kubeflow | grep mysql

# Test connectivity
kubectl run -it --rm mysql-client --image=mysql:8.0 --restart=Never -n kubeflow -- \
  mysql -h mysql-statefulset-service -u kubeflow -pkubeflow123 -e "SHOW DATABASES;"
```

### Scaling

```bash
# HPAs
kubectl get hpa -n kubeflow
kubectl top pods -n kubeflow

# Watch scaling
kubectl get hpa ml-pipeline-hpa -n kubeflow --watch

# Generate load to test (optional)
kubectl run -it load-generator --rm --image=busybox --restart=Never -- /bin/sh
```

### Kustomize

```bash
# Validate build
kubectl kustomize manifests/infrastructure/overlays/prod
kubectl kustomize manifests/scaling/overlays/prod

# Dry run apply
kubectl apply -k manifests/infrastructure/overlays/prod --dry-run=client
```

---

## 📖 Related Documentation

- **ArgoCD Apps**: `argocd-apps/README.md`
- **ArgoCD Installation**: `week10/README.md`
- **Week 6 (Database)**: `week6+7+8+9/README.md`
- **Week 7 (HPA)**: `week6+7+8+9/README.md`
- **Kustomize Docs**: https://kustomize.io/

---

**Last Updated**: 2026-01-05
**Version**: 1.0.0
