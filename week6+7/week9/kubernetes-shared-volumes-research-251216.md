# Kubernetes Shared Volume Strategies Research Report
**Date**: 2025-12-16
**Context**: Kubeflow on Ubuntu 24.04, hostPath volumes with RWO mode

---

## 1. ACCESS MODES OVERVIEW

### ReadWriteOnce (RWO)
- Volume mounted read-write by **single node only**
- Multiple pods on **same node** can access concurrently
- **Use when**: Single database instance, data consistency critical, hostPath volumes
- **Limitation**: hostPath only supports RWO

### ReadOnlyMany (ROX)
- Multiple pods mount volume read-only simultaneously
- **Use when**: Static content distribution, configuration files, shared datasets
- Ensures data consistency across all nodes

### ReadWriteMany (RWX)
- Multiple pods on **multiple nodes** mount read-write concurrently
- **Use when**: Distributed file systems, shared application data across nodes
- **Storage backend dependent** - hostPath does NOT support RWX

**Key Decision Factor**: If single-node access sufficient, use RWO. If multi-node read/write required, must use RWX-capable storage backend.

---

## 2. RWX STORAGE SOLUTIONS FOR BARE METAL

### NFS (Network File System)
**Status**: Primary recommendation for 2025
- Very stable, mature NFS CSI driver
- Supports RWO, ROX, RWX access modes
- **Pros**: Simple setup, proven stability, wide compatibility
- **Cons**: NFS daemon not HA unless using Corosync/Pacemaker failover
- **Setup**: Requires external NFS server, then configure StorageClass with NFS provisioner

### CephFS
**Status**: Viable alternative for 2025
- POSIX-compliant file system on Ceph cluster
- Supports block (RBD), object (RGW), file (CephFS) storage
- **Pros**: Highly available, distributed, flexible
- **Cons**: Complex setup, higher resource overhead
- **Setup**: Deploy Ceph cluster, use Rook operator or Ceph CSI driver

### GlusterFS
**Status**: **DEPRECATED - DO NOT USE**
- Removed from Kubernetes v1.26 (deprecated v1.25)
- No longer supported in Kubernetes 1.34+

### Local-path-provisioner with hostPath
**Status**: RWO only - cannot provide RWX
- Suitable for single-node clusters or testing
- **Not viable** for multi-pod RWX requirements

### Longhorn / OpenEBS
**Status**: Maintenance mode - limited feature development
- Receiving patches/bug fixes only, not recommended for new deployments in 2025

**Recommendation**: Use NFS for simplicity, CephFS for production-grade HA.

---

## 3. DATABASE IMPLICATIONS - CRITICAL RISKS

### **DANGER: Multiple MySQL Pods on Same Volume**

**Data Corruption Risk**
- MySQL **NOT designed** for concurrent multi-instance access to same data directory
- File locking conflicts cause corruption when multiple pods write simultaneously
- **Result**: Database integrity compromised, potential total data loss

**Pod Failures**
- Second replica enters CrashLoopBackOff when attempting to mount locked volume
- Connection errors: "Can't connect to local MySQL server through socket"
- First pod locks database files, preventing second pod access

### **Why This Fails**
MySQL expects exclusive access to:
- InnoDB tablespace files
- Transaction logs (ib_logfile)
- Binary logs
- Socket files

Multiple instances writing to these files = guaranteed corruption.

### **Solutions - DO NOT Share Database Volumes**

**Option 1: ReadWriteOncePod (Kubernetes v1.29+)**
- Ensures storage accessible by **only one pod**
- Other pods from same deployment fail to mount
- Prevents accidental multi-pod access

**Option 2: StatefulSets (Recommended)**
- Each pod gets **unique PersistentVolume** via volumeClaimTemplates
- Stable pod identity, dedicated storage
- Data survives pod rescheduling to different nodes
- Use headless service (clusterIP: None)

