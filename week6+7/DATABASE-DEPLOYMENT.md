# Database StatefulSet Deployment Guide

## Tổng quan

Hướng dẫn deploy MySQL bằng StatefulSet và test concurrent connections từ nhiều app pods.

## Kiến trúc

```
┌─────────────────────────────────────────────┐
│        Application Layer (Scalable)         │
│  [App Pod 1] [App Pod 2] ... [App Pod 10]  │
│  Connection Pool: 10 base + 5 overflow      │
└──────────┬──────────┬──────────┬────────────┘
           │          │          │
           └──────────┼──────────┘
                      │
        ┌─────────────▼─────────────┐
        │  mysql-statefulset-service│  (ClusterIP)
        │  10.233.x.x:3306          │
        └─────────────┬─────────────┘
                      │
        ┌─────────────▼─────────────┐
        │  MySQL StatefulSet        │
        │  mysql-statefulset-0      │
        │  + Persistent Volume (20Gi)│
        └───────────────────────────┘
```

---

## Files

| File | Mô tả |
|------|-------|
| `mysql-secret.yaml` | MySQL credentials (password, user, database) |
| `mysql-configmap.yaml` | MySQL config (max_connections, pool settings) |
| `mysql-statefulset.yaml` | StatefulSet + Service + PVC |
| `test-app-deployment.yaml` | Test app với connection pooling |
| `test-database-load.sh` | Script test concurrent connections |

---

## Bước 1: Deploy MySQL StatefulSet

### 1.1. Apply configs

```bash
cd /root/MONAI-Kubeflow-/week6+7

# Apply theo thứ tự
kubectl apply -f mysql-secret.yaml
kubectl apply -f mysql-configmap.yaml
kubectl apply -f mysql-statefulset.yaml
```

### 1.2. Verify deployment

```bash
# Check StatefulSet
kubectl get statefulset -n kubeflow

# Check pods
kubectl get pods -n kubeflow | grep mysql-statefulset

# Check services
kubectl get svc -n kubeflow | grep mysql

# Check PVC
kubectl get pvc -n kubeflow | grep mysql
```

**Expected output:**
```
statefulset.apps/mysql-statefulset   1/1     45s
mysql-statefulset-0                  1/1     Running
mysql-headless                       ClusterIP   None
mysql-statefulset-service            ClusterIP   10.233.x.x
data-mysql-statefulset-0             Bound
```

### 1.3. Wait for MySQL to be ready

```bash
# Wait for pod to be ready
kubectl wait --for=condition=ready pod/mysql-statefulset-0 -n kubeflow --timeout=180s

# Check logs
kubectl logs -n kubeflow mysql-statefulset-0 --tail=50
```

### 1.4. Test MySQL connection

```bash
# Get MySQL password
MYSQL_PASSWORD=$(kubectl get secret mysql-secret -n kubeflow -o jsonpath='{.data.password}' | base64 -d)

# Connect to MySQL
kubectl exec -it mysql-statefulset-0 -n kubeflow -- mysql -uroot -p$MYSQL_PASSWORD -e "SELECT VERSION();"

# Check max_connections setting
kubectl exec -it mysql-statefulset-0 -n kubeflow -- mysql -uroot -p$MYSQL_PASSWORD -e "SHOW VARIABLES LIKE 'max_connections';"
```

**Expected output:**
```
max_connections | 500
```

---

## Bước 2: Deploy Test Application

### 2.1. Deploy app

```bash
kubectl apply -f test-app-deployment.yaml
```

### 2.2. Verify app pods

```bash
# Check deployment
kubectl get deployment mysql-test-app -n kubeflow

# Check pods
kubectl get pods -n kubeflow -l app=mysql-test-app

# Check logs from one pod
POD=$(kubectl get pods -n kubeflow -l app=mysql-test-app -o jsonpath='{.items[0].metadata.name}')
kubectl logs -n kubeflow $POD --tail=50
```

