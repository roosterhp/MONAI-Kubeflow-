# Week 9: MySQL StatefulSet Testing - Volume Sharing & Data Persistence

## Mục lục
- [Tổng quan những gì đã làm](#tổng-quan-những-gì-đã-làm)
- [Research Findings](#research-findings)
- [Phase 1: Single-Pod Data Persistence](#phase-1-single-pod-data-persistence)
- [Phase 2: Multi-Replica Isolation Testing](#phase-2-multi-replica-isolation-testing)
- [Test Results & Analysis](#test-results--analysis)
- [Issues & Best Practices](#issues--best-practices)
- [Next Steps](#next-steps)

---

## Tổng quan những gì đã làm

### 1. **Comprehensive Research về Shared Volumes**
Deep-dive research về Kubernetes volume patterns, MySQL data directory sharing risks, và StatefulSet best practices.

### 2. **Data Persistence Testing (Phase 1)**
Test pod deletion → recreation để verify PVC persistence và data integrity với checksums.

### 3. **Multi-Replica Isolation Testing (Phase 2)**
Scale MySQL StatefulSet to 3 replicas, verify mỗi pod có isolated data directory, test independent lifecycle.

### 4. **Documentation**
Tạo comprehensive test report với performance metrics, timeline analysis, và production recommendations.

---

## Research Findings

### Key Questions Addressed

**Q1: Xóa pod A → tạo pod B → pod B có thấy đúng data cũ?**
**Answer:** ✅ **YES** - PVC persists, data 100% intact

**Q2: Nhiều pod DB cùng mount vào 1 volume?**
**Answer:** ❌ **NO** (Anti-pattern) → Data corruption guaranteed

**Q3: Nhiều pod mỗi pod 1 volume?**
**Answer:** ✅ **YES** (Safe pattern) → Perfect isolation, tested successfully

### Critical Findings

#### ❌ **Anti-Pattern: Shared Data Directory**
```
┌─────────────────────────────────────┐
│     1 PVC/PV (Shared Volume)        │
│     /data/mysql-shared              │
└─────────────────────────────────────┘
         ↑           ↑           ↑
         │           │           │
    ┌────┴───┐  ┌────┴───┐  ┌────┴───┐
    │ Pod-0  │  │ Pod-1  │  │ Pod-2  │
    │ MySQL  │  │ MySQL  │  │ MySQL  │
    └────────┘  └────────┘  └────────┘
```

**Problem:**
- 3 MySQL instances cùng ghi vào 1 data directory
- InnoDB tablespace corruption (không support multi-instance)
- File locking failures (NFS locks unreliable)
- **Result:** DATA CORRUPTION guaranteed

**MySQL Official Docs:**
> "Never have two servers that update data in same databases"
> "External locking unreliable on NFS"
> "Only MyISAM/MERGE supported (NOT InnoDB)"

#### ✅ **Safe Pattern: Separate Volumes Per Pod**
```
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│  PVC-0/PV-0  │    │  PVC-1/PV-1  │    │  PVC-2/PV-2  │
│ /data/mysql  │    │ /data/mysql-1│    │ /data/mysql-2│
└──────────────┘    └──────────────┘    └──────────────┘
       ↑                   ↑                   ↑
       │                   │                   │
  ┌────┴───┐          ┌────┴───┐          ┌────┴───┐
  │ Pod-0  │          │ Pod-1  │          │ Pod-2  │
  │ MySQL  │          │ MySQL  │          │ MySQL  │
  └────────┘          └────────┘          └────────┘
```

**Benefits:**
- VolumeClaimTemplates tự động tạo PVC per pod
- Perfect data isolation (0% leakage)
- Independent pod lifecycle
- StatefulSet guarantees stable storage

---

## Phase 1: Single-Pod Data Persistence

### Objective
Verify PVC persists after pod deletion và StatefulSet tự động recreate pod với same PVC.

### Test Setup

**Environment:**
```
Cluster: Kubernetes v1.28.10 on Ubuntu 24.04 (kernel 6.14.0)
Nodes: k8s-master-1, k8s-master-2, k8s-master-3
Namespace: kubeflow
MySQL: mysql:8.0.44
Storage: 20Gi hostPath PV (RWO)
```

**StatefulSet Config:**
```yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: mysql-statefulset
  namespace: kubeflow
spec:
  serviceName: mysql-statefulset-service
  replicas: 1
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

### Test Procedure

#### Step 1: Insert Test Data
```bash
# Connect to MySQL
kubectl exec mysql-statefulset-0 -n kubeflow -- mysql -uroot -pkubeflow123

# Create database & table
CREATE DATABASE IF NOT EXISTS test_persistence;
USE test_persistence;
CREATE TABLE volume_test (
    id INT PRIMARY KEY AUTO_INCREMENT,
    test_name VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    data TEXT
);

# Insert test data
INSERT INTO volume_test (test_name, data) VALUES
    ('pod-deletion-test', 'This data must survive pod deletion'),
    ('pvc-reattachment-test', 'PVC should reattach to new pod'),
    ('statefulset-test', 'StatefulSet guarantees stable storage');
```

**Data Inserted:** 3 rows

#### Step 2: Record Baseline Metrics
```bash
# Calculate data checksum
CHECKSUM=$(kubectl exec mysql-statefulset-0 -n kubeflow -- \
  mysql -uroot -pkubeflow123 test_persistence \
  -e "SELECT MD5(GROUP_CONCAT(data ORDER BY id)) FROM volume_test;" -N -s)

echo "Original checksum: $CHECKSUM"
# Output: 3ef5b2976fe0c34b41994c10fca95e26

# Record PVC UID
PVC_UID=$(kubectl get pvc data-mysql-statefulset-0 -n kubeflow -o jsonpath='{.metadata.uid}')
echo "PVC UID: $PVC_UID"
# Output: ec9b24ba-a6d2-47a6-ae45-e877f590217c
```

#### Step 3: Delete Pod
```bash
# Record deletion time
echo "Deleting pod at: $(date)"
# Output: Tue Dec 16 10:18:15 AM +07 2025

# Delete pod
kubectl delete pod mysql-statefulset-0 -n kubeflow
# Output: pod "mysql-statefulset-0" deleted

# Wait for recreation
kubectl wait --for=condition=ready pod/mysql-statefulset-0 -n kubeflow --timeout=180s
# Output: pod/mysql-statefulset-0 condition met

echo "Pod recreated at: $(date)"
# Output: Tue Dec 16 10:18:28 AM +07 2025
```

**Recreation Time:** 13 seconds ⚡

#### Step 4: Verify Data Persistence
```bash
# Verify PVC UID unchanged
NEW_PVC_UID=$(kubectl get pvc data-mysql-statefulset-0 -n kubeflow -o jsonpath='{.metadata.uid}')
echo "New PVC UID: $NEW_PVC_UID"
# Output: ec9b24ba-a6d2-47a6-ae45-e877f590217c ✅ SAME

# Verify data exists
kubectl exec mysql-statefulset-0 -n kubeflow -- mysql -uroot -pkubeflow123 test_persistence \
  -e "SELECT * FROM volume_test;"

# Output:
# id  test_name              created_at            data
# 1   pod-deletion-test      2025-12-16 03:17:52   This data must survive pod deletion
# 2   pvc-reattachment-test  2025-12-16 03:17:52   PVC should reattach to new pod
# 3   statefulset-test       2025-12-16 03:17:52   StatefulSet guarantees stable storage

# Verify checksum
NEW_CHECKSUM=$(kubectl exec mysql-statefulset-0 -n kubeflow -- \
  mysql -uroot -pkubeflow123 test_persistence \
  -e "SELECT MD5(GROUP_CONCAT(data ORDER BY id)) FROM volume_test;" -N -s)
echo "New checksum: $NEW_CHECKSUM"
# Output: 3ef5b2976fe0c34b41994c10fca95e26 ✅ IDENTICAL
```

### Phase 1 Results

| Metric | Expected | Actual | Status |
|--------|----------|--------|--------|
| Pod recreation time | < 2 minutes | **13 seconds** | ✅ PASS |
| PVC UID unchanged | Same | Same | ✅ PASS |
| Data integrity | 100% | **100%** | ✅ PASS |
| Data checksum | Match | **Match** | ✅ PASS |
| All rows readable | 3 rows | **3 rows** | ✅ PASS |

**Conclusion:** ✅ **PASSED** - PVC persistence và data integrity verified.

---

## Phase 2: Multi-Replica Isolation Testing

### Objective
Scale to 3 replicas, verify mỗi pod có dedicated PVC với isolated data, test independent lifecycle.

### Test Setup

#### Step 1: Create Additional PVs
```bash
# Create PV for pod-1
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
EOF

# Create PV for pod-2 (tương tự, path: /data/mysql-statefulset-2)
```

**PVs Created:**
- `mysql-statefulset-pv` → `/data/mysql-statefulset` (existing)
- `mysql-statefulset-pv-1` → `/data/mysql-statefulset-1` (new)
- `mysql-statefulset-pv-2` → `/data/mysql-statefulset-2` (new)

#### Step 2: Scale StatefulSet
```bash
# Scale to 3 replicas
kubectl scale statefulset mysql-statefulset -n kubeflow --replicas=3

# Watch pod creation
kubectl get pods -n kubeflow -l app=mysql-statefulset -w

# Timeline:
# T+0s:  mysql-statefulset-1 created (Pending)
# T+16s: mysql-statefulset-1 Running (PVC bound)
# T+11s: mysql-statefulset-2 created (Pending)
# T+16s: mysql-statefulset-2 Running (PVC bound)
```

**PVC Bindings (Auto-generated):**
```
data-mysql-statefulset-0 → mysql-statefulset-pv   (20Gi, Bound)
data-mysql-statefulset-1 → mysql-statefulset-pv-1 (20Gi, Bound)
data-mysql-statefulset-2 → mysql-statefulset-pv-2 (20Gi, Bound)
```

#### Step 3: Insert Unique Data Per Pod
```bash
# Pod-0: Create pod_0_data database
kubectl exec mysql-statefulset-0 -n kubeflow -- mysql -uroot -pkubeflow123 <<EOF
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
EOF

# Pod-1: Create pod_1_data database (tương tự)
# Pod-2: Create pod_2_data database (tương tự)
```

**Data Distribution:**
```
Pod-0: pod_0_data (2 rows) → PVC-0 → /data/mysql-statefulset
Pod-1: pod_1_data (2 rows) → PVC-1 → /data/mysql-statefulset-1
Pod-2: pod_2_data (2 rows) → PVC-2 → /data/mysql-statefulset-2
```

#### Step 4: Verify Data Isolation

**Test 1: Each pod only sees own database**
```bash
# Check pod-0 databases
kubectl exec mysql-statefulset-0 -n kubeflow -- \
  mysql -uroot -pkubeflow123 -e "SHOW DATABASES;" | grep pod_
# Output: pod_0_data ✅

# Check pod-1 databases
kubectl exec mysql-statefulset-1 -n kubeflow -- \
  mysql -uroot -pkubeflow123 -e "SHOW DATABASES;" | grep pod_
# Output: pod_1_data ✅

# Check pod-2 databases
kubectl exec mysql-statefulset-2 -n kubeflow -- \
  mysql -uroot -pkubeflow123 -e "SHOW DATABASES;" | grep pod_
# Output: pod_2_data ✅
```

**Test 2: Cross-database access fails**
```bash
# Pod-0 tries to access pod_1_data
kubectl exec mysql-statefulset-0 -n kubeflow -- \
  mysql -uroot -pkubeflow123 -e "USE pod_1_data; SELECT * FROM isolation_test;"

# Output: ERROR 1049 (42000): Unknown database 'pod_1_data' ✅

# Pod-1 tries to access pod_2_data
kubectl exec mysql-statefulset-1 -n kubeflow -- \
  mysql -uroot -pkubeflow123 -e "USE pod_2_data; SELECT * FROM isolation_test;"

# Output: ERROR 1049 (42000): Unknown database 'pod_2_data' ✅
```

**Isolation Matrix:**
```
          | pod-0 | pod-1 | pod-2 |
----------|-------|-------|-------|
pod_0_data| ✅     | ❌     | ❌     |
pod_1_data| ❌     | ✅     | ❌     |
pod_2_data| ❌     | ❌     | ✅     |
```

#### Step 5: Test Independent Pod Lifecycle

**Delete pod-1 (middle pod):**
```bash
# Delete pod-1
kubectl delete pod mysql-statefulset-1 -n kubeflow
# Output: pod "mysql-statefulset-1" deleted

# Wait for recreation
kubectl wait --for=condition=ready pod/mysql-statefulset-1 -n kubeflow --timeout=180s
# Output: pod/mysql-statefulset-1 condition met
```

**Verify pods 0 and 2 unaffected:**
```bash
# Check pod-0 data
kubectl exec mysql-statefulset-0 -n kubeflow -- \
  mysql -uroot -pkubeflow123 pod_0_data -e "SELECT COUNT(*) FROM isolation_test;"
# Output: 2 rows ✅ (unchanged)

# Check pod-2 data
kubectl exec mysql-statefulset-2 -n kubeflow -- \
  mysql -uroot -pkubeflow123 pod_2_data -e "SELECT COUNT(*) FROM isolation_test;"
# Output: 2 rows ✅ (unchanged)
```

**Verify pod-1 data persisted:**
```bash
kubectl exec mysql-statefulset-1 -n kubeflow -- \
  mysql -uroot -pkubeflow123 pod_1_data -e "SELECT * FROM isolation_test;"

# Output:
# id  pod_id  test_data                              created_at
# 1   pod-1   This is pod 1 exclusive data          2025-12-16 03:21:04
# 2   pod-1   Should only exist in mysql-statefulset-1  2025-12-16 03:21:04
```

### Phase 2 Results

| Test | Expected | Actual | Status |
|------|----------|--------|--------|
| Total pods scaled | 3 | **3** | ✅ PASS |
| PVC auto-creation | 3 PVCs | **3 PVCs** | ✅ PASS |
| PVC binding correctness | Correct PV | **Correct PV** | ✅ PASS |
| Data isolation | 0% leakage | **0% leakage** | ✅ PASS |
| Cross-pod access | Fail (ERROR 1049) | **Fail (ERROR 1049)** | ✅ PASS |
| Pod-1 recreation time | < 2 min | **~20s** | ✅ PASS |
| Pod-0/2 unaffected | No change | **No change** | ✅ PASS |
| Pod-1 data persistence | 100% | **100%** | ✅ PASS |

**Conclusion:** ✅ **PASSED** - Perfect isolation, independent lifecycle, zero data loss.

---

## Test Results & Analysis

### Storage Topology (After Tests)

```
Node: k8s-master-1
├── /data/mysql-statefulset     → mysql-statefulset-pv   → data-mysql-statefulset-0 → pod-0 (pod_0_data)
├── /data/mysql-statefulset-1   → mysql-statefulset-pv-1 → data-mysql-statefulset-1 → pod-1 (pod_1_data)
└── /data/mysql-statefulset-2   → mysql-statefulset-pv-2 → data-mysql-statefulset-2 → pod-2 (pod_2_data)
```

### Performance Metrics

| Operation | Time | Notes |
|-----------|------|-------|
| Pod deletion → recreation (single) | 13s | Phase 1, stable |
| Pod-1 recreation (multi-pod) | ~20s | Phase 2, with 2 other pods running |
| PVC creation per pod | <5s | Automatic via VolumeClaimTemplates |
| StatefulSet scale 1→3 | ~22s | Sequential pod creation (0→1→2) |
| Data verification time | <1s | Checksum calculation |

### Key Observations

**1. StatefulSet Behavior:**
- Creates pods **sequentially** (not parallel): Pod-1 waits for Pod-0 Ready
- Each pod waits for PVC binding before starting
- Pod naming stable: `mysql-statefulset-{0,1,2}`

**2. PVC Persistence:**
- PVC UID unchanged across pod deletion/recreation
- Data 100% intact verified by MD5 checksums
- VolumeClaimTemplates auto-create PVCs with predictable names

**3. Data Isolation:**
- Perfect isolation: Each pod only sees own database
- File-level verification: Directories completely separate on node
- Cross-access fails with MySQL error (not permission denied)

**4. Pod Recovery:**
- StatefulSet auto-recreates deleted pods
- Same PVC reattaches (stable pod identity)
- No data loss, no downtime for other pods

---

## Issues & Best Practices

### Issues Found

#### 1. Storage PV/PVC Naming Mismatch (Pre-existing)
**Problem:** PV names swapped between MySQL and MinIO
```
mysql-pv      → Bound to minio-pvc     ❌ WRONG
minio-pv      → Bound to mysql-pv-claim ❌ WRONG
```

**Risk:** Data corruption if pods reschedule to wrong PVs

**Fix:** Documented in test report, needs careful migration

#### 2. HostPath Single Node Dependency
**Problem:** All PVs pinned to k8s-master-1
```yaml
nodeAffinity:
  required:
    nodeSelectorTerms:
    - matchExpressions:
      - key: kubernetes.io/hostname
        operator: In
        values:
        - k8s-master-1  # Single point of failure
```

**Limitation:** Pods can't reschedule to other nodes if master-1 fails

**Fix:** Deploy network-attached storage (NFS, Ceph) for multi-node portability

### Best Practices Confirmed

#### ✅ **1. StatefulSet + VolumeClaimTemplates**
```yaml
spec:
  volumeClaimTemplates:
  - metadata:
      name: data
    spec:
      accessModes: ["ReadWriteOnce"]
```

**Benefits:**
- Auto PVC creation per pod
- Stable pod-to-PVC binding
- Zero manual PVC management

#### ✅ **2. RWO Access Mode for Databases**
```yaml
accessModes: ["ReadWriteOnce"]  # NOT ReadWriteMany
```

**Rationale:**
- Prevents multi-pod mounting same volume
- MySQL requires exclusive data directory access
- RWX would enable anti-pattern

#### ✅ **3. PVC Retention Policy**
```yaml
persistentVolumeReclaimPolicy: Retain  # For production
```

**Rationale:**
- PVCs survive StatefulSet deletion
- Data safe during pod lifecycle operations
- Manual cleanup required (prevents accidental loss)

#### ✅ **4. Health Probes**
```yaml
livenessProbe:
  exec:
    command: ["mysqladmin", "ping"]
readinessProbe:
  exec:
    command: ["mysqladmin", "ping"]
```

**Benefits:**
- Kubernetes auto-restarts unhealthy pods
- Traffic routed only to ready pods
- Faster failure detection

### Anti-Patterns to Avoid

#### ❌ **1. Shared Data Directory**
```yaml
# DON'T DO THIS
volumes:
- name: mysql-data
  persistentVolumeClaim:
    claimName: shared-mysql-data  # Same PVC for all pods
```

**Result:** Data corruption, pod crashes, database integrity failure

#### ❌ **2. RWX for MySQL Data**
```yaml
# DON'T DO THIS
accessModes: ["ReadWriteMany"]  # Wrong for databases
```

**Result:** Multiple MySQL instances write to same files → corruption

#### ❌ **3. Deployment for Stateful Apps**
```yaml
# DON'T DO THIS
kind: Deployment  # Use StatefulSet instead
```

**Result:** No stable pod identity, random PVC assignment, data loss risk

---

## Data Sharing Solutions (Safe Patterns)

### Pattern 1: MySQL Replication (Recommended)
```
    ┌────────┐           ┌────────┐  ┌────────┐
    │ Pod-0  │  Binlog   │ Pod-1  │  │ Pod-2  │
    │PRIMARY │ ─────────▶│REPLICA │  │REPLICA │
    │(R/W)   │ Replicate │ (R/O)  │  │ (R/O)  │
    └────────┘           └────────┘  └────────┘
        ↓                    ↓          ↓
    [PVC-0]              [PVC-1]    [PVC-2]
```

**Setup:**
```bash
# Configure Primary (Pod-0)
kubectl exec mysql-statefulset-0 -n kubeflow -- mysql -uroot -p <<EOF
CREATE USER 'repl'@'%' IDENTIFIED BY 'repl_password';
GRANT REPLICATION SLAVE ON *.* TO 'repl'@'%';
FLUSH PRIVILEGES;
SHOW MASTER STATUS;  # Note File and Position
EOF

# Configure Replica (Pod-1)
kubectl exec mysql-statefulset-1 -n kubeflow -- mysql -uroot -p <<EOF
CHANGE MASTER TO
  MASTER_HOST='mysql-statefulset-0.mysql-statefulset-service',
  MASTER_USER='repl',
  MASTER_PASSWORD='repl_password',
  MASTER_LOG_FILE='binlog.000001',
  MASTER_LOG_POS=123;
START SLAVE;
SHOW SLAVE STATUS\G
EOF
```

**Benefits:**
- Native MySQL feature
- HA & read scalability
- Each pod still has separate volume
- No data corruption

### Pattern 2: Shared NFS Volume (For Application Files)
```yaml
# Mount NFS volume for shared files (NOT MySQL data)
volumeMounts:
- name: mysql-data
  mountPath: /var/lib/mysql  # Separate per pod
- name: shared-files
  mountPath: /mnt/shared     # NFS, ReadWriteMany
```

**Use cases:**
- Application uploads
- Shared configuration files
- Log aggregation
- **NOT for database data directory**

---

## Documentation & Scripts
### Test Scripts

#### test-phase-01.sh
```bash
#!/bin/bash
# Phase 1: Single-pod data persistence test
# - Insert test data
# - Record checksum & PVC UID
# - Delete pod
# - Verify data persists after recreation
# - Validate checksum matches

# Result: ✅ PASSED
# - Pod recreation: 13s
# - Data integrity: 100%
# - Checksum: Match
```

#### test-phase-02.sh
```bash
#!/bin/bash
# Phase 2: Multi-replica isolation test
# - Create 2 additional PVs
# - Scale StatefulSet 1→3
# - Insert unique data per pod
# - Verify data isolation
# - Test independent pod lifecycle

# Result: ✅ PASSED
# - 3 PVCs auto-created
# - 0% data leakage
# - Independent lifecycle verified
```
---

## Related Documentation

- [Week 6](./week6.md) - Kubernetes cluster setup với Kubespray
- [Week 7](./week7.md) - Node management, rolling upgrades, node failure testing
- [Week 8](./week8.md) - HPA autoscaling và MySQL StatefulSet deployment
---

## Appendix: Command Reference

### StatefulSet Management
```bash
# View StatefulSet
kubectl get statefulset mysql-statefulset -n kubeflow

# Scale StatefulSet
kubectl scale statefulset mysql-statefulset -n kubeflow --replicas=3

# Delete StatefulSet (PVCs retained!)
kubectl delete statefulset mysql-statefulset -n kubeflow

# Restart StatefulSet
kubectl rollout restart statefulset mysql-statefulset -n kubeflow
```

### PVC Management
```bash
# View PVCs
kubectl get pvc -n kubeflow

# Describe PVC
kubectl describe pvc data-mysql-statefulset-0 -n kubeflow

# Check PVC binding
kubectl get pvc data-mysql-statefulset-0 -n kubeflow -o jsonpath='{.spec.volumeName}'

# Delete PVC (WARNING: data loss!)
kubectl delete pvc data-mysql-statefulset-0 -n kubeflow
```

### Database Operations
```bash
# Connect to MySQL
kubectl exec -it mysql-statefulset-0 -n kubeflow -- mysql -uroot -pkubeflow123

# Check databases
kubectl exec mysql-statefulset-0 -n kubeflow -- \
  mysql -uroot -pkubeflow123 -e "SHOW DATABASES;"

# Verify data
kubectl exec mysql-statefulset-0 -n kubeflow -- \
  mysql -uroot -pkubeflow123 test_persistence -e "SELECT * FROM volume_test;"

# Calculate checksum
kubectl exec mysql-statefulset-0 -n kubeflow -- \
  mysql -uroot -pkubeflow123 test_persistence \
  -e "SELECT MD5(GROUP_CONCAT(data ORDER BY id)) FROM volume_test;" -N -s
```

### Testing Commands
```bash
# Run Phase 1 test
/root/plans/251216-0950-mysql-shared-volume-testing/scripts/test-phase-01.sh

# Run Phase 2 test
/root/plans/251216-0950-mysql-shared-volume-testing/scripts/test-phase-02.sh

# Monitor pods real-time
watch -n 2 'kubectl get pods -n kubeflow -l app=mysql-statefulset -o wide'

# Check PVC status
watch -n 2 'kubectl get pvc -n kubeflow | grep mysql-statefulset'
```

---

## References

### Research Reports
1. [Kubernetes Shared Volumes Research](../kubernetes-shared-volumes-research-251216.md)
2. [MySQL Shared Volume Kubernetes](../plans/mysql-shared-volume-research/reports/251216-mysql-shared-volume-kubernetes.md)

### External Documentation
- [Kubernetes StatefulSets](https://kubernetes.io/docs/concepts/workloads/controllers/statefulset/)
- [MySQL External Locking](https://dev.mysql.com/doc/refman/8.0/en/external-locking.html)
- [Persistent Volumes](https://kubernetes.io/docs/concepts/storage/persistent-volumes/)
- [MySQL on Kubernetes Best Practices](https://dev.mysql.com/doc/mysql-operator/en/)

---

**HOÀN THÀNH WEEK 9!** Database testing với StatefulSet patterns validated!
