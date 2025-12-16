# Phase 1: Single-Pod Data Persistence Test

**Phase:** 01
**Status:** PENDING
**Duration:** ~30 minutes

## Objective

Verify MySQL data persists when pod is deleted and recreated by StatefulSet controller. Test that PVC reattaches to new pod with all data intact.

## Context

Current setup has StatefulSet with 1 replica using VolumeClaimTemplate. Need to validate:
- PVC survives pod deletion
- New pod reattaches to same PVC
- MySQL data readable after recreation

## Requirements

### Functional
- Insert test data into MySQL
- Delete pod `mysql-statefulset-0`
- StatefulSet recreates pod automatically
- Query same data from new pod

### Non-Functional
- Pod recreation time < 2 minutes
- Zero data loss
- No manual intervention required

## Current Configuration Analysis

**StatefulSet:** `mysql-statefulset`
```yaml
spec:
  replicas: 1
  persistentVolumeClaimRetentionPolicy:
    whenDeleted: Retain  # ✓ PVC survives StatefulSet deletion
    whenScaled: Retain   # ✓ PVC survives scale-down
  volumeClaimTemplates:
    - name: data
      spec:
        accessModes: [ReadWriteOnce]
        storageClassName: kubeflow-storage
        storage: 20Gi
```

**PVC:** `data-mysql-statefulset-0`
- Status: Bound to `mysql-statefulset-pv`
- Volume: hostPath `/data/mysql-statefulset` on k8s-master-1

**Security Context (MISSING):**
- No fsGroup configured
- MySQL runs as UID 999, needs write permissions

## Implementation Steps

### Step 1: Add Security Context (fsGroup)
**Why:** Ensure MySQL container can write to volume

**Action:**
```bash
kubectl patch statefulset mysql-statefulset -n kubeflow --type='json' \
  -p='[{"op":"add","path":"/spec/template/spec/securityContext","value":{"fsGroup":999}}]'
```

**Verification:**
```bash
kubectl get sts mysql-statefulset -n kubeflow -o jsonpath='{.spec.template.spec.securityContext.fsGroup}'
# Expected: 999
```

**Note:** This will trigger rolling update, pod will restart.

### Step 2: Wait for Pod Ready
```bash
kubectl wait --for=condition=ready pod/mysql-statefulset-0 -n kubeflow --timeout=300s
```

### Step 3: Create Test Database and Insert Data

**Get MySQL credentials:**
```bash
export MYSQL_ROOT_PASSWORD=$(kubectl get secret mysql-secret -n kubeflow -o jsonpath='{.data.root-password}' | base64 -d)
```

**Connect to MySQL:**
```bash
kubectl exec -it mysql-statefulset-0 -n kubeflow -- mysql -uroot -p"$MYSQL_ROOT_PASSWORD"
```

**SQL Commands:**
```sql
-- Create test database
CREATE DATABASE test_persistence;
USE test_persistence;

-- Create test table
CREATE TABLE volume_test (
    id INT PRIMARY KEY AUTO_INCREMENT,
    test_name VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    data TEXT
);

-- Insert test data
INSERT INTO volume_test (test_name, data) VALUES
    ('pod-deletion-test', 'This data must survive pod deletion'),
    ('pvc-reattachment-test', 'PVC should reattach to new pod'),
    ('statefulset-test', 'StatefulSet guarantees stable storage');

-- Verify insertion
SELECT * FROM volume_test;

-- Record checksum
SELECT MD5(GROUP_CONCAT(data ORDER BY id)) as data_checksum FROM volume_test;
```

**Save checksum for later verification:**
```bash
CHECKSUM=$(kubectl exec mysql-statefulset-0 -n kubeflow -- mysql -uroot -p"$MYSQL_ROOT_PASSWORD" \
  -e "USE test_persistence; SELECT MD5(GROUP_CONCAT(data ORDER BY id)) FROM volume_test;" -N -s)
echo "Original checksum: $CHECKSUM"
```

### Step 4: Record Pod State Before Deletion

```bash
kubectl get pod mysql-statefulset-0 -n kubeflow -o yaml > /tmp/pod-before-deletion.yaml
kubectl get pvc data-mysql-statefulset-0 -n kubeflow -o yaml > /tmp/pvc-before-deletion.yaml
```

**Key info to record:**
```bash
echo "Pod UID: $(kubectl get pod mysql-statefulset-0 -n kubeflow -o jsonpath='{.metadata.uid}')"
echo "PVC UID: $(kubectl get pvc data-mysql-statefulset-0 -n kubeflow -o jsonpath='{.metadata.uid}')"
echo "PV: $(kubectl get pvc data-mysql-statefulset-0 -n kubeflow -o jsonpath='{.spec.volumeName}')"
```

### Step 5: Delete Pod

