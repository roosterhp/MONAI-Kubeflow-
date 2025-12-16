#!/bin/bash
set -e

NS="kubeflow"
POD="mysql-statefulset-0"
PVC="data-mysql-statefulset-0"

echo "=========================================="
echo "Phase 1: Single-Pod Data Persistence Test"
echo "=========================================="

# Get MySQL password
export MYSQL_ROOT_PASSWORD=$(kubectl get secret mysql-secret -n $NS -o jsonpath='{.data.root-password}' | base64 -d)

# Step 1: Insert test data
echo ""
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
echo ""
CHECKSUM=$(kubectl exec $POD -n $NS -- mysql -uroot -p"$MYSQL_ROOT_PASSWORD" test_persistence \
  -e "SELECT MD5(GROUP_CONCAT(data ORDER BY id)) FROM volume_test;" -N -s 2>/dev/null)
echo "Original checksum: $CHECKSUM"

# Step 3: Record PVC UID
PVC_UID=$(kubectl get pvc $PVC -n $NS -o jsonpath='{.metadata.uid}')
echo "PVC UID: $PVC_UID"

# Step 4: Delete pod
echo ""
echo "=== Step 2: Deleting pod ==="
DELETION_TIME=$(date +%s)
kubectl delete pod $POD -n $NS
echo "Waiting for pod recreation..."

# Step 5: Wait for ready
kubectl wait --for=condition=ready pod/$POD -n $NS --timeout=300s
RECREATION_TIME=$(date +%s)
DOWNTIME=$((RECREATION_TIME - DELETION_TIME))
echo "Pod recreated successfully in ${DOWNTIME}s"

# Step 6: Verify PVC unchanged
NEW_PVC_UID=$(kubectl get pvc $PVC -n $NS -o jsonpath='{.metadata.uid}')
if [ "$PVC_UID" = "$NEW_PVC_UID" ]; then
    echo "✓ PVC UID unchanged: $PVC_UID"
else
    echo "✗ FAIL: PVC UID changed!"
    echo "  Original: $PVC_UID"
    echo "  New: $NEW_PVC_UID"
    exit 1
fi

# Step 7: Wait for MySQL ready
echo ""
echo "=== Step 3: Verifying data persistence ==="
sleep 10
kubectl exec $POD -n $NS -- mysqladmin ping -h localhost > /dev/null 2>&1

# Step 8: Verify data
echo "Data after recreation:"
kubectl exec $POD -n $NS -- mysql -uroot -p"$MYSQL_ROOT_PASSWORD" test_persistence \
  -e "SELECT * FROM volume_test;" 2>/dev/null

NEW_CHECKSUM=$(kubectl exec $POD -n $NS -- mysql -uroot -p"$MYSQL_ROOT_PASSWORD" test_persistence \
  -e "SELECT MD5(GROUP_CONCAT(data ORDER BY id)) FROM volume_test;" -N -s 2>/dev/null)

echo ""
if [ "$CHECKSUM" = "$NEW_CHECKSUM" ]; then
    echo "✓ SUCCESS: Data checksum matches!"
    echo "  Checksum: $CHECKSUM"
else
    echo "✗ FAIL: Data checksum mismatch!"
    echo "  Original: $CHECKSUM"
    echo "  New: $NEW_CHECKSUM"
    exit 1
fi

echo ""
echo "=========================================="
echo "Phase 1 Test PASSED"
echo "=========================================="
echo "Summary:"
echo "  - Pod recreation time: ${DOWNTIME}s"
echo "  - PVC reattached: ✓"
echo "  - Data persisted: ✓"
echo "  - Data checksum: ✓"
echo "=========================================="
