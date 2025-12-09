# Hướng dẫn Stress Test và Kiểm chứng Autoscaling

## Mục lục
- [Chuẩn bị](#chuẩn-bị)
- [Các bước thực hiện](#các-bước-thực-hiện)
- [Giải thích kết quả](#giải-thích-kết-quả)
- [Troubleshooting](#troubleshooting)

---

## Chuẩn bị

### 1. Kiểm tra HPA có hoạt động không:
```bash
kubectl get hpa -n kubeflow
```

**Output mong đợi:**
```
NAME                        REFERENCE                              TARGETS   MINPODS   MAXPODS   REPLICAS
ml-pipeline                 Deployment/ml-pipeline                 15%/80%   2         10        2
metadata-grpc-deployment    Deployment/metadata-grpc-deployment    10%/80%   1         5         1
...
```

### 2. Kiểm tra số pods ban đầu:
```bash
kubectl get pods -n kubeflow | grep ml-pipeline
```

### 3. Chuẩn bị scripts:
```bash
cd /root/MONAI-Kubeflow-/week6+7
chmod +x test-autoscaling.sh monitor-autoscaling.sh
```

---

## Các bước thực hiện

### Bước 1: Mở 2 terminals

**Terminal 1:** Monitor (theo dõi realtime)
```bash
./monitor-autoscaling.sh
```

**Terminal 2:** Stress test (tạo load)
```bash
./test-autoscaling.sh
```

### Bước 2: Quan sát trong Terminal 1

Bạn sẽ thấy các thông tin:

#### **HPA Status:**
```
NAME          REFERENCE                    TARGETS    MINPODS   MAXPODS   REPLICAS
ml-pipeline   Deployment/ml-pipeline       15%/80%    2         10        2
```

- **TARGETS:** CPU hiện tại / CPU threshold (15% / 80%)
- **REPLICAS:** Số pods hiện tại

#### **Pod Count:**
```
NAME                        READY   DESIRED   AVAILABLE
ml-pipeline                 2       2         2
ml-pipeline-ui              1       1         1
```

#### **Resource Usage:**
```
NAME                           CPU(cores)   MEMORY(bytes)
ml-pipeline-xxx                450m         512Mi
ml-pipeline-yyy                420m         480Mi
```

### Bước 3: Chạy stress test

Trong Terminal 2:
```bash
./test-autoscaling.sh
```

**Script sẽ:**
1. Tìm ml-pipeline service endpoint
2. Tạo pod `load-generator`
3. Gửi nhiều requests liên tục trong 2 phút
4. Tự động cleanup sau khi xong

### Bước 4: Theo dõi autoscaling

Trong Terminal 1, bạn sẽ thấy:

**Phase 1: Before Load (0-30s)**
```
HPA: 15%/80% → 2 pods
```

**Phase 2: Load Increase (30-60s)**
```
HPA: 85%/80% → 3 pods (scaling up!)
HPA: 90%/80% → 4 pods
```

**Phase 3: Load Stable (60-120s)**
```
HPA: 70%/80% → 4 pods (stable)
```

**Phase 4: Load Decrease (120-180s)**
```
HPA: 40%/80% → 4 pods (waiting cooldown)
HPA: 30%/80% → 3 pods (scaling down)
HPA: 20%/80% → 2 pods (back to min)
```

---

## Giải thích kết quả

### Autoscaling hoạt động đúng khi:

✅ **Scale Up (tăng pods):**
- CPU vượt 80% → HPA tạo thêm pods
- Số pods tăng từ 2 → 3 → 4
- Response time giảm khi có thêm pods

✅ **Scale Down (giảm pods):**
- CPU xuống dưới 80% và giữ ổn định 5 phút
- HPA giảm pods từ 4 → 3 → 2
- Không giảm xuống dưới MINPODS (2)

✅ **Limits:**
- Không tăng quá MAXPODS (10)
- Không giảm dưới MINPODS (2)

### Autoscaling KHÔNG hoạt động khi:

❌ **Không scale up:**
- CPU vượt 80% nhưng pods không tăng
- Check: `kubectl describe hpa ml-pipeline -n kubeflow`

❌ **Không scale down:**
- CPU thấp lâu nhưng pods không giảm
- Lý do: cooldown period (default 5 phút)

❌ **Pods Pending:**
- Pods được tạo nhưng ở trạng thái Pending
- Lý do: không đủ resources trên nodes
- Check: `kubectl describe pod <pod-name> -n kubeflow`

---

## Troubleshooting

### 1. HPA không hoạt động

**Kiểm tra metrics-server:**
```bash
kubectl get deployment metrics-server -n kube-system
kubectl top nodes
```

**Nếu metrics-server không có:**
```bash
kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml
```

### 2. Pods không scale

**Check HPA events:**
```bash
kubectl describe hpa ml-pipeline -n kubeflow
```

**Check deployment:**
```bash
kubectl describe deployment ml-pipeline -n kubeflow
```

### 3. Load test không tạo load

**Check service endpoint:**
```bash
kubectl get svc ml-pipeline-ui -n kubeflow
```

**Check load-generator pod:**
```bash
kubectl get pods load-generator
kubectl logs load-generator
```

### 4. Pods Pending

**Check node resources:**
```bash
kubectl top nodes
kubectl describe nodes
```

**Check events:**
```bash
kubectl get events -n kubeflow --sort-by='.lastTimestamp'
```

---

## Lệnh nhanh để verify

### 1. Đếm pods ml-pipeline:
```bash
watch "kubectl get pods -n kubeflow -l app=ml-pipeline --no-headers | wc -l"
```

### 2. Monitor HPA realtime:
```bash
watch -n 2 "kubectl get hpa -n kubeflow"
```

### 3. Check CPU usage:
```bash
watch -n 2 "kubectl top pods -n kubeflow | grep ml-pipeline"
```

### 4. Tất cả trong một màn hình:
```bash
./monitor-autoscaling.sh
```

---

## Expected Timeline

| Time | CPU Usage | Pods | Status |
|------|-----------|------|--------|
| 0s | 15% | 2 | Initial state |
| 30s | 85% | 3 | Scaling up |
| 60s | 90% | 4 | Scaling up |
| 90s | 70% | 4 | Stable under load |
| 120s | 40% | 4 | Load test ended |
| 420s | 30% | 3 | Cooldown + scale down |
| 720s | 20% | 2 | Back to minimum |

**Note:** Scale down có cooldown period (default 5 phút), nên cần đợi lâu hơn mới thấy pods giảm.

---

## Tips

1. **Tăng load mạnh hơn:**
   - Edit `test-autoscaling.sh`
   - Giảm `sleep 0.1` thành `sleep 0.01`
   - Hoặc tăng số lượng requests

2. **Test lâu hơn:**
   - Thay `timeout 120` thành `timeout 300` (5 phút)

3. **Monitor nhiều metrics:**
   - Thêm memory monitoring
   - Check network traffic
   - Monitor database connections

4. **Production tips:**
   - Adjust CPU threshold (80% → 70%)
   - Increase MINPODS for critical services
   - Set proper resource limits
   - Monitor cost vs performance
