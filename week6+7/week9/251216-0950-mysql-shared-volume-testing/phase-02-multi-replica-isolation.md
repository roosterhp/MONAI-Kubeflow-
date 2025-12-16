# Phase 2: Multi-Replica Data Isolation Test

**Phase:** 02
**Status:** PENDING
**Duration:** ~45 minutes
**Prerequisites:** Phase 1 completed successfully

## Objective

Scale MySQL StatefulSet to 3 replicas and verify:
1. Each pod gets dedicated PVC (data-mysql-statefulset-{0,1,2})
2. Data isolation between pods (no cross-contamination)
3. Independent pod lifecycle (deleting pod-1 doesn't affect pod-0 or pod-2)

## Context

StatefulSet VolumeClaimTemplates automatically create PVC per pod. Need to:
- Pre-create PVs for pod-1 and pod-2 (manual provisioner)
- Scale replicas to 3
- Test data isolation
- Verify each pod survives independent deletion

## Requirements

### Functional
- 3 MySQL pods running concurrently
- Each pod has unique data
- Pod deletion/recreation preserves per-pod data
- No data leakage between pods

### Non-Functional
- Each pod can read/write independently
- No performance degradation with multiple pods
- Clean pod startup sequence (pod-0 → pod-1 → pod-2)

## Architecture

### Storage Topology After Scaling

```
k8s-master-1 (node):
├── /data/mysql-statefulset    → mysql-statefulset-pv   → data-mysql-statefulset-0 → pod/mysql-statefulset-0
├── /data/mysql-statefulset-1  → mysql-statefulset-pv-1 → data-mysql-statefulset-1 → pod/mysql-statefulset-1
└── /data/mysql-statefulset-2  → mysql-statefulset-pv-2 → data-mysql-statefulset-2 → pod/mysql-statefulset-2
```

**Key Points:**
- Each pod has dedicated data directory
- No shared storage between pods
- Independent MySQL instances (not a cluster)
- Each pod can have different databases/tables

## Implementation Steps

### Step 1: Create Additional PersistentVolumes

**Why:** `kubeflow-storage` uses manual provisioner (no dynamic provisioning)

**PV for pod-1:**
```yaml
# /tmp/mysql-pv-1.yaml
apiVersion: v1
kind: PersistentVolume
metadata:
  name: mysql-statefulset-pv-1
spec:
  capacity:
    storage: 20Gi
  accessModes:
    - ReadWriteOnce
  persistentVolumeReclaimPolicy: Delete
  storageClassName: kubeflow-storage
  hostPath:
    path: /data/mysql-statefulset-1
    type: DirectoryOrCreate
  nodeAffinity:
    required:
      nodeSelectorTerms:
      - matchExpressions:
        - key: kubernetes.io/hostname
          operator: In
          values:
          - k8s-master-1
```

**PV for pod-2:**
```yaml
# /tmp/mysql-pv-2.yaml
apiVersion: v1
kind: PersistentVolume
metadata:
  name: mysql-statefulset-pv-2
spec:
  capacity:
    storage: 20Gi
  accessModes:
    - ReadWriteOnce
  persistentVolumeReclaimPolicy: Delete
  storageClassName: kubeflow-storage
  hostPath:
    path: /data/mysql-statefulset-2
    type: DirectoryOrCreate
  nodeAffinity:
    required:
      nodeSelectorTerms:
      - matchExpressions:
        - key: kubernetes.io/hostname
          operator: In
          values:
          - k8s-master-1
```

**Apply PVs:**
```bash
kubectl apply -f /tmp/mysql-pv-1.yaml
kubectl apply -f /tmp/mysql-pv-2.yaml

# Verify PVs created
kubectl get pv | grep mysql-statefulset
```

**Expected output:**
```
mysql-statefulset-pv     20Gi  RWO  Delete  Bound    kubeflow/data-mysql-statefulset-0   kubeflow-storage
mysql-statefulset-pv-1   20Gi  RWO  Delete  Available                                     kubeflow-storage
mysql-statefulset-pv-2   20Gi  RWO  Delete  Available                                     kubeflow-storage
```

### Step 2: Pre-Create Directories on Node

**Why:** Ensure directories exist before pod creation (hostPath DirectoryOrCreate)

```bash
# SSH to k8s-master-1
ssh k8s-master-1 "mkdir -p /data/mysql-statefulset-1 /data/mysql-statefulset-2"

# Set ownership (MySQL UID 999)
ssh k8s-master-1 "chown -R 999:999 /data/mysql-statefulset-1 /data/mysql-statefulset-2"

# Verify
ssh k8s-master-1 "ls -ld /data/mysql-statefulset*"
```

**Expected output:**
```
drwxr-xr-x 6 999 999 4096 Dec 09 15:54 /data/mysql-statefulset
drwxr-xr-x 2 999 999 4096 Dec 16 10:00 /data/mysql-statefulset-1
drwxr-xr-x 2 999 999 4096 Dec 16 10:00 /data/mysql-statefulset-2
```

### Step 3: Scale StatefulSet to 3 Replicas

```bash
# Scale up
kubectl scale statefulset mysql-statefulset -n kubeflow --replicas=3

# Watch pod creation
kubectl get pods -n kubeflow -l app=mysql-statefulset -w
```

**Expected behavior:**
1. Pod mysql-statefulset-1 starts (waits for PVC binding)
2. PVC data-mysql-statefulset-1 created → binds to mysql-statefulset-pv-1
3. Pod-1 goes Running → Ready
4. Pod mysql-statefulset-2 starts (same process)

**Wait for all pods ready:**
```bash
kubectl wait --for=condition=ready pod -l app=mysql-statefulset -n kubeflow --timeout=600s
```

### Step 4: Verify PVC Bindings

```bash
kubectl get pvc -n kubeflow | grep mysql-statefulset
```

**Expected output:**
```
data-mysql-statefulset-0  Bound  mysql-statefulset-pv    20Gi  RWO  kubeflow-storage
data-mysql-statefulset-1  Bound  mysql-statefulset-pv-1  20Gi  RWO  kubeflow-storage
data-mysql-statefulset-2  Bound  mysql-statefulset-pv-2  20Gi  RWO  kubeflow-storage
```

**Verify each pod mounted correct PVC:**
```bash
for i in 0 1 2; do
  echo "=== Pod $i ==="
  kubectl get pod mysql-statefulset-$i -n kubeflow -o jsonpath='{.spec.volumes[?(@.name=="data")].persistentVolumeClaim.claimName}'
  echo
done
```

### Step 5: Insert Unique Data in Each Pod

**Get MySQL password:**
```bash
export MYSQL_ROOT_PASSWORD=$(kubectl get secret mysql-secret -n kubeflow -o jsonpath='{.data.root-password}' | base64 -d)
```

**Pod 0 - Dataset A:**
```bash
kubectl exec mysql-statefulset-0 -n kubeflow -- mysql -uroot -p"$MYSQL_ROOT_PASSWORD" <<EOF
CREATE DATABASE IF NOT EXISTS pod_0_data;
USE pod_0_data;
CREATE TABLE isolation_test (
    id INT PRIMARY KEY AUTO_INCREMENT,
    pod_id VARCHAR(50),
    test_data VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
INSERT INTO isolation_test (pod_id, test_data) VALUES
    ('pod-0', 'This is pod 0 exclusive data'),
    ('pod-0', 'Should only exist in mysql-statefulset-0');
SELECT * FROM isolation_test;
EOF
```

**Pod 1 - Dataset B:**
```bash
kubectl exec mysql-statefulset-1 -n kubeflow -- mysql -uroot -p"$MYSQL_ROOT_PASSWORD" <<EOF
CREATE DATABASE IF NOT EXISTS pod_1_data;
USE pod_1_data;
CREATE TABLE isolation_test (
    id INT PRIMARY KEY AUTO_INCREMENT,
    pod_id VARCHAR(50),
    test_data VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
INSERT INTO isolation_test (pod_id, test_data) VALUES
    ('pod-1', 'This is pod 1 exclusive data'),
    ('pod-1', 'Should only exist in mysql-statefulset-1');
SELECT * FROM isolation_test;
EOF
```

**Pod 2 - Dataset C:**
```bash
kubectl exec mysql-statefulset-2 -n kubeflow -- mysql -uroot -p"$MYSQL_ROOT_PASSWORD" <<EOF
CREATE DATABASE IF NOT EXISTS pod_2_data;
USE pod_2_data;
CREATE TABLE isolation_test (
    id INT PRIMARY KEY AUTO_INCREMENT,
    pod_id VARCHAR(50),
    test_data VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
INSERT INTO isolation_test (pod_id, test_data) VALUES
    ('pod-2', 'This is pod 2 exclusive data'),
    ('pod-2', 'Should only exist in mysql-statefulset-2');
SELECT * FROM isolation_test;
EOF
```

### Step 6: Verify Data Isolation

**Test 1: Each pod only sees its own database**
```bash
for i in 0 1 2; do
  echo "=== Pod $i databases ==="
  kubectl exec mysql-statefulset-$i -n kubeflow -- mysql -uroot -p"$MYSQL_ROOT_PASSWORD" \
    -e "SHOW DATABASES;" | grep pod_
done
```

**Expected output:**
```
=== Pod 0 databases ===
pod_0_data

=== Pod 1 databases ===
pod_1_data

=== Pod 2 databases ===
pod_2_data
```

**Test 2: Cross-database access fails**
```bash
# Try to access pod_1_data from pod-0 (should fail)
kubectl exec mysql-statefulset-0 -n kubeflow -- mysql -uroot -p"$MYSQL_ROOT_PASSWORD" \
  -e "USE pod_1_data; SELECT * FROM isolation_test;" 2>&1 | grep -i "unknown database" && echo "✓ Isolation verified"
```

**Test 3: File-level verification**
```bash
# Check data directories on node
ssh k8s-master-1 "ls /data/mysql-statefulset/pod_0_data"
ssh k8s-master-1 "ls /data/mysql-statefulset-1/pod_1_data"
ssh k8s-master-1 "ls /data/mysql-statefulset-2/pod_2_data"
```

### Step 7: Test Independent Pod Lifecycle

**Delete pod-1 (middle pod):**
```bash
echo "=== Deleting pod-1 ==="
kubectl delete pod mysql-statefulset-1 -n kubeflow

# Watch recreation
kubectl get pods -n kubeflow -l app=mysql-statefulset -w
```

**Verify pods 0 and 2 unaffected:**
```bash
# Pod 0 still has its data
kubectl exec mysql-statefulset-0 -n kubeflow -- mysql -uroot -p"$MYSQL_ROOT_PASSWORD" \
  -e "USE pod_0_data; SELECT COUNT(*) FROM isolation_test;"

# Pod 2 still has its data
kubectl exec mysql-statefulset-2 -n kubeflow -- mysql -uroot -p"$MYSQL_ROOT_PASSWORD" \
  -e "USE pod_2_data; SELECT COUNT(*) FROM isolation_test;"
```

**Wait for pod-1 ready:**
```bash
kubectl wait --for=condition=ready pod/mysql-statefulset-1 -n kubeflow --timeout=300s
```

**Verify pod-1 data persisted:**
```bash
kubectl exec mysql-statefulset-1 -n kubeflow -- mysql -uroot -p"$MYSQL_ROOT_PASSWORD" \
  -e "USE pod_1_data; SELECT * FROM isolation_test;"
```

**Expected:** Both rows from pod-1 still exist.

### Step 8: Stress Test - Delete All Pods Simultaneously

```bash
# Delete all pods at once
kubectl delete pod -n kubeflow -l app=mysql-statefulset

# Watch recreation (should happen sequentially: 0 → 1 → 2)
kubectl get pods -n kubeflow -l app=mysql-statefulset -w
```

**Wait for all ready:**
```bash
kubectl wait --for=condition=ready pod -l app=mysql-statefulset -n kubeflow --timeout=600s
```

**Verify all data intact:**
```bash
for i in 0 1 2; do
  echo "=== Verifying pod-$i data ==="
  kubectl exec mysql-statefulset-$i -n kubeflow -- mysql -uroot -p"$MYSQL_ROOT_PASSWORD" \
    -e "USE pod_${i}_data; SELECT COUNT(*) FROM isolation_test;"
done
```

**Expected:** Each pod returns COUNT(*) = 2

## Success Criteria

- [x] 3 PVs created (mysql-statefulset-pv-{0,1,2})
- [x] 3 PVCs bound (data-mysql-statefulset-{0,1,2})
- [x] 3 pods running (mysql-statefulset-{0,1,2})
- [x] Each pod has unique database (pod_{0,1,2}_data)
- [x] Database pod_X only exists in pod-X
- [x] Cross-pod database access fails (isolation verified)
- [x] Pod-1 deletion doesn't affect pod-0 or pod-2
- [x] Pod-1 data persists after recreation
- [x] All pods survive simultaneous deletion

## Test Script

**File:** `/root/plans/251216-0950-mysql-shared-volume-testing/scripts/test-phase-02.sh`

```bash
#!/bin/bash
set -e

NS="kubeflow"
export MYSQL_ROOT_PASSWORD=$(kubectl get secret mysql-secret -n $NS -o jsonpath='{.data.root-password}' | base64 -d)

echo "=== Phase 2: Multi-Replica Isolation Test ==="

# Step 1: Create PVs
echo "Step 1: Creating PVs..."
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: PersistentVolume
metadata:
  name: mysql-statefulset-pv-1
spec:
  capacity:
    storage: 20Gi
  accessModes:
    - ReadWriteOnce
  persistentVolumeReclaimPolicy: Delete
  storageClassName: kubeflow-storage
  hostPath:
    path: /data/mysql-statefulset-1
    type: DirectoryOrCreate
  nodeAffinity:
    required:
      nodeSelectorTerms:
      - matchExpressions:
        - key: kubernetes.io/hostname
          operator: In
          values:
          - k8s-master-1
---
apiVersion: v1
kind: PersistentVolume
metadata:
  name: mysql-statefulset-pv-2
spec:
  capacity:
    storage: 20Gi
  accessModes:
    - ReadWriteOnce
  persistentVolumeReclaimPolicy: Delete
  storageClassName: kubeflow-storage
  hostPath:
    path: /data/mysql-statefulset-2
    type: DirectoryOrCreate
  nodeAffinity:
    required:
      nodeSelectorTerms:
      - matchExpressions:
        - key: kubernetes.io/hostname
          operator: In
          values:
          - k8s-master-1
EOF

# Step 2: Create directories
echo "Step 2: Creating directories on node..."
ssh k8s-master-1 "mkdir -p /data/mysql-statefulset-1 /data/mysql-statefulset-2 && chown -R 999:999 /data/mysql-statefulset-1 /data/mysql-statefulset-2"

# Step 3: Scale StatefulSet
echo "Step 3: Scaling to 3 replicas..."
kubectl scale statefulset mysql-statefulset -n $NS --replicas=3
kubectl wait --for=condition=ready pod -l app=mysql-statefulset -n $NS --timeout=600s
echo "All pods ready"

# Step 4: Insert unique data per pod
echo "Step 4: Inserting unique data in each pod..."
for i in 0 1 2; do
  kubectl exec mysql-statefulset-$i -n $NS -- mysql -uroot -p"$MYSQL_ROOT_PASSWORD" <<EOF
CREATE DATABASE IF NOT EXISTS pod_${i}_data;
USE pod_${i}_data;
CREATE TABLE IF NOT EXISTS isolation_test (
    id INT PRIMARY KEY AUTO_INCREMENT,
    pod_id VARCHAR(50),
    test_data VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
TRUNCATE TABLE isolation_test;
INSERT INTO isolation_test (pod_id, test_data) VALUES
    ('pod-$i', 'This is pod $i exclusive data'),
    ('pod-$i', 'Should only exist in mysql-statefulset-$i');
EOF
done

# Step 5: Verify isolation
echo "Step 5: Verifying data isolation..."
for i in 0 1 2; do
  DB_COUNT=$(kubectl exec mysql-statefulset-$i -n $NS -- mysql -uroot -p"$MYSQL_ROOT_PASSWORD" \
    -e "SHOW DATABASES;" -N -s | grep pod_ | wc -l)
  if [ "$DB_COUNT" -eq 1 ]; then
    echo "✓ Pod-$i: Only 1 pod database (isolation OK)"
  else
    echo "✗ Pod-$i: Found $DB_COUNT pod databases (isolation FAILED)"
    exit 1
  fi
done

# Step 6: Test pod-1 deletion
echo "Step 6: Testing pod-1 deletion and recreation..."
kubectl delete pod mysql-statefulset-1 -n $NS
kubectl wait --for=condition=ready pod/mysql-statefulset-1 -n $NS --timeout=300s

# Verify pod-1 data persisted
COUNT=$(kubectl exec mysql-statefulset-1 -n $NS -- mysql -uroot -p"$MYSQL_ROOT_PASSWORD" \
  -e "USE pod_1_data; SELECT COUNT(*) FROM isolation_test;" -N -s)
if [ "$COUNT" -eq 2 ]; then
  echo "✓ Pod-1 data persisted after recreation"
else
  echo "✗ Pod-1 data lost (found $COUNT rows, expected 2)"
  exit 1
fi

# Verify pods 0 and 2 unaffected
for i in 0 2; do
  COUNT=$(kubectl exec mysql-statefulset-$i -n $NS -- mysql -uroot -p"$MYSQL_ROOT_PASSWORD" \
    -e "USE pod_${i}_data; SELECT COUNT(*) FROM isolation_test;" -N -s)
  if [ "$COUNT" -eq 2 ]; then
    echo "✓ Pod-$i data unaffected"
  else
    echo "✗ Pod-$i data corrupted"
    exit 1
  fi
done

echo "=== Phase 2 Test PASSED ==="
```

## Expected Results

**Storage Layout:**
```
PV Name                    PVC Name                   Pod Name               Database
mysql-statefulset-pv    → data-mysql-statefulset-0 → mysql-statefulset-0 → pod_0_data
mysql-statefulset-pv-1  → data-mysql-statefulset-1 → mysql-statefulset-1 → pod_1_data
mysql-statefulset-pv-2  → data-mysql-statefulset-2 → mysql-statefulset-2 → pod_2_data
```

**Isolation Matrix:**
```
          | pod-0 | pod-1 | pod-2 |
----------|-------|-------|-------|
pod_0_data| ✓     | ✗     | ✗     |
pod_1_data| ✗     | ✓     | ✗     |
pod_2_data| ✗     | ✗     | ✓     |
```

## Troubleshooting

### Pod Stuck in Pending After Scaling
**Symptom:** mysql-statefulset-1 or -2 stuck in Pending

**Diagnose:**
```bash
kubectl describe pod mysql-statefulset-1 -n kubeflow
kubectl describe pvc data-mysql-statefulset-1 -n kubeflow
```

**Fix:**
- Check PV exists: `kubectl get pv mysql-statefulset-pv-1`
- Verify nodeAffinity matches node: `kubectl get nodes --show-labels`
- Ensure directory exists on node: `ssh k8s-master-1 ls -ld /data/mysql-statefulset-1`

### PVC Bound to Wrong PV
**Symptom:** data-mysql-statefulset-1 bound to mysql-statefulset-pv-2

**Cause:** PV selection timing race

**Fix:**
```bash
# Delete misbound PVC (if pod not started yet)
kubectl delete pvc data-mysql-statefulset-1 -n kubeflow

# Manually bind PVC to correct PV
kubectl patch pv mysql-statefulset-pv-1 -p '{"spec":{"claimRef":{"name":"data-mysql-statefulset-1","namespace":"kubeflow"}}}'
```

### Data Leakage Between Pods
**Symptom:** pod-0 can see pod_1_data database

**Cause:** Pods mounted same PV (corruption)

**Fix:**
```bash
# Check volume mounts
for i in 0 1 2; do
  kubectl get pod mysql-statefulset-$i -n kubeflow -o jsonpath='{.spec.volumes[?(@.name=="data")].persistentVolumeClaim.claimName}'
  echo
done

# Verify PV paths on node
kubectl get pv -o custom-columns=NAME:.metadata.name,PATH:.spec.hostPath.path
```

## Cleanup

**Scale back to 1 replica:**
```bash
kubectl scale statefulset mysql-statefulset -n kubeflow --replicas=1
```

**Note:** PVCs for pod-1 and pod-2 will be retained (retention policy)

**Optional: Delete test data**
```bash
kubectl exec mysql-statefulset-0 -n kubeflow -- mysql -uroot -p"$MYSQL_ROOT_PASSWORD" \
  -e "DROP DATABASE IF EXISTS pod_0_data;"
```

**Optional: Delete additional PVs**
```bash
# Delete PVCs first
kubectl delete pvc data-mysql-statefulset-1 data-mysql-statefulset-2 -n kubeflow

# Delete PVs
kubectl delete pv mysql-statefulset-pv-1 mysql-statefulset-pv-2

# Remove directories on node
ssh k8s-master-1 "rm -rf /data/mysql-statefulset-1 /data/mysql-statefulset-2"
```

## Next Phase

After successful completion, proceed to:
→ **Phase 3:** `phase-03-documentation.md`

## Phase Report Template

```markdown
# Phase 2 Execution Report

**Date:** YYYY-MM-DD
**Executed By:** [name]
**Duration:** [actual time]

## Results
- Total pods scaled: [X]
- PVC creation time: [Xs per PVC]
- Data isolation: [✓ VERIFIED / ✗ FAILED]
- Pod-1 recreation time: [Xs]

## Issues Encountered
- [None / List issues]

## Observations
- [Key findings about multi-pod behavior]

## Status: [PASSED / FAILED]
```
