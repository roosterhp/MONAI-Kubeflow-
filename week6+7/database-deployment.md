# Database Scaling with StatefulSet - Deep Dive

## Vấn đề cần giải quyết

### Database KHÔNG THỂ scale như application pods

**App pods có thể scale (Stateless):**
```
Ban đầu: 2 app pods xử lý 100 req/s
Quá tải! → HPA scale lên 10 pods
→ Mỗi pod xử lý 10 req/s
→ WORK! Vì mỗi pod độc lập
```

**Database KHÔNG THỂ scale như vậy (Stateful):**
```
❌ TRY: Scale lên 3 database pods

App Pod 1 → writes "User ID=1, Name=John" → DB Pod 1
App Pod 2 → writes "User ID=1, Name=Jane" → DB Pod 2
App Pod 3 → reads "User ID=1" → DB Pod 3

→ KẾT QUẢ:
  DB Pod 1: Name=John
  DB Pod 2: Name=Jane
  DB Pod 3: KHÔNG CÓ DATA!

❌ DATA INCONSISTENCY! 3 databases khác nhau!
```

### Tại sao không scale được?

**Problem 1: Data Inconsistency**
```
Timeline:
10:00 - User đăng ký → ghi vào DB Pod 1
10:01 - User login → đọc từ DB Pod 2 (load balancer)
→ Result: "User not found" ← DB Pod 2 KHÔNG CÓ DATA!
```

**Problem 2: Write Conflicts**
```
App Pod 1: UPDATE balance=100 WHERE id=1 → DB Pod 1
App Pod 2: UPDATE balance=200 WHERE id=1 → DB Pod 2

→ KẾT QUẢ:
  DB Pod 1: balance=100
  DB Pod 2: balance=200
→ Balance thật là bao nhiêu? KHÔNG BIẾT!
```

**Problem 3: Transaction Issues**
```
BEGIN TRANSACTION;
  UPDATE balance-100 WHERE user='A'; → DB Pod 1
  UPDATE balance+100 WHERE user='B'; → DB Pod 2
COMMIT;

→ 2 pods KHÔNG BIẾT transaction của nhau!
→ Nếu DB Pod 2 fail? 100$ BIẾN MẤT!
```

---

## Giải pháp: StatefulSet + Shared Endpoint

### Kiến trúc

```
┌─────────────────────────────────────────────┐
│         Application Layer (SCALABLE)        │
│  [App Pod 1] [App Pod 2] ... [App Pod 30]  │
│                                             │
│  Mỗi pod có connection pool:                │
│  - 10 base connections                      │
│  - 5 overflow connections                   │
└──────────┬──────────┬──────────┬────────────┘
           │          │          │
           │  Tất cả pods connect tới          │
           │  CÙNG 1 endpoint                  │
           │                                   │
           └──────────┼──────────┘
                      │
        ┌─────────────▼─────────────┐
        │  Service (ClusterIP)      │
        │  mysql-statefulset-service│
        │                           │
        │  DNS: mysql-statefulset-  │
        │  service.kubeflow.svc.    │
        │  cluster.local:3306       │
        │                           │
        │  Stable endpoint cho apps │
        └─────────────┬─────────────┘
                      │
                      │ Service trỏ tới
                      │ DUY NHẤT 1 pod
                      ↓
        ┌─────────────────────────────┐
        │  MySQL StatefulSet          │
        │  mysql-statefulset-0        │
        │                             │
        │  - Stable hostname           │
        │  - Persistent storage        │
        │  - max_connections: 500      │
        │                             │
        │  Config optimized:          │
        │  - innodb_buffer_pool: 2G   │
        │  - thread_cache: 128        │
        └─────────────┬───────────────┘
                      │
                      │ Persistent data
                      ↓
        ┌─────────────────────────────┐
        │  PersistentVolume (20Gi)    │
        │  /var/lib/mysql             │
        │                             │
        │  Data không mất khi pod     │
        │  restart hoặc recreate      │
        └─────────────────────────────┘
```

### Giải thích chi tiết

#### 1. Tại sao dùng StatefulSet thay vì Deployment?

**Deployment (Kubeflow hiện tại):**
```yaml
kind: Deployment
metadata:
  name: mysql
spec:
  replicas: 1
```

**Vấn đề:**
```
kubectl delete pod mysql-abc123
→ Pod mới: mysql-def456 (tên KHÁC!)
→ Hostname thay đổi
→ Data MẤT nếu không có persistent volume
→ KHÔNG ổn định cho database!
```