**Expected logs:**
```
=== MySQL Connection Pool Test ===
Host: mysql-statefulset-service.kubeflow.svc.cluster.local:3306
Database: kubeflow_db
Pool Size: 10
Max Overflow: 5
Pod: mysql-test-app-xxxxx

Connected to MySQL successfully!
Test table created

Starting continuous connection test...
[HH:MM:SS] Requests: 10 | Pool: 3/10 | Overflow: 0 | DB Rows: 50 | Unique Pods: 5
```

---

## Bước 3: Test Concurrent Connections

### 3.1. Scale app pods

```bash
# Scale to 10 pods
kubectl scale deployment mysql-test-app -n kubeflow --replicas=10

# Wait for pods
kubectl wait --for=condition=ready pod -l app=mysql-test-app -n kubeflow --timeout=180s
```

### 3.2. Monitor database connections

```bash
# Run load test script
chmod +x test-database-load.sh
./test-database-load.sh
```

**Expected output:**
```
=== Database Load Test Monitor ===
Time: 2025-12-09 15:30:00

--- App Pods ---
Running         : 10

--- MySQL Pod ---
Status: Running | Restarts: 0 | Age: 5m

=== Database Connection Stats ===
total_connections | idle_connections | active_connections | app_connections
105               | 95               | 10                 | 100

--- MySQL Resource Usage ---
NAME                  CPU(cores)   MEMORY(bytes)
mysql-statefulset-0   450m         1800Mi

--- Connection Pool Info ---
Expected connections: 10 pods × 10 pool_size = 100 connections
Max possible: 10 pods × (10 + 5 overflow) = 150 connections
```

### 3.3. Manual monitoring commands

```bash
# Check connections
kubectl exec -n kubeflow mysql-statefulset-0 -- \
  mysql -uroot -p$(kubectl get secret mysql-secret -n kubeflow -o jsonpath='{.data.root-password}' | base64 -d) \
  -e "SELECT COUNT(*) FROM information_schema.processlist;"

# Show connection details
kubectl exec -n kubeflow mysql-statefulset-0 -- \
  mysql -uroot -p$(kubectl get secret mysql-secret -n kubeflow -o jsonpath='{.data.root-password}' | base64 -d) \
  -e "SHOW PROCESSLIST;"

# Check resource usage
kubectl top pod mysql-statefulset-0 -n kubeflow
```

---

## Bước 4: Test với nhiều pods

### 4.1. Scale to 20 pods

```bash
kubectl scale deployment mysql-test-app -n kubeflow --replicas=20
```

**Expected connections:**
```
20 pods × 10 pool_size = 200 active connections
Max possible: 20 × 15 = 300 connections
```

### 4.2. Scale to 30 pods

```bash
kubectl scale deployment mysql-test-app -n kubeflow --replicas=30
```

**Expected connections:**
```
30 pods × 10 pool_size = 300 active connections
Max possible: 30 × 15 = 450 connections
```

### 4.3. Monitor performance

```bash
# Watch connections realtime
watch -n 2 "kubectl exec -n kubeflow mysql-statefulset-0 -- mysql -uroot -p\$(kubectl get secret mysql-secret -n kubeflow -o jsonpath='{.data.root-password}' | base64 -d) -e 'SELECT COUNT(*) FROM information_schema.processlist;' 2>/dev/null"

# Watch resource usage
watch -n 2 "kubectl top pod mysql-statefulset-0 -n kubeflow"
```

---

## Test Results Expected

| App Pods | Expected Connections | Max Connections | MySQL CPU | MySQL Memory |
|----------|---------------------|-----------------|-----------|--------------|
| 5        | 50                  | 75              | ~200m     | ~1Gi         |
| 10       | 100                 | 150             | ~400m     | ~1.5Gi       |
| 20       | 200                 | 300             | ~800m     | ~2Gi         |
| 30       | 300                 | 450             | ~1200m    | ~2.5Gi       |

