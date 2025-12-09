# Week 8: Tổng hợp Config Files

## Mục lục
- [File Config từ Kubernetes](#file-config-từ-kubernetes)
- [File Test](#file-test)
- [Các file làm gì?](#các-file-làm-gì)
- [Chi tiết Config Files](#chi-tiết-config-files)
- [Cách sử dụng](#cách-sử-dụng)

---

## File Config từ Kubernetes

Các file config đã export từ Kubernetes cluster đang chạy:

| File              | Đường dẫn                              | Dòng | Mô tả                             |
|-------------------|----------------------------------------|------|-----------------------------------|
| HPA Config        | `./kubeflow-hpa-config.yaml`       | 568  | Config của 7 HPA (đang chạy)      |
| Deployment Config | `./kubeflow-deployments-config.yaml` | 1600 | Config của 14 deployments         |
| PDB Config        | `./kubeflow-pdb-config.yaml`       | 95   | Config của 3 PodDisruptionBudgets |

---

## File Test

File script để test autoscaling:

| File             | Đường dẫn                | Mô tả                   |
|------------------|--------------------------|-------------------------|
| Load Test Script | `./test-autoscaling.sh` | Script test autoscaling |

---

## Các file làm gì?

### 1. **kubeflow-hpa-config.yaml** (Horizontal Pod Autoscaler)
**Làm gì:** Tự động tăng/giảm số lượng pods dựa trên CPU/Memory usage

**Ví dụ thực tế:**
- Khi CPU > 80% → tự động tạo thêm pods để xử lý tải
- Khi CPU < 30% → tự động xóa bớt pods để tiết kiệm tài nguyên
- Giúp hệ thống tự động scale up khi có nhiều request, scale down khi ít request

**Tại sao cần:**
- Tiết kiệm chi phí: không phải chạy nhiều pods khi không cần
- Đảm bảo performance: tự động tăng pods khi tải cao
- Tự động hóa: không cần can thiệp thủ công

**7 services có HPA:** ml-pipeline, ml-pipeline-ui, metadata-grpc-deployment, metadata-writer, minio, mysql, cache-server

---

### 2. **kubeflow-deployments-config.yaml** (Deployment Configs)
**Làm gì:** Định nghĩa cách các services chạy trên Kubernetes

**Bao gồm:**
- **Docker images:** image nào được dùng cho mỗi service
- **Resource limits:** Cần bao nhiêu RAM/CPU (VD: mysql cần 2GB RAM, 1 CPU core)
- **Environment variables:** API keys, database URLs, v.v.
- **Health checks:** Kubernetes biết khi nào pod healthy/unhealthy
- **Storage volumes:** Mount data vào đâu (VD: MySQL data storage)

**Tại sao cần:**
- Định nghĩa chuẩn cách deploy services
- Dễ dàng replicate deployment trên cluster khác
- Version control cho infrastructure

**14 deployments:** ml-pipeline, workflow-controller, minio, mysql, metadata services, cache-server, v.v.

---

### 3. **kubeflow-pdb-config.yaml** (PodDisruptionBudget)
**Làm gì:** Đảm bảo service không bị down hoàn toàn khi maintenance

**Ví dụ thực tế:**
- MySQL có 3 pods, PDB đảm bảo luôn có ít nhất 2 pods running
- Khi update/restart Kubernetes nodes, không kill hết cả 3 pods cùng lúc
- Kubernetes sẽ rolling update từng pod một, đảm bảo service luôn available

**Tại sao cần:**
- **High Availability:** Service không bao giờ down hoàn toàn
- **Safe maintenance:** Update infrastructure mà không ảnh hưởng users
- **Zero-downtime deployment:** Deploy version mới không gián đoạn service

**3 services có PDB:** ml-pipeline, metadata-grpc-deployment, mysql

---

### 4. **test-autoscaling.sh** (Load Test Script)
**Làm gì:** Test xem HPA có hoạt động đúng không

**Chức năng:**
- Gửi nhiều requests đồng thời vào Kubeflow (simulate high load)
- Monitor số lượng pods tăng/giảm theo thời gian
- Đo response time để verify performance
- Validate autoscaling thresholds đã config có đúng không

**Ví dụ test:**
```bash
# Ban đầu: 2 pods
# Gửi 1000 concurrent requests
# → CPU tăng lên 85%
# → HPA tự động tạo thêm 3 pods (total 5 pods)
# → CPU giảm xuống 40%
# → Sau 5 phút idle, HPA xóa bớt còn 2 pods
```

**Tại sao cần:**
- Validate HPA config trước khi production
- Tìm bottlenecks và optimize thresholds
- Đảm bảo autoscaling work như mong đợi

---

## Tóm lại

| File | Chức năng chính | Khi nào dùng |
|------|-----------------|--------------|
| **HPA** | Auto-scale pods (tăng/giảm tự động) | Khi muốn optimize cost và performance |
| **Deployments** | Config chi tiết từng service | Khi deploy hoặc update services |
| **PDB** | Bảo vệ service khi maintenance | Khi cần high availability |
| **Test script** | Kiểm tra autoscaling có work không | Sau khi setup HPA hoặc thay đổi config |

---

## Chi tiết Config Files

### 1. HPA Config (`kubeflow-hpa-config.yaml`)
**Số dòng:** 568
**Nội dung:** Horizontal Pod Autoscaler configurations cho 7 services

HPA tự động scale pods dựa trên CPU/memory usage để đảm bảo performance và tối ưu tài nguyên.

**Services có HPA:**
- ml-pipeline
- ml-pipeline-ui
- metadata-grpc-deployment
- metadata-writer
- minio
- mysql
- cache-server

---

### 2. Deployment Config (`kubeflow-deployments-config.yaml`)
**Số dòng:** 1600
**Nội dung:** Deployment configurations cho 14 services

Các deployment định nghĩa:
- Container images
- Resource requests/limits
- Environment variables
- Volume mounts
- Liveness/Readiness probes
- Security contexts

**14 Deployments:**
1. ml-pipeline
2. ml-pipeline-persistenceagent
3. ml-pipeline-scheduledworkflow
4. ml-pipeline-ui
5. ml-pipeline-viewer-crd
6. ml-pipeline-visualizationserver
7. metadata-envoy-deployment
8. metadata-grpc-deployment
9. metadata-writer
10. minio
11. mysql
12. cache-server
13. workflow-controller
14. (và các services khác)

---

### 3. PDB Config (`kubeflow-pdb-config.yaml`)
**Số dòng:** 95
**Nội dung:** PodDisruptionBudget configurations cho 3 services

PDB đảm bảo minimum số pods available trong quá trình maintenance/updates.

**Services có PDB:**
- ml-pipeline
- metadata-grpc-deployment
- mysql

---

## Load Test Script

### File: `test-autoscaling.sh`
**Location:** `./test-autoscaling.sh`

Script để test HPA autoscaling behavior:
- Tạo concurrent requests
- Monitor pod scaling
- Measure response times
- Validate autoscaling thresholds

---

## Cách sử dụng

### Export lại config từ Kubernetes:
```bash
# Export HPA configs
kubectl get hpa -n kubeflow -o yaml > kubeflow-hpa-config.yaml

# Export Deployment configs
kubectl get deployments -n kubeflow -o yaml > kubeflow-deployments-config.yaml

# Export PDB configs
kubectl get pdb -n kubeflow -o yaml > kubeflow-pdb-config.yaml
```

### Chạy load test:
```bash
chmod +x ./test-autoscaling.sh
./test-autoscaling.sh
```

### Apply configs:
```bash
# Apply HPA
kubectl apply -f kubeflow-hpa-config.yaml

# Apply Deployments
kubectl apply -f kubeflow-deployments-config.yaml

# Apply PDB
kubectl apply -f kubeflow-pdb-config.yaml
```

---

## Notes

- Tất cả configs đã được export từ Kubernetes cluster đang chạy production
- HPA configs đã được tune để balance giữa performance và cost
- PDB configs đảm bảo high availability trong maintenance windows
- Load test script có thể customize thresholds và duration

---

## Related Documentation

- [Week 6+7 README](./README.md) - Kubernetes cluster installation guide
- [Kubeflow Official Docs](https://www.kubeflow.org/docs/)
- [Kubernetes HPA](https://kubernetes.io/docs/tasks/run-application/horizontal-pod-autoscale/)
- [PodDisruptionBudget](https://kubernetes.io/docs/concepts/workloads/pods/disruptions/)
