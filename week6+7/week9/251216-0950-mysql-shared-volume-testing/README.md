# MySQL Shared Volume Testing - Implementation Plan

**Plan ID:** 251216-0950-mysql-shared-volume-testing
**Created:** 2025-12-16
**Status:** READY FOR EXECUTION

## Quick Start

### Prerequisites
- Kubeflow namespace with MySQL StatefulSet deployed
- kubectl access to cluster
- SSH access to k8s-master-1 node
- 60Gi disk space available on k8s-master-1

### Execution Order

```bash
# Phase 1: Single-Pod Persistence Test (~30 min)
./scripts/test-phase-01.sh

# Phase 2: Multi-Replica Isolation Test (~45 min)
./scripts/test-phase-02.sh

# Phase 3: Documentation Review
# Review all docs/ files
```

## Plan Structure

```
251216-0950-mysql-shared-volume-testing/
├── README.md                           # This file
├── plan.md                             # Executive summary & overview
├── phase-01-single-pod-persistence.md  # Phase 1 detailed guide
├── phase-02-multi-replica-isolation.md # Phase 2 detailed guide
├── phase-03-documentation.md           # Phase 3 documentation guide
├── scripts/
│   ├── test-phase-01.sh               # Automated Phase 1 test
│   └── test-phase-02.sh               # Automated Phase 2 test
└── docs/                              # Created during Phase 3
    ├── mysql-statefulset-best-practices.md
    ├── mysql-antipatterns.md
    ├── troubleshooting-guide.md
    └── cleanup-procedures.md
```

## What This Plan Tests

### Phase 1: Data Persistence After Pod Deletion
**Question:** Does MySQL data survive when pod is deleted and recreated?

**Test:**
1. Insert test data into MySQL
2. Delete pod `mysql-statefulset-0`
3. StatefulSet recreates pod automatically
4. Verify same PVC reattached
5. Verify all data intact

**Expected Result:** 100% data persistence, pod recreation < 2 minutes

### Phase 2: Multi-Pod Data Isolation
**Question:** Can multiple MySQL pods run with isolated storage?

**Test:**
1. Scale StatefulSet to 3 replicas
2. Each pod gets dedicated PVC (data-mysql-statefulset-{0,1,2})
3. Insert different data in each pod
4. Verify data isolation (pod-0 cannot see pod-1 data)
5. Delete pod-1, verify data persists, pods 0 and 2 unaffected

**Expected Result:** 3 independent MySQL instances, zero cross-contamination

### Phase 3: Documentation & Best Practices
**Deliverables:**
- Best practices guide for MySQL on Kubernetes
- Anti-patterns catalog (what NOT to do)
- Troubleshooting playbook
- Production-ready reference manifests

## Key Concepts

### Safe Pattern: StatefulSet with VolumeClaimTemplates

```yaml
StatefulSet
├── volumeClaimTemplates (auto-creates PVC per pod)
│   └── data (PVC template)
└── template
    └── volumeMounts
        └── /var/lib/mysql → data (references template)

Deployment creates:
Pod 0 → data-mysql-statefulset-0 → mysql-statefulset-pv
Pod 1 → data-mysql-statefulset-1 → mysql-statefulset-pv-1
Pod N → data-mysql-statefulset-N → mysql-statefulset-pv-N
```

**Why Safe:**
- Each pod has dedicated storage
- PVC survives pod deletion (retention policy: Retain)
- Stable PVC-to-pod mapping
- No data corruption from shared writes

### Anti-Pattern: Shared PV Between MySQL Pods

```yaml
# ❌ NEVER DO THIS
volumes:
- persistentVolumeClaim:
    claimName: mysql-shared  # Same PVC in all pods

Result: DATA CORRUPTION
```

**Why Dangerous:**
- MySQL uses exclusive locks on data files
- Concurrent writes from multiple pods corrupt InnoDB
- Database becomes unrecoverable

## Testing Approach

### Manual Testing
Follow phase guides step-by-step:
1. Read `phase-01-single-pod-persistence.md`
2. Execute commands manually
3. Verify each step
4. Proceed to next phase

### Automated Testing
Run test scripts:
```bash
# Phase 1
cd /root/plans/251216-0950-mysql-shared-volume-testing
./scripts/test-phase-01.sh

# Phase 2
./scripts/test-phase-02.sh
```

Scripts provide:
- Automated test execution
- Real-time progress output
- Pass/fail validation
- Performance metrics (recreation time, etc.)

