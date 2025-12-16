# MySQL Shared Volume Testing - StatefulSet Pattern Implementation Plan

**Plan ID:** 251216-0950-mysql-shared-volume-testing
**Created:** 2025-12-16
**Status:** READY FOR IMPLEMENTATION

## Executive Summary

Test MySQL volume persistence and isolation in Kubeflow using StatefulSet with VolumeClaimTemplates pattern. Validates data persistence after pod deletion/recreation and multi-pod deployment with isolated storage.

**Key Objectives:**
1. Verify data persistence across pod lifecycle (delete → recreate → data intact)
2. Test multi-replica StatefulSet with isolated PVCs per pod
3. Document safe patterns for MySQL storage in Kubernetes

## Current State Analysis

**Existing Setup:**
- StatefulSet: `mysql-statefulset` (1 replica, running 6d10h)
- StorageClass: `kubeflow-storage` (no-provisioner, WaitForFirstConsumer)
- PV: hostPath on k8s-master-1 node (`/data/mysql-statefulset`)
- PVC: `data-mysql-statefulset-0` (20Gi, RWO, Bound)
- VolumeClaimTemplate: Already configured ✓

**Architecture Pattern (Already Implemented):**
```
StatefulSet → VolumeClaimTemplates → Auto-generated PVCs per pod
- Pod 0 → data-mysql-statefulset-0 → mysql-statefulset-pv
- Pod N → data-mysql-statefulset-N → (requires PV creation)
```

**Key Findings:**
- StatefulSet already uses VolumeClaimTemplates (CORRECT pattern ✓)
- PVC retention policy: `whenDeleted: Retain, whenScaled: Retain` ✓
- Current provisioner: manual (kubernetes.io/no-provisioner)
- Missing: fsGroup security context for MySQL permissions
- Missing: Additional PVs for multi-replica testing

## Test Strategy

### Phase 1: Single-Pod Data Persistence Test
**Objective:** Verify PVC persists after pod deletion

**Test Flow:**
```
1. Insert test data → mysql-statefulset-0
2. Delete pod → kubectl delete pod mysql-statefulset-0
3. StatefulSet recreates pod automatically
4. Verify data still exists in recreated pod
```

**Success Criteria:**
- Pod recreates within 2 minutes
- Same PVC (`data-mysql-statefulset-0`) reattaches
- Test table/data readable after recreation

### Phase 2: Multi-Pod Isolation Test
**Objective:** Verify each pod gets dedicated PVC with isolated data

**Test Flow:**
```
1. Create additional PVs (mysql-statefulset-pv-1, mysql-statefulset-pv-2)
2. Scale StatefulSet to 3 replicas
3. Insert different data in each pod
4. Verify data isolation (pod-0 ≠ pod-1 ≠ pod-2)
5. Delete pod-1, verify pod-1 data persists after recreation
```

**Success Criteria:**
- 3 PVCs created: data-mysql-statefulset-{0,1,2}
- Each pod reads/writes only its own data
- No data corruption or cross-contamination

### Phase 3: Production Pattern Validation
**Objective:** Document and validate recommended patterns

**Validation Points:**
- ✓ VolumeClaimTemplates usage
- ✓ PVC retention policy configuration
- ✓ Security context (fsGroup: 999 for MySQL)
- ✓ Node affinity for hostPath PVs
- ✗ Anti-pattern: Never share same PV between MySQL pods

## Implementation Phases

### Phase 1: Setup & Single-Pod Persistence Test
**File:** `phase-01-single-pod-persistence.md`
- Configure fsGroup security context
- Create test database and table
- Execute pod deletion test
- Verify data persistence

**Deliverables:**
- Updated StatefulSet with security context
- Test script for data insertion/verification
- Test execution report

### Phase 2: Multi-Replica Setup & Testing
**File:** `phase-02-multi-replica-isolation.md`
- Create PVs for pod-1 and pod-2
- Scale StatefulSet to 3 replicas
- Test data isolation between pods
- Verify independent lifecycle

**Deliverables:**
- 2 additional PV manifests
- Multi-pod test script
- Isolation validation report

### Phase 3: Documentation & Best Practices
**File:** `phase-03-documentation.md`
- Document safe patterns
- Create troubleshooting guide
- List anti-patterns to avoid
- Cleanup procedures

**Deliverables:**
- MySQL StatefulSet best practices doc
- Common pitfalls guide
- Cleanup scripts

## Technical Architecture

### Safe Pattern: StatefulSet with VolumeClaimTemplates

```yaml
StatefulSet Spec:
  volumeClaimTemplates:
    - metadata:
        name: data
      spec:
        accessModes: [ReadWriteOnce]
        storageClassName: kubeflow-storage
        resources:
          requests:
            storage: 20Gi

  template:
    spec:
      securityContext:
        fsGroup: 999  # MySQL UID/GID
      containers:
        - volumeMounts:
            - name: data
              mountPath: /var/lib/mysql
```

### Storage Topology (hostPath)

```
k8s-master-1 (node):
├── /data/mysql-statefulset     → mysql-statefulset-pv   → data-mysql-statefulset-0
├── /data/mysql-statefulset-1   → mysql-statefulset-pv-1 → data-mysql-statefulset-1
└── /data/mysql-statefulset-2   → mysql-statefulset-pv-2 → data-mysql-statefulset-2
```

**Node Affinity Required:**
- All PVs pinned to k8s-master-1 (hostPath constraint)
- Pods scheduled to same node via PVC binding

## Anti-Patterns to Avoid

❌ **NEVER DO THIS:**
1. Mount same PV to multiple MySQL pods → **DATA CORRUPTION**
2. Use RWX (ReadWriteMany) for MySQL data directory
3. Share `/var/lib/mysql` between pods
4. Delete PVCs before backing up data

✓ **ALWAYS DO THIS:**
1. Use VolumeClaimTemplates in StatefulSet
2. One dedicated PVC per MySQL pod
3. Set `persistentVolumeClaimRetentionPolicy: Retain`
4. Configure fsGroup for proper permissions

## Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|------------|
| PV creation on wrong node | Pod stuck pending | Verify nodeAffinity before apply |
| Data loss during testing | Medium | Use test database, backup production data |
| Resource exhaustion | Low | Monitor disk usage on k8s-master-1 |
| PVC stuck in pending | Medium | Pre-create PVs before scaling |

## Prerequisites

- [x] Existing MySQL StatefulSet in kubeflow namespace
- [x] kubectl access to cluster
- [x] Disk space on k8s-master-1: 60Gi available (3x20Gi PVs)
- [ ] Backup of current MySQL data (if production)
- [ ] mysql client installed in pods

## Success Metrics

1. **Data Persistence:** 100% data recovery after pod deletion
2. **Isolation:** 0 cross-pod data leakage
3. **Recovery Time:** Pod recreation < 2 minutes
4. **Storage Efficiency:** PVC reattachment without data copy

## Timeline Estimate

- Phase 1: 30 minutes (setup + single-pod test)
- Phase 2: 45 minutes (multi-replica setup + testing)
- Phase 3: 30 minutes (documentation)
- **Total:** ~2 hours

## Next Steps

1. Review this plan
2. Proceed to Phase 1: `phase-01-single-pod-persistence.md`
3. Execute tests sequentially
4. Document findings in each phase report

## References

- Kubernetes StatefulSet Docs: https://kubernetes.io/docs/concepts/workloads/controllers/statefulset/
- MySQL on Kubernetes Best Practices
- Current MySQL config: `/tmp/mysql-current-config.yaml`

---

**Plan Status:** ✅ READY
**Next Action:** Execute Phase 1
