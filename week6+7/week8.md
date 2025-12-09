# Week 8: Tổng hợp Config Files

## Mục lục
- [File Config từ Kubernetes](#file-config-từ-kubernetes)
- [File Test](#file-test)
- [Chi tiết Config Files](#chi-tiết-config-files)

---

## File Config từ Kubernetes

Các file config đã export từ Kubernetes cluster đang chạy:

| File              | Đường dẫn                              | Dòng | Mô tả                             |
|-------------------|----------------------------------------|------|-----------------------------------|
| HPA Config        | `/root/kubeflow-hpa-config.yaml`       | 568  | Config của 7 HPA (đang chạy)      |
| Deployment Config | `/root/kubeflow-deployments-config.yaml` | 1600 | Config của 14 deployments         |
| PDB Config        | `/root/kubeflow-pdb-config.yaml`       | 95   | Config của 3 PodDisruptionBudgets |

---

## File Test

File script để test autoscaling:

| File             | Đường dẫn                | Mô tả                   |
|------------------|--------------------------|-------------------------|
| Load Test Script | `/tmp/test-autoscaling.sh` | Script test autoscaling |

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
**Location:** `/tmp/test-autoscaling.sh`

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
chmod +x /tmp/test-autoscaling.sh
/tmp/test-autoscaling.sh
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
