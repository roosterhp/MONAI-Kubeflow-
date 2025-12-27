#!/bin/bash
# Simple MySQL Database Test

echo "=========================================="
echo "MySQL Database Test"
echo "=========================================="

# Get password
PASS=$(kubectl get secret mysql-secret -n kubeflow -o jsonpath="{.data.root-password}" | base64 -d)
USER_PASS=$(kubectl get secret mysql-secret -n kubeflow -o jsonpath="{.data.password}" | base64 -d)

# Test 1: Pod Running
echo ""
echo "[1/10] Pod Status..."
kubectl get pod mysql-statefulset-0 -n kubeflow | grep Running && echo "[PASS]" || echo "[FAIL]"

# Test 2: MySQL Version
echo ""
echo "[2/10] MySQL Connectivity..."
kubectl exec mysql-statefulset-0 -n kubeflow -- mysql -u root -p"$PASS" -e "SELECT VERSION() as version;" 2>&1 | grep -v Warning

# Test 3: Show Databases
echo ""
echo "[3/10] Show Databases..."
kubectl exec mysql-statefulset-0 -n kubeflow -- mysql -u root -p"$PASS" -e "SHOW DATABASES;" 2>&1 | grep -v Warning

# Test 4: Check User
echo ""
echo "[4/10] Check User 'kubeflow'..."
kubectl exec mysql-statefulset-0 -n kubeflow -- mysql -u root -p"$PASS" -e "SELECT User, Host FROM mysql.user WHERE User='kubeflow';" 2>&1 | grep -v Warning

# Test 5: User Can Login
echo ""
echo "[5/10] Test User Login..."
kubectl exec mysql-statefulset-0 -n kubeflow -- mysql -u kubeflow -p"$USER_PASS" -e "SELECT USER() as current_user;" 2>&1 | grep -v Warning

# Test 6-10: CRUD Operations
echo ""
echo "[6/10] CREATE Table..."
kubectl exec mysql-statefulset-0 -n kubeflow -- mysql -u root -p"$PASS" kubeflow_db -e "CREATE TABLE IF NOT EXISTS test_health (id INT PRIMARY KEY AUTO_INCREMENT, name VARCHAR(50));" 2>&1 | grep -v Warning
echo "[DONE]"

echo ""
echo "[7/10] INSERT Data..."
kubectl exec mysql-statefulset-0 -n kubeflow -- mysql -u root -p"$PASS" kubeflow_db -e "INSERT INTO test_health (name) VALUES ('test1'), ('test2'), ('test3');" 2>&1 | grep -v Warning
echo "[DONE]"

echo ""
echo "[8/10] SELECT Data..."
kubectl exec mysql-statefulset-0 -n kubeflow -- mysql -u root -p"$PASS" kubeflow_db -e "SELECT * FROM test_health;" 2>&1 | grep -v Warning

echo ""
echo "[9/10] UPDATE Data..."
kubectl exec mysql-statefulset-0 -n kubeflow -- mysql -u root -p"$PASS" kubeflow_db -e "UPDATE test_health SET name='updated' WHERE id=1; SELECT * FROM test_health WHERE id=1;" 2>&1 | grep -v Warning

echo ""
echo "[10/10] DELETE Data..."
kubectl exec mysql-statefulset-0 -n kubeflow -- mysql -u root -p"$PASS" kubeflow_db -e "DELETE FROM test_health WHERE id=2; SELECT COUNT(*) as remaining FROM test_health;" 2>&1 | grep -v Warning

# Additional Info
echo ""
echo "=========================================="
echo "Additional Information"
echo "=========================================="

echo ""
echo "MySQL Configuration:"
kubectl exec mysql-statefulset-0 -n kubeflow -- mysql -u root -p"$PASS" -e "SELECT @@max_connections, @@innodb_buffer_pool_size/1024/1024/1024 as buffer_gb;" 2>&1 | grep -v Warning

echo ""
echo "Active Connections:"
kubectl exec mysql-statefulset-0 -n kubeflow -- mysql -u root -p"$PASS" -e "SELECT COUNT(*) as total_connections FROM information_schema.PROCESSLIST;" 2>&1 | grep -v Warning

echo ""
echo "Storage Usage:"
kubectl exec mysql-statefulset-0 -n kubeflow -- df -h /var/lib/mysql

echo ""
echo "Resource Usage:"
kubectl top pod mysql-statefulset-0 -n kubeflow 2>/dev/null || echo "Metrics not available"

echo ""
echo "=========================================="
echo "Test Complete!"
echo "=========================================="
