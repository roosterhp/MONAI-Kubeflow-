# Database Scaling Strategy - Giải pháp cho Database không HPA được

## Vấn đề

**Database KHÔNG THỂ scale như application pods** vì:
- Database là **STATEFUL** (có state/data)
- Không thể tạo nhiều instances và load balance ngẫu nhiên
- Data consistency issues khi có nhiều instances ghi đồng thời
- Cần coordination giữa các instances

**Ví dụ vấn đề:**
```
App Pod 1 → writes to MySQL Pod 1
App Pod 2 → writes to MySQL Pod 2
→ DATA INCONSISTENCY! (2 databases khác nhau)
```

---

## Các giải pháp Scale Database

### **Giải pháp 1: StatefulSet + Single Master** (Đơn giản nhất)
✅ Khả thi: CÓ
✅ Phức tạp: THẤP
✅ Use case: Small-Medium workload

#### Kiến trúc:
```
┌─────────────────────────────────────────────┐
│            Application Layer                │
│  [App Pod 1] [App Pod 2] [App Pod 3] ...   │
└──────────┬──────────┬──────────┬────────────┘
           │          │          │
           └──────────┼──────────┘
                      │
           ┌──────────▼──────────┐
           │   MySQL Service     │ (ClusterIP)
           │    (Endpoint)       │
           └──────────┬──────────┘
                      │
           ┌──────────▼──────────┐
           │   MySQL StatefulSet │
           │     (1 replica)     │
           │   Persistent Volume │
           └─────────────────────┘
```

#### Implement:

**1. MySQL StatefulSet:**
```yaml
# mysql-statefulset.yaml
apiVersion: v1
kind: Service
metadata:
  name: mysql
  namespace: kubeflow
spec:
  ports:
  - port: 3306
  clusterIP: None  # Headless service for StatefulSet
  selector:
    app: mysql
---
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: mysql
  namespace: kubeflow
spec:
  serviceName: mysql
  replicas: 1  # Single master
  selector:
    matchLabels:
      app: mysql
  template:
    metadata:
      labels:
        app: mysql
    spec:
      containers:
      - name: mysql
        image: mysql:8.0
        env:
        - name: MYSQL_ROOT_PASSWORD
          valueFrom:
            secretKeyRef:
              name: mysql-secret
              key: password
        ports:
        - containerPort: 3306
          name: mysql
        volumeMounts:
        - name: data
          mountPath: /var/lib/mysql
        resources:
          requests:
            cpu: "2"
            memory: "4Gi"
          limits:
            cpu: "4"
            memory: "8Gi"
  volumeClaimTemplates:
  - metadata:
      name: data
    spec:
      accessModes: [ "ReadWriteOnce" ]
      resources:
        requests:
          storage: 100Gi
```

**2. App Pods Connection:**
```yaml
# app-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ml-pipeline
  namespace: kubeflow
spec:
  replicas: 10  # Scale thoải mái
  template:
    spec:
      containers:
      - name: app
        env:
        - name: DB_HOST
          value: "mysql.kubeflow.svc.cluster.local"
        - name: DB_PORT
          value: "3306"
        - name: DB_CONNECTION_POOL_SIZE
          value: "20"  # Connection pool per pod
        - name: DB_MAX_CONNECTIONS
          value: "100"  # Limit per pod
```

**3. Connection Pooling (Python example):**
```python
# app/database.py
from sqlalchemy import create_engine
from sqlalchemy.pool import QueuePool

# Connection pool config
engine = create_engine(
    f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}",
    pool_size=20,           # Base connections
    max_overflow=10,        # Extra connections khi cần
    pool_timeout=30,        # Timeout waiting for connection
    pool_recycle=3600,      # Recycle connections every hour
    pool_pre_ping=True,     # Check connection health
    echo_pool=True          # Log connection pool activity
)
```

**Ưu điểm:**
- ✅ Đơn giản, dễ implement
- ✅ Data consistency 100%
- ✅ Không cần setup phức tạp

**Nhược điểm:**
- ❌ Single point of failure
- ❌ Không scale horizontally
- ❌ Limited by single database instance resources

