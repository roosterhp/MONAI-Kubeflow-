#!/bin/bash
set -e

NS="kubeflow"

echo "=========================================="
echo "Phase 2: Multi-Replica Isolation Test"
echo "=========================================="

# Get MySQL password
export MYSQL_ROOT_PASSWORD=$(kubectl get secret mysql-secret -n $NS -o jsonpath='{.data.root-password}' | base64 -d)

# Step 1: Create PVs
echo ""
echo "=== Step 1: Creating PVs ==="
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

echo "PVs created. Current status:"
kubectl get pv | grep mysql-statefulset

# Step 2: Create directories
echo ""
echo "=== Step 2: Creating directories on node ==="
ssh k8s-master-1 "mkdir -p /data/mysql-statefulset-1 /data/mysql-statefulset-2 && chown -R 999:999 /data/mysql-statefulset-1 /data/mysql-statefulset-2"
echo "Directories created with MySQL permissions"

# Step 3: Scale StatefulSet
echo ""
echo "=== Step 3: Scaling to 3 replicas ==="
kubectl scale statefulset mysql-statefulset -n $NS --replicas=3
echo "Waiting for all pods to be ready (this may take 2-3 minutes)..."
kubectl wait --for=condition=ready pod -l app=mysql-statefulset -n $NS --timeout=600s
echo "All pods ready"

# Verify PVC bindings
echo ""
echo "PVC Bindings:"
kubectl get pvc -n $NS | grep mysql-statefulset

# Step 4: Insert unique data per pod
echo ""
echo "=== Step 4: Inserting unique data in each pod ==="
for i in 0 1 2; do
  echo "Inserting data in pod-$i..."
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

echo "Data inserted in all pods"

# Step 5: Verify isolation
echo ""
echo "=== Step 5: Verifying data isolation ==="
ISOLATION_OK=true
for i in 0 1 2; do
  DB_COUNT=$(kubectl exec mysql-statefulset-$i -n $NS -- mysql -uroot -p"$MYSQL_ROOT_PASSWORD" \
    -e "SHOW DATABASES;" -N -s | grep -c pod_ || true)

  if [ "$DB_COUNT" -eq 1 ]; then
    echo "✓ Pod-$i: Only 1 pod database (isolation OK)"
  else
    echo "✗ Pod-$i: Found $DB_COUNT pod databases (isolation FAILED)"
    ISOLATION_OK=false
  fi

  # Show which database exists
  DB_NAME=$(kubectl exec mysql-statefulset-$i -n $NS -- mysql -uroot -p"$MYSQL_ROOT_PASSWORD" \
    -e "SHOW DATABASES;" -N -s | grep pod_)
  echo "  Database in pod-$i: $DB_NAME"
done

if [ "$ISOLATION_OK" = false ]; then
  echo "✗ Data isolation test FAILED"
  exit 1
fi

# Step 6: Test pod-1 deletion
echo ""
echo "=== Step 6: Testing pod-1 deletion and recreation ==="
echo "Deleting pod-1..."
kubectl delete pod mysql-statefulset-1 -n $NS
kubectl wait --for=condition=ready pod/mysql-statefulset-1 -n $NS --timeout=300s
echo "Pod-1 recreated"

# Verify pod-1 data persisted
COUNT=$(kubectl exec mysql-statefulset-1 -n $NS -- mysql -uroot -p"$MYSQL_ROOT_PASSWORD" \
  -e "USE pod_1_data; SELECT COUNT(*) FROM isolation_test;" -N -s)
if [ "$COUNT" -eq 2 ]; then
  echo "✓ Pod-1 data persisted after recreation (2 rows found)"
else
  echo "✗ Pod-1 data lost (found $COUNT rows, expected 2)"
  exit 1
fi

# Verify pods 0 and 2 unaffected
echo ""
echo "Verifying pods 0 and 2 unaffected by pod-1 deletion..."
for i in 0 2; do
  COUNT=$(kubectl exec mysql-statefulset-$i -n $NS -- mysql -uroot -p"$MYSQL_ROOT_PASSWORD" \
    -e "USE pod_${i}_data; SELECT COUNT(*) FROM isolation_test;" -N -s)
  if [ "$COUNT" -eq 2 ]; then
    echo "✓ Pod-$i data unaffected"
  else
    echo "✗ Pod-$i data corrupted (found $COUNT rows, expected 2)"
    exit 1
  fi
done

echo ""
echo "=========================================="
echo "Phase 2 Test PASSED"
echo "=========================================="
echo "Summary:"
echo "  - 3 pods deployed: ✓"
echo "  - 3 PVCs created: ✓"
echo "  - Data isolation: ✓"
echo "  - Pod-1 recreation: ✓"
echo "  - Data persistence: ✓"
echo "  - Pods 0,2 unaffected: ✓"
echo "=========================================="
echo ""
echo "Current state:"
kubectl get pods -n $NS -l app=mysql-statefulset
echo ""
kubectl get pvc -n $NS | grep mysql-statefulset