**StatefulSet (Giải pháp này):**
```yaml
kind: StatefulSet
metadata:
  name: mysql-statefulset
spec:
  replicas: 1
  volumeClaimTemplates:
  - metadata:
      name: data
    spec:
      storage: 20Gi
```

**Ưu điểm:**
```
kubectl delete pod mysql-statefulset-0
→ Pod mới: mysql-statefulset-0 (TÊN GIỐNG!)
→ Hostname KHÔNG ĐỔI
→ Mount lại PVC cũ → Data GIỮ NGUYÊN
→ ỔN ĐỊNH cho database!
```

**So sánh:**

| Feature | Deployment | StatefulSet |
|---------|------------|-------------|
| **Pod name** | `mysql-abc123` (random) | `mysql-statefulset-0` (fixed) |
| **Restart behavior** | Tạo pod mới tên khác | Vẫn là `mysql-statefulset-0` |
| **Hostname** | Thay đổi | KHÔNG ĐỔI |
| **Storage** | Optional | Built-in với volumeClaimTemplates |
| **Ordered scaling** | No | Yes (0→1→2) |
| **For database** | ❌ Not recommended | ✅ Best practice |

#### 2. Service - Shared Endpoint

**Chức năng:**
```yaml
apiVersion: v1
kind: Service
metadata:
  name: mysql-statefulset-service
spec:
  type: ClusterIP
  selector:
    app: mysql-statefulset
  ports:
  - port: 3306
```

**Tạo STABLE ENDPOINT:**
- DNS: `mysql-statefulset-service.kubeflow.svc.cluster.local`
- ClusterIP: `10.233.53.123` (không đổi)
- Forward tất cả traffic tới `mysql-statefulset-0`

**Workflow:**
```
App Pod 1 connect:
  → DNS lookup: mysql-statefulset-service.kubeflow.svc.cluster.local
  → Resolve to: 10.233.53.123 (Service ClusterIP)
  → Service forward to: mysql-statefulset-0 (Pod IP: 10.233.x.x)
  → MySQL nhận connection

App Pod 2 connect:
  → DNS lookup: mysql-statefulset-service.kubeflow.svc.cluster.local
  → Resolve to: 10.233.53.123 (CÙNG IP!)
  → Service forward to: mysql-statefulset-0 (CÙNG POD!)
  → MySQL nhận connection

App Pod 30 connect:
  → ... (CÙNG FLOW!)

→ TẤT CẢ 30 APP PODS CONNECT TỚI CÙNG 1 MYSQL POD!
→ DATA CONSISTENCY ✓
```

#### 3. Connection Pooling - Tối ưu connections

**Vấn đề không có connection pool:**
```python
# ❌ Mỗi request tạo connection mới
def get_user(id):
    conn = mysql.connect()  # Tạo mới! (expensive)
    result = conn.query(f"SELECT * FROM users WHERE id={id}")
    conn.close()  # Đóng
    return result

# 30 pods × 100 requests/s = 3000 connections/s
# MySQL chết vì quá nhiều connections!
```

**Giải pháp: Connection Pool**
```python
# ✅ Reuse connections
from sqlalchemy import create_engine

engine = create_engine(
    "mysql://user:pass@mysql-statefulset-service:3306/db",
    pool_size=10,        # Giữ 10 connections sẵn
    max_overflow=5,      # Tạo thêm 5 nếu cần
    pool_recycle=3600,   # Recycle mỗi giờ
    pool_pre_ping=True   # Check health
)

def get_user(id):
    with engine.connect() as conn:  # Lấy từ pool (fast)
        result = conn.query(f"SELECT * FROM users WHERE id={id}")
        # Connection tự động trả về pool
    return result
```

**Kết quả:**
```
Trước: 30 pods × 100 new connections/s = 3000 connections/s
       → MySQL CPU 100%, queries slow

Sau:   30 pods × 10 pool_size = 300 connections (reuse!)
       → MySQL CPU 30%, queries fast

→ GIẢM 90% overhead!
→ Performance tăng 10x!
```

**Connection calculation:**
```
Base connections: 30 pods × 10 pool_size = 300
Max connections:  30 pods × (10 + 5 overflow) = 450

MySQL max_connections = 500
→ Còn dư 50 connections cho system/admin

→ SAFE! Không bị "Too many connections" error
```

#### 4. Data Consistency - Timeline example

**Scenario: User registration và login**