**Khi nào dùng:**
- Workload nhỏ-trung bình
- Cần đơn giản, ổn định
- Budget hạn chế

---

### **Giải pháp 2: Master-Slave Replication** (Scale reads)
✅ Khả thi: CÓ
✅ Phức tạp: TRUNG BÌNH
✅ Use case: Read-heavy workload (90% reads, 10% writes)

#### Kiến trúc:
```
App Pods (Writes) ──────────┐
                            │
                   ┌────────▼────────┐
                   │  MySQL MASTER   │ (Writes only)
                   │  StatefulSet-0  │
                   └────────┬────────┘
                            │ Replication
        ┌───────────────────┼───────────────────┐
        │                   │                   │
┌───────▼────────┐  ┌───────▼────────┐  ┌──────▼───────┐
│ MySQL SLAVE 1  │  │ MySQL SLAVE 2  │  │ MySQL SLAVE 3│
│ StatefulSet-1  │  │ StatefulSet-2  │  │ StatefulSet-3│
└───────▲────────┘  └───────▲────────┘  └──────▲───────┘
        │                   │                   │
App Pods (Reads) ───────────┴───────────────────┘
```

#### Implement:

**1. Master-Slave StatefulSet:**
```yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: mysql
  namespace: kubeflow
spec:
  serviceName: mysql
  replicas: 3  # 1 master + 2 slaves
  template:
    spec:
      initContainers:
      - name: init-mysql
        image: mysql:8.0
        command:
        - bash
        - "-c"
        - |
          set -ex
          # Generate mysql server-id from pod ordinal index
          [[ $(hostname) =~ -([0-9]+)$ ]] || exit 1
          ordinal=${BASH_REMATCH[1]}
          echo [mysqld] > /mnt/conf.d/server-id.cnf
          echo server-id=$((100 + $ordinal)) >> /mnt/conf.d/server-id.cnf

          # Master (pod 0) hoặc Slave (pod 1,2,3...)
          if [[ $ordinal -eq 0 ]]; then
            cp /mnt/config-map/master.cnf /mnt/conf.d/
          else
            cp /mnt/config-map/slave.cnf /mnt/conf.d/
          fi
        volumeMounts:
        - name: conf
          mountPath: /mnt/conf.d
        - name: config-map
          mountPath: /mnt/config-map
      containers:
      - name: mysql
        image: mysql:8.0
        env:
        - name: MYSQL_ROOT_PASSWORD
          valueFrom:
            secretKeyRef:
              name: mysql-secret
              key: password
        ports:
        - containerPort: 3306
          name: mysql
        volumeMounts:
        - name: data
          mountPath: /var/lib/mysql
        - name: conf
          mountPath: /etc/mysql/conf.d
        resources:
          requests:
            cpu: "2"
            memory: "4Gi"
          limits:
            cpu: "4"
            memory: "8Gi"
      volumes:
      - name: conf
        emptyDir: {}
      - name: config-map
        configMap:
          name: mysql-config
  volumeClaimTemplates:
  - metadata:
      name: data
    spec:
      accessModes: [ "ReadWriteOnce" ]
      resources:
        requests:
          storage: 100Gi
```

**2. Services cho Master và Slaves:**
```yaml
# Master service (writes)
apiVersion: v1
kind: Service
metadata:
  name: mysql-master
  namespace: kubeflow
spec:
  ports:
  - port: 3306
  selector:
    app: mysql
    statefulset.kubernetes.io/pod-name: mysql-0  # Pod 0 = master
---
# Slave service (reads)
apiVersion: v1
kind: Service
metadata:
  name: mysql-slave
  namespace: kubeflow
spec:
  ports:
  - port: 3306
  selector:
    app: mysql
  # Load balance across all slaves (pod 1,2,3...)
```