**Note:** MySQL max_connections = 500, vậy tối đa có thể chạy ~30-35 app pods trước khi hit limit.

---

## Troubleshooting

### Problem 1: Pod pending (PVC not bound)

```bash
# Check storage class
kubectl get sc

# If local-path not available, change storageClassName in mysql-statefulset.yaml
# Or use default storage class
kubectl patch storageclass local-path -p '{"metadata": {"annotations":{"storageclass.kubernetes.io/is-default-class":"true"}}}'
```

### Problem 2: Too many connections error

```bash
# Check current connections
kubectl exec -n kubeflow mysql-statefulset-0 -- mysql -uroot -p$MYSQL_PASSWORD -e "SHOW STATUS LIKE 'Threads_connected';"

# Increase max_connections in mysql-configmap.yaml
# Then restart MySQL:
kubectl rollout restart statefulset mysql-statefulset -n kubeflow
```

### Problem 3: App pods can't connect

```bash
# Test DNS resolution
kubectl run test-dns --image=busybox --rm -it -n kubeflow -- nslookup mysql-statefulset-service.kubeflow.svc.cluster.local

# Test port connectivity
kubectl run test-port --image=busybox --rm -it -n kubeflow -- telnet mysql-statefulset-service.kubeflow.svc.cluster.local 3306

# Check service endpoints
kubectl get endpoints mysql-statefulset-service -n kubeflow
```

### Problem 4: MySQL out of memory

```bash
# Increase memory limits in mysql-statefulset.yaml
resources:
  limits:
    memory: "8Gi"  # Increase from 4Gi

# Apply changes
kubectl apply -f mysql-statefulset.yaml
```

---

## Cleanup

```bash
# Delete test app
kubectl delete deployment mysql-test-app -n kubeflow
kubectl delete configmap mysql-test-app-code -n kubeflow

# Delete MySQL (WARNING: This deletes data!)
kubectl delete statefulset mysql-statefulset -n kubeflow
kubectl delete service mysql-headless mysql-statefulset-service -n kubeflow
kubectl delete configmap mysql-config -n kubeflow
kubectl delete secret mysql-secret -n kubeflow

# Delete PVC (WARNING: Permanent data loss!)
kubectl delete pvc data-mysql-statefulset-0 -n kubeflow
```

---

## Connection Pool Configuration

### Current settings:

```yaml
env:
- name: DB_POOL_SIZE
  value: "10"      # Base connections per pod
- name: DB_MAX_OVERFLOW
  value: "5"       # Extra connections when needed
- name: DB_POOL_TIMEOUT
  value: "30"      # Wait time for connection
- name: DB_POOL_RECYCLE
  value: "3600"    # Recycle connections hourly
```

### Tuning guidelines:

**Light load (5-10 pods):**
```yaml
DB_POOL_SIZE: "5"
DB_MAX_OVERFLOW: "3"
```

**Medium load (10-20 pods):**
```yaml
DB_POOL_SIZE: "10"
DB_MAX_OVERFLOW: "5"
```

**Heavy load (20-30 pods):**
```yaml
DB_POOL_SIZE: "8"
DB_MAX_OVERFLOW: "4"
```

**Formula:**
```
Total connections = (num_pods × pool_size) + (num_pods × max_overflow)
Must be < MySQL max_connections (500)
```

---

## Next Steps

1. **Week 9:** Implement Master-Slave replication for read scaling
2. **Week 10:** Add monitoring with Prometheus + Grafana
3. **Week 11:** Implement backup/restore strategy
4. **Week 12:** Setup high availability with Patroni

---

## References

- [Kubernetes StatefulSets](https://kubernetes.io/docs/concepts/workloads/controllers/statefulset/)
- [MySQL Connection Pooling](https://dev.mysql.com/doc/connector-python/en/connector-python-connection-pooling.html)
- [SQLAlchemy Connection Pool](https://docs.sqlalchemy.org/en/20/core/pooling.html)