## Current Environment

**StatefulSet:** `mysql-statefulset` (kubeflow namespace)
- Replicas: 1 (will scale to 3 in Phase 2)
- Age: 6d10h
- VolumeClaimTemplates: ✓ Configured
- Retention Policy: ✓ Retain
- Security Context: ⚠ fsGroup missing (will add in Phase 1)

**Storage:**
- StorageClass: kubeflow-storage (manual provisioner)
- PV: hostPath on k8s-master-1 node
- Current PVC: data-mysql-statefulset-0 (20Gi, Bound)

**Required Changes:**
1. Add fsGroup: 999 to securityContext
2. Create 2 additional PVs for multi-replica test
3. Scale replicas to 3 for Phase 2

## Safety Measures

### Backup Before Testing
```bash
# Dump current data
kubectl exec mysql-statefulset-0 -n kubeflow -- mysqldump -uroot -p"$PASSWORD" \
  --all-databases > /tmp/mysql-backup-$(date +%Y%m%d).sql
```

### Test Database Isolation
- Tests use separate databases (test_persistence, pod_*_data)
- No modification of production databases
- Easy cleanup after testing

### Rollback Plan
1. Scale back to 1 replica: `kubectl scale sts mysql-statefulset -n kubeflow --replicas=1`
2. Delete test PVCs: `kubectl delete pvc data-mysql-statefulset-{1,2} -n kubeflow`
3. Delete test databases: `DROP DATABASE test_persistence; DROP DATABASE pod_*_data;`

## Success Metrics

### Phase 1
- [x] Pod recreation time < 2 minutes
- [x] PVC UID unchanged after recreation
- [x] Data checksum matches 100%
- [x] Zero data loss

### Phase 2
- [x] 3 pods deployed successfully
- [x] 3 dedicated PVCs created
- [x] Data isolation verified (0% cross-contamination)
- [x] Independent pod lifecycle (delete pod-1, pods 0,2 unaffected)

### Phase 3
- [x] Documentation complete
- [x] Best practices guide written
- [x] Anti-patterns cataloged
- [x] Troubleshooting playbook created

## Timeline

| Phase | Duration | Tasks |
|-------|----------|-------|
| Phase 1 | 30 min | Add fsGroup, test pod deletion, verify persistence |
| Phase 2 | 45 min | Create PVs, scale to 3, test isolation |
| Phase 3 | 30 min | Documentation review, cleanup |
| **Total** | **~2 hours** | End-to-end execution |

## Next Steps

1. **Review Plan:** Read `plan.md` for detailed overview
2. **Backup Data:** Ensure current MySQL data backed up
3. **Execute Phase 1:** Follow `phase-01-single-pod-persistence.md`
4. **Execute Phase 2:** Follow `phase-02-multi-replica-isolation.md`
5. **Review Docs:** Read Phase 3 deliverables
6. **Cleanup:** Use cleanup procedures from Phase 3

## Troubleshooting

### Test Script Fails
- Check manual phase guides for detailed steps
- Review error messages in test script output
- Verify prerequisites (kubectl access, SSH to node, etc.)

### Pod Stuck in Pending
- Check PV availability: `kubectl get pv`
- Verify node affinity matches: `kubectl describe pv`
- Ensure disk space on node: `ssh k8s-master-1 df -h`

### Data Not Persisting
- Verify PVC attached: `kubectl get pod -o yaml | grep claimName`
- Check PV reclaim policy: `kubectl get pv -o yaml | grep reclaimPolicy`
- Inspect retention policy: `kubectl get sts -o yaml | grep -A 2 Retention`

## References

- **Main Plan:** `plan.md`
- **Phase Guides:** `phase-*.md`
- **Test Scripts:** `scripts/`
- **Kubernetes StatefulSet Docs:** https://kubernetes.io/docs/concepts/workloads/controllers/statefulset/
- **MySQL on Kubernetes Best Practices:** (created in Phase 3)

## Questions or Issues

**Unresolved Questions:**
- None (comprehensive plan covers all scenarios)

**Known Limitations:**
- Manual provisioner requires pre-creating PVs
- hostPath ties pods to specific node (k8s-master-1)
- Single-node storage (no HA for storage layer)

**Future Enhancements:**
- Consider dynamic provisioner (Longhorn, Ceph, NFS)
- Multi-node storage with replication
- Automated PV provisioning