**3. App connection routing:**
```python
# app/database.py
from sqlalchemy import create_engine

# Write connection (master only)
write_engine = create_engine(
    f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@mysql-master.kubeflow.svc.cluster.local:3306/{DB_NAME}",
    pool_size=20,
    max_overflow=10
)

# Read connection (slaves with load balancing)
read_engine = create_engine(
    f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@mysql-slave.kubeflow.svc.cluster.local:3306/{DB_NAME}",
    pool_size=50,  # More connections for reads
    max_overflow=20
)

# Usage
def get_user(user_id):
    # Read from slave
    return read_engine.execute(f"SELECT * FROM users WHERE id={user_id}")

def create_user(data):
    # Write to master
    return write_engine.execute(f"INSERT INTO users ...")
```

**Ưu điểm:**
- ✅ Scale reads horizontally (thêm slaves)
- ✅ High availability (master fail, promote slave)
- ✅ Tăng throughput cho read-heavy workload

**Nhược điểm:**
- ❌ Không scale writes (vẫn single master)
- ❌ Replication lag (slaves có thể chậm hơn master vài ms)
- ❌ Setup phức tạp hơn

**Khi nào dùng:**
- Read-heavy workload (90% reads)
- Cần high availability
- Có budget cho nhiều database instances

---

### **Giải pháp 3: Database Clustering** (Scale cả reads và writes)
✅ Khả thi: CÓ
✅ Phức tạp: CAO
✅ Use case: Large-scale, mission-critical

#### Các options:

**A. MySQL InnoDB Cluster (Group Replication):**
```
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│  MySQL Node 1│◄─┤  MySQL Node 2│◄─┤  MySQL Node 3│
│   (Primary)  │──►   (Secondary) │──►   (Secondary)│
└──────────────┘  └──────────────┘  └──────────────┘
       ▲                  ▲                  ▲
       │                  │                  │
       └──────────────────┴──────────────────┘
              MySQL Router (Load Balancer)
```

**B. Galera Cluster (MariaDB):**
- Multi-master: tất cả nodes có thể write
- Synchronous replication
- Automatic failover

**C. PostgreSQL với Patroni:**
- Automatic failover
- Streaming replication
- Kubernetes operator support

**D. Cloud-managed databases:**
- AWS RDS (Multi-AZ)
- Google Cloud SQL (HA)
- Azure Database for MySQL

**Ưu điểm:**
- ✅ Scale cả reads và writes
- ✅ High availability tự động
- ✅ Zero downtime maintenance

**Nhược điểm:**
- ❌ Rất phức tạp setup
- ❌ Chi phí cao
- ❌ Cần expertise vận hành

---

### **Giải pháp 4: Connection Pooling + Vertical Scaling**
✅ Khả thi: CÓ (Đơn giản nhất!)
✅ Phức tạp: THẤP
✅ Use case: Khi chưa cần horizontal scaling

#### Tối ưu connection pool:

**1. MySQL Server config:**
```ini
# /etc/mysql/my.cnf
[mysqld]
max_connections = 500          # Tăng max connections
max_connect_errors = 1000000   # Tránh block clients
wait_timeout = 600             # Timeout cho idle connections
interactive_timeout = 600
thread_cache_size = 128        # Cache threads
table_open_cache = 4000        # Cache tables
innodb_buffer_pool_size = 8G   # Cache data in memory
innodb_log_file_size = 512M    # Transaction log size
```

**2. Application connection pool:**
```python
# Python SQLAlchemy
from sqlalchemy import create_engine

engine = create_engine(
    database_url,

    # Pool settings
    pool_size=20,              # Connections per pod
    max_overflow=10,           # Extra connections
    pool_timeout=30,           # Wait time
    pool_recycle=3600,         # Recycle hourly
    pool_pre_ping=True,        # Health check

    # Connection settings
    connect_args={
        "connect_timeout": 10,
        "read_timeout": 30,
        "write_timeout": 30,
    }
)
```

**3. Calculate total connections:**
```
Total connections = (app_pods × pool_size) + (app_pods × max_overflow)

Example:
- 10 app pods
- pool_size = 20
- max_overflow = 10
Total = (10 × 20) + (10 × 10) = 300 connections

MySQL max_connections phải > 300 (recommend 500)
```