```bash
# Delete pod (StatefulSet will recreate it)
kubectl delete pod mysql-statefulset-0 -n kubeflow

# Immediately watch recreation
kubectl get pods -n kubeflow -w -l app=mysql-statefulset
```

**Expected behavior:**
1. Pod enters `Terminating` state
2. After grace period (30s), pod removed
3. StatefulSet controller creates new pod
4. New pod goes: Pending → ContainerCreating → Running → Ready

### Step 6: Wait for New Pod Ready

```bash
kubectl wait --for=condition=ready pod/mysql-statefulset-0 -n kubeflow --timeout=300s
```

**Measure recreation time:**
```bash
kubectl get events -n kubeflow --sort-by='.lastTimestamp' | grep mysql-statefulset-0
```

### Step 7: Verify Data Persistence

**Check PVC unchanged:**
```bash
kubectl get pvc data-mysql-statefulset-0 -n kubeflow -o yaml > /tmp/pvc-after-recreation.yaml

# Compare UIDs (should be identical)
diff <(grep 'uid:' /tmp/pvc-before-deletion.yaml) \
     <(grep 'uid:' /tmp/pvc-after-recreation.yaml)
```

**Verify pod attached to same PVC:**
```bash
kubectl get pod mysql-statefulset-0 -n kubeflow -o jsonpath='{.spec.volumes[?(@.name=="data")].persistentVolumeClaim.claimName}'
# Expected: data-mysql-statefulset-0
```

**Verify MySQL data:**
```bash
# Wait for MySQL ready
kubectl exec mysql-statefulset-0 -n kubeflow -- mysqladmin ping -h localhost

# Query test table
kubectl exec mysql-statefulset-0 -n kubeflow -- mysql -uroot -p"$MYSQL_ROOT_PASSWORD" \
  -e "USE test_persistence; SELECT * FROM volume_test;"

# Verify checksum matches
NEW_CHECKSUM=$(kubectl exec mysql-statefulset-0 -n kubeflow -- mysql -uroot -p"$MYSQL_ROOT_PASSWORD" \
  -e "USE test_persistence; SELECT MD5(GROUP_CONCAT(data ORDER BY id)) FROM volume_test;" -N -s)

if [ "$CHECKSUM" = "$NEW_CHECKSUM" ]; then
    echo "✓ SUCCESS: Data checksum matches!"
else
    echo "✗ FAIL: Data checksum mismatch!"
    echo "  Original: $CHECKSUM"
    echo "  New: $NEW_CHECKSUM"
fi
```

### Step 8: Additional Validation

**Check filesystem on node:**
```bash
# SSH to k8s-master-1 and verify data files exist
ssh k8s-master-1 "ls -lah /data/mysql-statefulset/"
# Should see MySQL data files (ibdata1, ib_logfile*, mysql/, etc.)
```

**Verify no errors in pod logs:**
```bash
kubectl logs mysql-statefulset-0 -n kubeflow | grep -i error || echo "No errors found"
```

## Success Criteria

- [x] Pod recreated within 2 minutes
- [x] PVC UID unchanged (same PVC reattached)
- [x] PV binding intact
- [x] Test database exists
- [x] All 3 rows present in volume_test table
- [x] Data checksum matches original
- [x] No MySQL errors in logs

## Test Script

**File:** `/root/plans/251216-0950-mysql-shared-volume-testing/scripts/test-phase-01.sh`