```
Time   | App Pod | Action | Target | Result
-------|---------|--------|--------|--------
10:00  | Pod 5   | INSERT user='John', id=1 |
       |         |   ↓                      |
       |         | mysql-statefulset-service |
       |         |   ↓                      |
       |         | mysql-statefulset-0      |
       |         |   → Data written to PVC  | ✓ Stored
-------|---------|--------|--------|--------
10:01  | Pod 12  | SELECT user WHERE id=1   |
       |         |   ↓                      |
       |         | mysql-statefulset-service |
       |         |   ↓                      |
       |         | mysql-statefulset-0      | ← CÙNG POD!
       |         |   → Read from PVC        | ✓ Return: John
-------|---------|--------|--------|--------
10:02  | Pod 23  | UPDATE user='John Doe' WHERE id=1 |
       |         |   ↓                      |
       |         | mysql-statefulset-service |
       |         |   ↓                      |
       |         | mysql-statefulset-0      | ← VẪN CÙNG POD!
       |         |   → Update in PVC        | ✓ Updated
-------|---------|--------|--------|--------
10:03  | Pod 7   | SELECT user WHERE id=1   |
       |         |   ↓                      |
       |         | mysql-statefulset-service |
       |         |   ↓                      |
       |         | mysql-statefulset-0      | ← VẪN CÙNG POD!
       |         |   → Read from PVC        | ✓ Return: John Doe

→ TẤT CẢ APP PODS ĐỀU THẤY DATA NHẤT QUÁN!
→ KHÔNG CÓ data inconsistency!
```

**So sánh nếu KHÔNG dùng shared endpoint:**

```
❌ WRONG APPROACH: Multiple databases
10:00  | Pod 5   | INSERT user='John'  | DB Pod 1 | ✓
10:01  | Pod 12  | SELECT user id=1    | DB Pod 2 | ✗ Not found!
       |         |                     | (load balancer picked Pod 2)
       |         |                     | (Pod 2 không có data!)
```

---

## Configuration Details

### MySQL Config (mysql-configmap.yaml)

```ini
[mysqld]
# Connection settings - tối ưu cho connection pooling
max_connections = 500          # Cho phép 500 connections đồng thời
max_connect_errors = 1000000   # Tránh block clients
wait_timeout = 600             # Timeout cho idle connections
interactive_timeout = 600      # Timeout cho interactive sessions

# Cache settings - tăng performance
thread_cache_size = 128        # Cache threads để reuse
table_open_cache = 4000        # Cache table definitions

# InnoDB settings - storage engine optimization
innodb_buffer_pool_size = 2G   # Cache data và indexes trong RAM
                               # Rule: 70-80% of available RAM
innodb_log_file_size = 512M    # Transaction log size
innodb_flush_log_at_trx_commit = 2  # Balance safety/performance
innodb_flush_method = O_DIRECT # Bypass OS cache

# Binary logging - cho replication (future)
log_bin = /var/log/mysql/mysql-bin.log
expire_logs_days = 7
max_binlog_size = 100M
```

**Giải thích:**

| Setting | Value | Tại sao |
|---------|-------|---------|
| `max_connections` | 500 | Cho phép 30 pods × 15 connections = 450 |
| `innodb_buffer_pool_size` | 2G | Cache data trong RAM → queries nhanh hơn |
| `thread_cache_size` | 128 | Reuse threads → reduce overhead |
| `wait_timeout` | 600s | Tự động đóng idle connections sau 10 phút |

### App Connection Pool Config

```yaml
env:
- name: DB_HOST
  value: "mysql-statefulset-service.kubeflow.svc.cluster.local"
- name: DB_PORT
  value: "3306"

# Connection pool settings
- name: DB_POOL_SIZE
  value: "10"      # 10 connections per pod (persistent)
- name: DB_MAX_OVERFLOW
  value: "5"       # +5 temporary connections khi cần
- name: DB_POOL_TIMEOUT
  value: "30"      # Wait 30s for available connection
- name: DB_POOL_RECYCLE
  value: "3600"    # Recycle connections sau 1 giờ
```

**Connection math:**
```
Light load (5 pods):
  5 × 10 pool = 50 connections
  Buffer: 450 connections còn lại

Medium load (10 pods):
  10 × 10 pool = 100 connections
  Buffer: 400 connections còn lại

Heavy load (20 pods):
  20 × 10 pool = 200 connections
  Max burst: 20 × 15 = 300 connections
  Buffer: 200 connections còn lại

Max safe (30 pods):
  30 × 10 pool = 300 connections
  Max burst: 30 × 15 = 450 connections
  Buffer: 50 connections còn lại

→ 30 pods là LIMIT an toàn với config hiện tại!
```