**4. Monitor connections:**
```sql
-- Check current connections
SHOW PROCESSLIST;

-- Check connection statistics
SHOW STATUS LIKE 'Threads_connected';
SHOW STATUS LIKE 'Max_used_connections';

-- Check if hitting limits
SHOW VARIABLES LIKE 'max_connections';
```

**5. Vertical scale database:**
```yaml
# Tăng resources cho MySQL pod
resources:
  requests:
    cpu: "4"      # Tăng từ 2 lên 4
    memory: "8Gi"  # Tăng từ 4Gi lên 8Gi
  limits:
    cpu: "8"
    memory: "16Gi"
```

---

## Load Testing với nhiều pods

### Test script:

```bash
#!/bin/bash
# test-database-load.sh

echo "=== Database Load Test ==="
echo "Testing concurrent connections from multiple pods..."

# Scale app to 20 pods
kubectl scale deployment ml-pipeline -n kubeflow --replicas=20

echo "Waiting for pods to be ready..."
kubectl wait --for=condition=ready pod -l app=ml-pipeline -n kubeflow --timeout=300s

echo "Starting load test..."

# Monitor database connections
watch -n 2 "kubectl exec -n kubeflow mysql-0 -- mysql -uroot -p\$MYSQL_ROOT_PASSWORD -e 'SHOW PROCESSLIST; SELECT COUNT(*) as connections FROM information_schema.processlist;'"
```

### Metrics để monitor:

```bash
# 1. Database connections
kubectl exec -n kubeflow mysql-0 -- mysql -uroot -p$MYSQL_ROOT_PASSWORD -e "
  SELECT
    COUNT(*) as total_connections,
    SUM(IF(command='Sleep', 1, 0)) as idle_connections,
    SUM(IF(command!='Sleep', 1, 0)) as active_connections
  FROM information_schema.processlist;
"

# 2. Database CPU/Memory
kubectl top pod mysql-0 -n kubeflow

# 3. Query performance
kubectl exec -n kubeflow mysql-0 -- mysql -uroot -p$MYSQL_ROOT_PASSWORD -e "
  SELECT
    query_time,
    lock_time,
    rows_examined,
    rows_sent,
    sql_text
  FROM mysql.slow_log
  ORDER BY query_time DESC
  LIMIT 10;
"

# 4. Connection errors
kubectl logs -n kubeflow -l app=ml-pipeline | grep -i "connection"
```

---

## Khuyến nghị Implementation

### **Bắt đầu với:** Giải pháp 1 + 4 (StatefulSet + Connection Pooling)

**Roadmap:**
1. **Week 8 (Hiện tại):**
   - Deploy MySQL với StatefulSet
   - Configure connection pooling
   - Set resource limits
   - Load testing

2. **Week 9 (Nếu cần scale):**
   - Implement Master-Slave replication
   - Separate read/write traffic
   - Add monitoring

3. **Week 10+ (Production-ready):**
   - Setup backup/restore
   - High availability
   - Monitoring & alerting
   - Performance tuning

---

## File cần tạo:

```
week6+7/
├── mysql-statefulset.yaml       # MySQL deployment
├── mysql-configmap.yaml         # MySQL config
├── mysql-secret.yaml            # MySQL credentials
├── app-deployment-updated.yaml  # App với connection pool config
└── test-database-load.sh        # Load test script
```

---

## Kết luận

**TRẢ LỜI TRỰC TIẾP:**

✅ **CÓ thể làm như bạn đề xuất:**
- Deploy database bằng StatefulSet ✓
- Cấu hình app pods dùng chung endpoint ✓
- Test hiệu năng concurrent connections ✓
- Tối ưu connection pool ✓

**Nhưng lưu ý:**
- Database KHÔNG scale như app pods (không HPA được)
- Cần vertical scaling (tăng CPU/RAM) thay vì horizontal
- Hoặc dùng Master-Slave cho read-heavy workload
- Connection pooling là KEY để optimize

**Next steps:**
1. Implement StatefulSet cho MySQL
2. Configure connection pooling trong app
3. Load testing với nhiều pods
4. Monitor và optimize