```bash
#!/bin/bash
set -e

NS="kubeflow"
POD="mysql-statefulset-0"
PVC="data-mysql-statefulset-0"

# Get MySQL password
export MYSQL_ROOT_PASSWORD=$(kubectl get secret mysql-secret -n $NS -o jsonpath='{.data.root-password}' | base64 -d)

# Step 1: Insert test data
echo "=== Step 1: Creating test data ==="
kubectl exec $POD -n $NS -- mysql -uroot -p"$MYSQL_ROOT_PASSWORD" <<EOF
CREATE DATABASE IF NOT EXISTS test_persistence;
USE test_persistence;
CREATE TABLE IF NOT EXISTS volume_test (
    id INT PRIMARY KEY AUTO_INCREMENT,
    test_name VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    data TEXT
);
TRUNCATE TABLE volume_test;
INSERT INTO volume_test (test_name, data) VALUES
    ('pod-deletion-test', 'This data must survive pod deletion'),
    ('pvc-reattachment-test', 'PVC should reattach to new pod'),
    ('statefulset-test', 'StatefulSet guarantees stable storage');
SELECT * FROM volume_test;
EOF

# Step 2: Record checksum
CHECKSUM=$(kubectl exec $POD -n $NS -- mysql -uroot -p"$MYSQL_ROOT_PASSWORD" \
  -e "USE test_persistence; SELECT MD5(GROUP_CONCAT(data ORDER BY id)) FROM volume_test;" -N -s)
echo "Original checksum: $CHECKSUM"

# Step 3: Record PVC UID
PVC_UID=$(kubectl get pvc $PVC -n $NS -o jsonpath='{.metadata.uid}')
echo "PVC UID: $PVC_UID"

# Step 4: Delete pod
echo "=== Step 2: Deleting pod ==="
kubectl delete pod $POD -n $NS
echo "Waiting for pod recreation..."

# Step 5: Wait for ready
kubectl wait --for=condition=ready pod/$POD -n $NS --timeout=300s
echo "Pod recreated successfully"

# Step 6: Verify PVC unchanged
NEW_PVC_UID=$(kubectl get pvc $PVC -n $NS -o jsonpath='{.metadata.uid}')
if [ "$PVC_UID" = "$NEW_PVC_UID" ]; then
    echo "✓ PVC UID unchanged: $PVC_UID"
else
    echo "✗ FAIL: PVC UID changed!"
    exit 1
fi

# Step 7: Wait for MySQL ready
echo "=== Step 3: Verifying data persistence ==="
sleep 10
kubectl exec $POD -n $NS -- mysqladmin ping -h localhost

# Step 8: Verify data
kubectl exec $POD -n $NS -- mysql -uroot -p"$MYSQL_ROOT_PASSWORD" \
  -e "USE test_persistence; SELECT * FROM volume_test;"

NEW_CHECKSUM=$(kubectl exec $POD -n $NS -- mysql -uroot -p"$MYSQL_ROOT_PASSWORD" \
  -e "USE test_persistence; SELECT MD5(GROUP_CONCAT(data ORDER BY id)) FROM volume_test;" -N -s)

if [ "$CHECKSUM" = "$NEW_CHECKSUM" ]; then
    echo "✓ SUCCESS: Data checksum matches!"
    echo "  Checksum: $CHECKSUM"
else
    echo "✗ FAIL: Data checksum mismatch!"
    echo "  Original: $CHECKSUM"
    echo "  New: $NEW_CHECKSUM"
    exit 1
fi

echo "=== Phase 1 Test PASSED ==="
```

## Expected Results

**Timeline:**
```
T+0s:    Delete pod
T+0-30s: Pod terminating (grace period)
T+30s:   Pod removed
T+31s:   StatefulSet creates new pod
T+35s:   Pod scheduled (PVC binding)
T+40s:   Container starts
T+50s:   MySQL initialization
T+60s:   Pod ready (total: ~1 minute)
```

**PVC Status:**
- Before: Bound to mysql-statefulset-pv
- During deletion: Remains Bound (not deleted)
- After recreation: Still Bound to same PV

**Data Integrity:**
- Database: test_persistence exists
- Table: volume_test with 3 rows
- Checksum: Matches original

## Troubleshooting

### Pod Stuck in Pending
**Cause:** PVC binding issue or node unavailable

**Fix:**
```bash
kubectl describe pod mysql-statefulset-0 -n kubeflow
kubectl describe pvc data-mysql-statefulset-0 -n kubeflow
# Check if PV is still bound
kubectl get pv mysql-statefulset-pv
```

### MySQL Crashes After Recreation
**Cause:** Permission issues or corrupted data

**Fix:**
```bash
# Check logs
kubectl logs mysql-statefulset-0 -n kubeflow

# Verify fsGroup applied
kubectl get pod mysql-statefulset-0 -n kubeflow -o jsonpath='{.spec.securityContext.fsGroup}'

# Check file permissions on node
ssh k8s-master-1 "ls -ln /data/mysql-statefulset/ | head -20"
```

### Data Missing After Recreation
**Cause:** Wrong PVC attached or data directory empty

**Fix:**
```bash
# Verify PVC name
kubectl get pod mysql-statefulset-0 -n kubeflow -o jsonpath='{.spec.volumes[?(@.name=="data")]}'

# Check PV path on node
kubectl get pv mysql-statefulset-pv -o jsonpath='{.spec.hostPath.path}'
ssh k8s-master-1 "ls -lah /data/mysql-statefulset/"
```

## Cleanup (Optional)

**Remove test data (keep pod running):**
```bash
kubectl exec mysql-statefulset-0 -n kubeflow -- mysql -uroot -p"$MYSQL_ROOT_PASSWORD" \
  -e "DROP DATABASE test_persistence;"
```

**Do NOT delete:**
- StatefulSet (production service)
- PVC (contains real data)
- PV (storage backend)

## Next Phase

After successful completion, proceed to:
→ **Phase 2:** `phase-02-multi-replica-isolation.md`

## Phase Report Template

```markdown
# Phase 1 Execution Report

**Date:** YYYY-MM-DD
**Executed By:** [name]
**Duration:** [actual time]

## Results
- Pod deletion time: [Xs]
- Pod recreation time: [Xs]
- Total downtime: [Xs]
- Data checksum: [✓ MATCH / ✗ MISMATCH]

## Issues Encountered
- [None / List issues]

## Observations
- [Key findings]

## Status: [PASSED / FAILED]
```