---

## Deployment Guide

### Bước 1: Deploy MySQL StatefulSet

```bash
cd /root/MONAI-Kubeflow-/week6+7

# 1. Apply Secret (credentials)
kubectl apply -f mysql-secret.yaml

# 2. Apply ConfigMap (MySQL config)
kubectl apply -f mysql-configmap.yaml

# 3. Apply PersistentVolume (storage)
kubectl apply -f mysql-pv.yaml

# 4. Apply StatefulSet + Services
kubectl apply -f mysql-statefulset.yaml
```

**Verify:**
```bash
# Check StatefulSet
kubectl get statefulset mysql-statefulset -n kubeflow
# Expected: READY 1/1

# Check Pod
kubectl get pod mysql-statefulset-0 -n kubeflow
# Expected: STATUS Running

# Check Services
kubectl get svc -n kubeflow | grep mysql
# Expected:
#   mysql-headless (ClusterIP None)
#   mysql-statefulset-service (ClusterIP 10.233.x.x)

# Check PVC
kubectl get pvc -n kubeflow | grep mysql
# Expected: data-mysql-statefulset-0 Bound

# Test connection
kubectl exec -n kubeflow mysql-statefulset-0 -- \
  mysql -uroot -pkubeflow123 -e "SELECT VERSION();"
# Expected: 8.0.44
```

### Bước 2: Deploy Test Application

```bash
# Deploy test app (5 pods)
kubectl apply -f test-app-deployment.yaml

# Wait for pods ready
kubectl wait --for=condition=ready pod \
  -l app=mysql-test-app -n kubeflow --timeout=180s

# Check pods
kubectl get pods -n kubeflow -l app=mysql-test-app
```

**Check app logs:**
```bash
POD=$(kubectl get pods -n kubeflow -l app=mysql-test-app \
  -o jsonpath='{.items[0].metadata.name}')

kubectl logs -n kubeflow $POD --tail=50

# Expected output:
# === MySQL Connection Pool Test ===
# Host: mysql-statefulset-service.kubeflow.svc.cluster.local:3306
# Database: kubeflow_db
# Pool Size: 10
# Max Overflow: 5
# Pod: mysql-test-app-xxxxx
#
# Connected to MySQL successfully!
# Test table created
#
# [15:30:00] Requests: 10 | Pool: 3/10 | Overflow: 0 |
#            DB Rows: 50 | Unique Pods: 5
```

### Bước 3: Test Concurrent Connections

```bash
# Run load test script
chmod +x test-database-load.sh
./test-database-load.sh

# Script will ask: Scale to how many pods?
# Try: 10, 20, 30
```

**Monitor dashboard:**
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

---

## Troubleshooting

### Problem 1: Pod Pending (PVC not bound)

**Solution:**
```bash
# Check storage class
kubectl get sc

# Create PV manually
kubectl apply -f mysql-pv.yaml
```

### Problem 2: Too Many Connections

**Solution:**
```bash
# Option 1: Increase max_connections in mysql-configmap.yaml
# Option 2: Reduce pool_size per pod
# Option 3: Scale down app pods
```

### Problem 3: App Can't Connect

**Solution:**
```bash
# Test DNS
kubectl run test-dns --image=busybox --rm -it -n kubeflow -- \
  nslookup mysql-statefulset-service.kubeflow.svc.cluster.local

# Check service endpoints
kubectl get endpoints mysql-statefulset-service -n kubeflow
```

---

## Summary

### What we built:

1. **MySQL StatefulSet**: 1 pod with persistent storage
2. **Shared Service Endpoint**: All apps connect to same MySQL
3. **Connection Pooling**: 10 connections per pod (reusable)
4. **Optimized Config**: max_connections=500, buffer_pool=2G
5. **Load Testing**: Supports up to 30 app pods safely

### Why it works:

- ✅ **Data Consistency**: All apps read/write same database
- ✅ **Persistence**: Data survives pod restarts
- ✅ **Performance**: Connection pooling reduces overhead
- ✅ **Scalability**: App pods scale, database stable

### Limitations:

- ❌ **Single Point of Failure**: 1 pod down = no database
- ❌ **No Horizontal Scaling**: Can't add more database pods
- ❌ **Limited Capacity**: Max 30 app pods with current config

### When to use:

- ✅ Small-medium workload (< 500 req/s)
- ✅ Need data consistency
- ✅ Simple architecture
- ✅ Budget constrained