**Option 3: MySQL Replication Architecture**
- Primary pod with RWO volume for writes
- Read replicas with separate volumes, data synced via MySQL replication
- **Note**: Kubernetes does NOT handle data replication - configure MySQL replication manually

**NEVER**: Use RWX volume for multiple MySQL pods expecting shared data directory.

---

## 4. TEST STRATEGIES FOR DATA PERSISTENCE

### Reclaim Policies
**Retain** (recommended for testing):
- PV keeps data after PVC deletion
- Allows manual inspection/recovery
- Must manually clean up PV

**Delete** (default for dynamic provisioning):
- PV deleted when PVC deleted
- Data lost - unsuitable for persistence testing

### Storage Object Protection
- PVCs in active use by pods cannot be deleted immediately
- Deletion postponed until pod releases PVC
- Prevents accidental data loss during pod operations

### Test Procedure

**Step 1: Write Test Data**
```bash
# Create pod, write data to PV
kubectl exec -it <pod> -- mysql -u root -p -e "CREATE DATABASE testdb; USE testdb; CREATE TABLE data(id INT); INSERT INTO data VALUES(1);"
```

**Step 2: Delete Pod (NOT PVC)**
```bash
kubectl delete pod <pod-name>
# StatefulSet/Deployment recreates pod automatically
```

**Step 3: Verify Data Persists**
```bash
kubectl exec -it <new-pod> -- mysql -u root -p -e "USE testdb; SELECT * FROM data;"
# Should return id=1
```

**Step 4: Delete Entire StatefulSet (Keep PVC)**
```bash
kubectl delete statefulset <sts-name>
# PVCs remain - critical for data persistence
```

**Step 5: Recreate StatefulSet**
```bash
kubectl apply -f statefulset.yaml
# New pods bind to existing PVCs, data intact
```

**Step 6: Test PVC Deletion (Optional - Data Loss)**
```bash
kubectl delete pvc <pvc-name>
# With Retain policy: PV remains, data recoverable
# With Delete policy: PV deleted, data lost
```

### Key Testing Insights
- **Pod deletion**: Data persists (PVC unchanged)
- **StatefulSet deletion**: PVCs survive, data safe
- **PVC deletion**: Depends on reclaimPolicy (Retain vs Delete)
- PV exists independently of pods - survives cluster changes

---

## 5. BEST PRACTICES

### Database Deployments
1. **Use StatefulSets**, never Deployments for databases
2. **One PV per database pod** via volumeClaimTemplates
3. **Headless service** for stable network identity
4. **ReadWriteOncePod** access mode if available (k8s v1.29+)
5. **Separate namespace** for database workloads
6. **Retain reclaim policy** for production data
7. **HashiCorp Vault** for secrets, not Kubernetes Secrets

### Storage Configuration
1. **Choose StorageClass carefully**: SSD for performance, HDD for capacity
2. **Set appropriate access mode**: RWO for databases, RWX only when necessary
3. **Test backup/restore** procedures before production
4. **Monitor storage usage** and set resource limits
5. **Use CSI drivers** over deprecated in-tree volume plugins

### Data Replication
- **Manual setup required**: Kubernetes StatefulSets do NOT handle database replication
- **MySQL**: Configure master-slave replication yourself
- **PostgreSQL**: Set up streaming replication separately
- **Operators recommended**: Use database-specific operators (MySQL Operator, Zalando Postgres Operator) for automated replication management

### StatefulSet Behavior
- Deleting pod: PVC retained, data safe
- Deleting StatefulSet: PVCs retained, data safe
- Replacement pods: Same name, same PVC, data preserved
- **Critical**: PVCs not auto-deleted, preventing accidental data loss

### Production Checklist (2025)
- ✅ Use Kubernetes 1.30+ for latest StatefulSet features
- ✅ Deploy database operators for automated management
- ✅ Implement monitoring (Prometheus/Grafana)
- ✅ Configure automated backups (Velero, database-native tools)
- ✅ Test disaster recovery procedures
- ✅ Document data sync/replication setup
- ✅ Use security policies (NetworkPolicies, PodSecurityStandards)

