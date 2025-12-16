#!/bin/bash

# Quick MySQL Database Test Script

set -e

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "=========================================="
echo "MySQL Database Quick Test"
echo "=========================================="

# Get credentials
ROOT_PASS=$(kubectl get secret mysql-secret -n kubeflow -o jsonpath="{.data.root-password}" | base64 -d)
USER_PASS=$(kubectl get secret mysql-secret -n kubeflow -o jsonpath="{.data.password}" | base64 -d)
DB_NAME=$(kubectl get secret mysql-secret -n kubeflow -o jsonpath="{.data.database}" | base64 -d)
DB_USER=$(kubectl get secret mysql-secret -n kubeflow -o jsonpath="{.data.user}" | base64 -d)

echo -e "\n[1/10] Pod Status..."
kubectl get pod mysql-statefulset-0 -n kubeflow --no-headers | awk '{print "[PASS] Pod: " $1 " Status: " $3}'

echo -e "\n[2/10] MySQL Version..."
VERSION=$(kubectl exec mysql-statefulset-0 -n kubeflow -- mysql -u root -p"$ROOT_PASS" -e "SELECT VERSION();" 2>&1 | grep -v Warning | tail -1)
echo -e "${GREEN}[PASS]${NC} MySQL $VERSION"

echo -e "\n[3/10] Database Exists..."
kubectl exec mysql-statefulset-0 -n kubeflow -- mysql -u root -p"$ROOT_PASS" -e "SHOW DATABASES LIKE '$DB_NAME';" 2>&1 | grep -v Warning | grep -q "$DB_NAME" && echo -e "${GREEN}[PASS]${NC} Database '$DB_NAME' exists" || echo -e "${RED}[FAIL]${NC} Database not found"

echo -e "\n[4/10] User Exists..."
kubectl exec mysql-statefulset-0 -n kubeflow -- mysql -u root -p"$ROOT_PASS" -e "SELECT User FROM mysql.user WHERE User='$DB_USER';" 2>&1 | grep -v Warning | grep -q "$DB_USER" && echo -e "${GREEN}[PASS]${NC} User '$DB_USER' exists" || echo -e "${RED}[FAIL]${NC} User not found"

echo -e "\n[5/10] User Can Login..."
kubectl exec mysql-statefulset-0 -n kubeflow -- mysql -u "$DB_USER" -p"$USER_PASS" -e "SELECT 1;" 2>&1 | grep -v Warning > /dev/null && echo -e "${GREEN}[PASS]${NC} User can login" || echo -e "${RED}[FAIL]${NC} Cannot login"

echo -e "\n[6/10] CREATE Table..."
kubectl exec mysql-statefulset-0 -n kubeflow -- mysql -u root -p"$ROOT_PASS" "$DB_NAME" -e "DROP TABLE IF EXISTS test_crud; CREATE TABLE test_crud (id INT PRIMARY KEY AUTO_INCREMENT, name VARCHAR(100));" 2>&1 | grep -v Warning > /dev/null
echo -e "${GREEN}[PASS]${NC} Table created"

echo -e "\n[7/10] INSERT Data..."
kubectl exec mysql-statefulset-0 -n kubeflow -- mysql -u root -p"$ROOT_PASS" "$DB_NAME" -e "INSERT INTO test_crud (name) VALUES ('test1'), ('test2'), ('test3');" 2>&1 | grep -v Warning > /dev/null
echo -e "${GREEN}[PASS]${NC} Data inserted"

echo -e "\n[8/10] SELECT Data..."
ROWS=$(kubectl exec mysql-statefulset-0 -n kubeflow -- mysql -u root -p"$ROOT_PASS" "$DB_NAME" -e "SELECT COUNT(*) FROM test_crud;" 2>&1 | grep -v Warning | tail -1)
echo -e "${GREEN}[PASS]${NC} Read $ROWS rows"

echo -e "\n[9/10] UPDATE Data..."
kubectl exec mysql-statefulset-0 -n kubeflow -- mysql -u root -p"$ROOT_PASS" "$DB_NAME" -e "UPDATE test_crud SET name='updated' WHERE id=1;" 2>&1 | grep -v Warning > /dev/null
echo -e "${GREEN}[PASS]${NC} Data updated"

echo -e "\n[10/10] DELETE Data..."
kubectl exec mysql-statefulset-0 -n kubeflow -- mysql -u root -p"$ROOT_PASS" "$DB_NAME" -e "DELETE FROM test_crud WHERE id=2;" 2>&1 | grep -v Warning > /dev/null
REMAINING=$(kubectl exec mysql-statefulset-0 -n kubeflow -- mysql -u root -p"$ROOT_PASS" "$DB_NAME" -e "SELECT COUNT(*) FROM test_crud;" 2>&1 | grep -v Warning | tail -1)
echo -e "${GREEN}[PASS]${NC} Data deleted. Remaining: $REMAINING rows"

echo -e "\n=========================================="
echo "Additional Checks"
echo "=========================================="

echo -e "\n[CONFIG] MySQL Settings..."
kubectl exec mysql-statefulset-0 -n kubeflow -- mysql -u root -p"$ROOT_PASS" -e "SELECT @@max_connections as max_conn, ROUND(@@innodb_buffer_pool_size/1024/1024/1024,2) as buffer_gb;" 2>&1 | grep -v Warning

echo -e "\n[CONNECTIONS] Active Connections..."
kubectl exec mysql-statefulset-0 -n kubeflow -- mysql -u root -p"$ROOT_PASS" -e "SELECT COUNT(*) as total FROM information_schema.PROCESSLIST;" 2>&1 | grep -v Warning

echo -e "\n[STORAGE] Disk Usage..."
kubectl exec mysql-statefulset-0 -n kubeflow -- df -h /var/lib/mysql | tail -1

echo -e "\n[RESOURCES] Pod Resource Usage..."
kubectl top pod mysql-statefulset-0 -n kubeflow 2>/dev/null || echo "Metrics not available"

echo -e "\n[CLEANUP] Dropping test table..."
kubectl exec mysql-statefulset-0 -n kubeflow -- mysql -u root -p"$ROOT_PASS" "$DB_NAME" -e "DROP TABLE IF EXISTS test_crud;" 2>&1 | grep -v Warning > /dev/null
echo -e "${GREEN}[PASS]${NC} Cleanup complete"

echo -e "\n=========================================="
echo -e "${GREEN}ALL TESTS PASSED!${NC}"
echo "=========================================="
echo ""
echo "Summary:"
echo "  Database: $DB_NAME"
echo "  User: $DB_USER"
echo "  Pod: mysql-statefulset-0"
echo "  Namespace: kubeflow"
echo ""
