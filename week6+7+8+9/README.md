# Week 6-9: Production Deployment & Scaling

## 🎯 Tổng quan 4 tuần

Các tuần 6-9 tập trung vào **production deployment**, **scaling**, và **monitoring** của hệ thống MONAI + Kubeflow.

---

## 📚 Nội dung từng tuần

### 📁 [Week 6](week6/) - Database & Storage

**Mục tiêu**: Deploy và quản lý database cho production

**Nội dung chính**:
- Deploy MySQL StatefulSet trên Kubernetes
- Configure PersistentVolume và PersistentVolumeClaim
- Setup database backup và restore
- Security: MySQL secrets và credentials

**Files chính**:
- `mysql-statefulset.yaml` - MySQL deployment config
- `mysql-pv.yaml`, `mysql-secret.yaml` - Storage và security
- `database-deployment.md` - Hướng dẫn deploy chi tiết

**➡️ Xem chi tiết**: [week6/README.md](week6/README.md)

---

### 📁 [Week 7](week7/) - Horizontal Pod Autoscaling (HPA)

**Mục tiêu**: Auto-scale pods dựa trên CPU/Memory usage

**Nội dung chính**:
- Configure HPA cho Kubeflow components
- Setup Pod Disruption Budget (PDB)
- Load testing và performance tuning
- Monitor autoscaling behavior

**Files chính**:
- `kubeflow-hpa-config.yaml` - HPA configuration
- `kubeflow-pdb-config.yaml` - Pod Disruption Budget
- `test-autoscaling.sh` - Test HPA behavior
- `monitor-autoscaling.sh` - Monitor HPA metrics

**➡️ Xem chi tiết**: [week7/README.md](week7/README.md)

---

### 📁 [Week 8](week8/) - Deployment Strategies & Stress Testing

**Mục tiêu**: Deploy strategies và performance testing

**Nội dung chính**:
- Kubeflow deployments configuration
- Rolling updates và rollback
- Stress testing và load testing
- Performance optimization

**Files chính**:
- `kubeflow-deployments-config.yaml` - Deployment configs
- `test-app-deployment.yaml` - Test application
- `stress-test-guide.md` - Load testing guide

**➡️ Xem chi tiết**: [week8/README.md](week8/README.md)

---

### 📁 [Week 9](week9/) - Production Readiness & Database Testing

**Mục tiêu**: Final testing và production checklist

**Nội dung chính**:
- Comprehensive database testing
- Production readiness checklist
- Final validation và monitoring
- Documentation completion

**Files chính**:
- `test-mysql-database.sh` - Comprehensive DB tests
- `test-database-load.sh` - Load testing database
- `mysql-test-results.txt` - Test results

**➡️ Xem chi tiết**: [week9/README.md](week9/README.md)

---

## 🗓️ Learning Path

### Lộ trình học theo thứ tự

```
Week 6 → Week 7 → Week 8 → Week 9
  ↓        ↓        ↓        ↓
Database  HPA    Deploy   Testing
Storage   Scale  Strategy  Ready
```

**Yêu cầu trước khi bắt đầu**:
- ✅ Đã hoàn thành Week 3, 4, 5
- ✅ Có Kubernetes cluster (Minikube hoặc cloud)
- ✅ Kubeflow Pipelines đã cài đặt
- ✅ Kubectl và Docker đã setup

---

## 🎯 Kết quả sau 4 tuần

Sau khi hoàn thành Week 6-9, bạn sẽ có:

✅ **MySQL Database** running trên Kubernetes với PersistentVolume
✅ **Autoscaling** cho Kubeflow components (2-10 replicas)
✅ **Deployment Strategies** với rolling updates
✅ **Monitoring** và alerting setup
✅ **Load Testing** framework và results
✅ **Production Checklist** hoàn chỉnh

---

## 📊 Performance Targets

| Metric | Target | Achieved |
|--------|--------|----------|
| Database throughput | 1000+ req/s | ✅ |
| API response time | <100ms (p95) | ✅ |
| Autoscaling time | <2 minutes | ✅ |
| System uptime | 99.9% | 🎯 |
| Pod recovery time | <1 minute | ✅ |

---

## 🚀 Quick Start

### Cài đặt tuần 6 (Database)

```bash
cd week6
kubectl apply -f mysql-secret.yaml
kubectl apply -f mysql-pv.yaml
kubectl apply -f mysql-statefulset.yaml
```

### Cài đặt tuần 7 (HPA)

```bash
cd week7
kubectl apply -f kubeflow-hpa-config.yaml
kubectl apply -f kubeflow-pdb-config.yaml
./monitor-autoscaling.sh
```

### Test tuần 8 (Stress Testing)

```bash
cd week8
kubectl apply -f kubeflow-deployments-config.yaml
# Xem hướng dẫn trong stress-test-guide.md
```

### Validate tuần 9 (Production)

```bash
cd week9
./test-mysql-database.sh
./test-database-load.sh
```

---

## 📖 Tài liệu tham khảo

- [Kubernetes StatefulSets](https://kubernetes.io/docs/concepts/workloads/controllers/statefulset/)
- [Horizontal Pod Autoscaler](https://kubernetes.io/docs/tasks/run-application/horizontal-pod-autoscale/)
- [Kubeflow Production Best Practices](https://www.kubeflow.org/docs/started/best-practices/)

---

**Cấu trúc**: 4 folders riêng biệt, mỗi tuần có README chi tiết
**Thời gian**: ~4 tuần (1 tuần/topic)
**Độ khó**: Intermediate → Advanced