---

## SUMMARY FOR YOUR USE CASE

**Current Setup**: Kubeflow, Ubuntu 24.04, hostPath + RWO

### If Goal: Multiple Pods Access Same Database Volume
**Answer**: **DO NOT DO THIS** - will corrupt database

**Instead**:
- **Single database pod**: Keep RWO, use StatefulSet with 1 replica
- **Database HA**: Deploy MySQL replication (primary + replicas, each with own PV)
- **Shared file storage**: Deploy NFS server, use NFS-backed RWX PVs (NOT for database data directory)

### If Goal: Test Data Persistence on Pod Deletion
**Steps**:
1. Use StatefulSet with volumeClaimTemplate
2. Set reclaimPolicy: Retain in StorageClass
3. Follow test procedure in Section 4
4. Delete pod → verify data persists in new pod
5. Delete StatefulSet → PVC survives → recreate StatefulSet → data intact

### If Goal: Enable RWX for Non-Database Workloads
**Solution**: Deploy NFS
1. Install NFS server on Ubuntu 24.04: `apt install nfs-kernel-server`
2. Configure exports: `/etc/exports`
3. Install NFS CSI driver in cluster
4. Create StorageClass with NFS provisioner, accessModes: [ReadWriteMany]
5. Use for shared application data, NOT database directories

---

## UNRESOLVED QUESTIONS

1. **What is the actual use case for multiple pods accessing same volume?**
   - If database replication: Need MySQL replication setup, not shared volume
   - If shared application files: NFS viable
   - If testing: Clarify test objective (persistence vs multi-access)

2. **Kubeflow-specific requirements?**
   - Some Kubeflow components may need RWX for pipeline artifacts
   - Verify which components require shared storage

3. **Cluster size?**
   - Single-node: hostPath + RWO sufficient for most workloads
   - Multi-node: NFS required for RWX

---

## SOURCES

- [Understanding Kubernetes Volume Access Modes](https://medium.com/@babu.animela/understanding-kubernetes-volume-access-modes-rwo-rox-and-rwx-8859fc6712a4)
- [Kubernetes Persistent Volumes Documentation](https://kubernetes.io/docs/concepts/storage/persistent-volumes/)
- [PVC AccessModes Guide](https://zesty.co/finops-glossary/pvc-accessmodes-in-kubernetes/)
- [Clustered RWX Filesystems for Kubernetes](https://autoize.com/clustered-readwritemany-filesystems-for-kubernetes-persistent-volumes/)
- [Kubernetes Storage Options: NFS, Ceph, GlusterFS](https://dev.to/abhay_yt_52a8e72b213be229/kubernetes-storage-options-exploring-nfs-ceph-glusterfs-and-ebs-3bf9)
- [Kubernetes Storage Layers: Ceph vs Longhorn](https://oneuptime.com/blog/post/2025-11-27-choosing-kubernetes-storage-layers/view)
- [Multiple MySQL Pods Volume Mount Issue](https://github.com/kubernetes/kubernetes/issues/124691)
- [Ensuring Single Pod Access for Volumes](https://medium.com/@tabea.spahn/ensuring-single-pod-access-for-volumes-with-kubernetes-4df3e723c452)
- [To Run Database on Kubernetes - Google Cloud](https://cloud.google.com/blog/products/databases/to-run-or-not-to-run-a-database-on-kubernetes-what-to-consider)
- [Kubernetes Persistent Volumes Tutorial](https://spacelift.io/blog/kubernetes-persistent-volumes)
- [StatefulSets Documentation](https://kubernetes.io/docs/concepts/workloads/controllers/statefulset/)
- [Best Practices for Managing Stateful Workloads](https://www.clutchevents.co/resources/persistent-volumes-in-kubernetes-best-practices-for-managing-stateful-workloads)
- [StatefulSets & Persistent Storage](https://www.glukhov.org/post/2025/11/statefulsets-and-persistent-storage-in-kubernetes/)
