# Week 7: Quản lý và Tối ưu Kubernetes Cluster

## Mục tiêu
Sau khi hoàn thành, bạn sẽ biết cách:
- Deploy và quản lý ứng dụng web nginx trên cluster
- Thêm node mới vào cluster
- Xóa node khỏi cluster một cách an toàn
- Kiểm thử shutdown node và xem tác động
- Thực hiện rolling upgrade nodes để tránh downtime
- Mô phỏng node die và kiểm tra cơ chế tự động reschedule

**Yêu cầu:**
- Đã hoàn thành Week 6 (Cluster 3 nodes đã chạy)
- Master node 1: 10.105.196.111
- Master node 2: 10.105.196.112
- Master node 3: 10.105.196.113

---

## PHẦN 1: DEPLOY ỨNG DỤNG DEMO NGINX

### Bước 1.1: Tạo Deployment Nginx với 3 replicas

**Trên Master Node 1:**

```bash
# SSH vào master node
ssh root@10.105.196.111

# Tạo namespace cho demo
kubectl create namespace nginx-demo

# Tạo file deployment
cat <<'EOF' > nginx-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: nginx-demo
  namespace: nginx-demo
  labels:
    app: nginx
spec:
  replicas: 3
  selector:
    matchLabels:
      app: nginx
  template:
    metadata:
      labels:
        app: nginx
    spec:
      containers:
      - name: nginx
        image: nginx:1.25
        ports:
        - containerPort: 80
        resources:
          requests:
            memory: "64Mi"
            cpu: "100m"
          limits:
            memory: "128Mi"
            cpu: "200m"
---
apiVersion: v1
kind: Service
metadata:
  name: nginx-service
  namespace: nginx-demo
spec:
  type: NodePort
  selector:
    app: nginx
  ports:
  - port: 80
    targetPort: 80
    nodePort: 30080
EOF

# Apply deployment
kubectl apply -f nginx-deployment.yaml
```

### Bước 1.2: Kiểm tra deployment

```bash
# Xem deployment
kubectl get deployments -n nginx-demo

# Kết quả mong đợi:
# NAME         READY   UP-TO-DATE   AVAILABLE   AGE
# nginx-demo   3/3     3            3           1m

# Xem pods và node chúng đang chạy
kubectl get pods -n nginx-demo -o wide

# Kết quả:
# NAME                          READY   STATUS    NODE
# nginx-demo-xxxx-yyy           1/1     Running   k8s-master-1
# nginx-demo-xxxx-zzz           1/1     Running   k8s-master-2
# nginx-demo-xxxx-aaa           1/1     Running   k8s-master-3

# Xem service
kubectl get svc -n nginx-demo

# Test truy cập nginx
curl http://10.105.196.111:30080
# Kết quả: Welcome to nginx!
```

### Bước 1.3: Tạo script giám sát pods

```bash
# Tạo script để theo dõi pods real-time
cat <<'EOF' > ~/monitor-pods.sh
#!/bin/bash
while true; do
  clear
  echo "=== Nginx Pods Status ==="
  echo "Time: $(date)"
  echo ""
  kubectl get pods -n nginx-demo -o wide
  echo ""
  echo "=== Node Status ==="
  kubectl get nodes
  sleep 5
done
EOF

chmod +x ~/monitor-pods.sh

# Chạy trong terminal riêng
# ~/monitor-pods.sh
```

**CHECKPOINT PHẦN 1**:
- [ ] Nginx deployment đã tạo với 3 replicas
- [ ] Service NodePort đã expose ở port 30080
- [ ] Tất cả 3 pods đang Running trên các nodes khác nhau
- [ ] Có thể truy cập nginx qua browser: http://10.105.196.111:30080

---

## PHẦN 2: THÊM NODE MỚI VÀO CLUSTER

### Bước 2.1: Chuẩn bị node mới (Node 4)

**Giả sử bạn có node mới với IP: 10.105.196.114**

**Trên Node 4 (10.105.196.114):**

```bash
# SSH vào node 4
ssh root@10.105.196.114

# Enable SSH root (nếu chưa)
nano /etc/ssh/sshd_config
# Set: PermitRootLogin yes
systemctl restart sshd

# Cấu hình IP tĩnh
nano /etc/netplan/00-installer-config.yaml
# Cấu hình:
network:
  ethernets:
    ens33:
      dhcp4: no
      addresses:
        - 10.105.196.114/24
      gateway4: 10.105.196.1
      nameservers:
        addresses:
          - 8.8.8.8
          - 8.8.4.4
  version: 2

netplan apply

# Set hostname
hostnamectl set-hostname k8s-worker-1

# Cấu hình /etc/hosts
cat <<EOF >> /etc/hosts
10.105.196.111 k8s-master-1
10.105.196.112 k8s-master-2
10.105.196.113 k8s-master-3
10.105.196.114 k8s-worker-1
EOF

# Disable swap
swapoff -a
sed -i '/ swap / s/^\(.*\)$/#\1/g' /etc/fstab
```

### Bước 2.2: Thêm node vào Kubespray inventory

**Trên Master Node 1:**

```bash
ssh root@10.105.196.111

# Copy SSH key đến node mới
ssh-copy-id -i ~/.ssh/id_ed25519.pub root@10.105.196.114

# Test SSH
ssh root@10.105.196.114 "hostname"
# Kết quả: k8s-worker-1

# Chỉnh sửa hosts.ini
cd ~/kubespray
nano inventory/mycluster/hosts.ini

# Thêm node mới vào file:
[all]
k8s-master-1 ansible_host=10.105.196.111 ip=10.105.196.111
k8s-master-2 ansible_host=10.105.196.112 ip=10.105.196.112
k8s-master-3 ansible_host=10.105.196.113 ip=10.105.196.113
k8s-worker-1 ansible_host=10.105.196.114 ip=10.105.196.114

[kube-master]
k8s-master-1

[kube-node]
k8s-master-1
k8s-master-2
k8s-master-3
k8s-worker-1

[etcd]
k8s-master-1

[k8s-cluster:children]
kube-node
kube-master

[calico-rr]

[vault]
k8s-master-1

# Lưu file
```

### Bước 2.3: Chạy playbook để thêm node

```bash
# Activate venv
cd ~/kubespray
source venv/bin/activate

# Test Ansible connectivity
ansible all -i inventory/mycluster/hosts.ini -m ping

# Chạy scale playbook
ansible-playbook -i inventory/mycluster/hosts.ini scale.yml -b -v

# Quá trình này mất 5-10 phút
```

### Bước 2.4: Kiểm tra node mới

```bash
# Xem nodes
kubectl get nodes

# Kết quả mong đợi (4 nodes):
# NAME           STATUS   ROLES           AGE   VERSION
# k8s-master-1   Ready    control-plane   1d    v1.28.x
# k8s-master-2   Ready    <none>          1d    v1.28.x
# k8s-master-3   Ready    <none>          1d    v1.28.x
# k8s-worker-1   Ready    <none>          2m    v1.28.x

# Xem chi tiết node mới
kubectl describe node k8s-worker-1

# Xem pods nginx sau khi thêm node
kubectl get pods -n nginx-demo -o wide
```

### Bước 2.5: Scale deployment để sử dụng node mới

```bash
# Scale lên 6 replicas
kubectl scale deployment nginx-demo --replicas=6 -n nginx-demo

# Xem pods phân bố
kubectl get pods -n nginx-demo -o wide

# Pods sẽ được schedule lên node mới
```

**CHECKPOINT PHẦN 2**:
- [ ] Node mới (k8s-worker-1) đã thêm vào cluster
- [ ] Node mới có STATUS=Ready
- [ ] Pods có thể schedule lên node mới
- [ ] Deployment scale lên 6 replicas thành công

---

## PHẦN 3: XÓA NODE KHỎI CLUSTER

### Bước 3.1: Drain node (di chuyển pods ra khỏi node)

**Giả sử muốn xóa k8s-worker-1:**

```bash
# Trên Master Node 1

# Drain node (di chuyển tất cả pods ra khỏi node)
kubectl drain k8s-worker-1 --ignore-daemonsets --delete-emptydir-data

# Quá trình drain:
# - Pods sẽ được terminate trên node này
# - Pods sẽ được recreate trên các nodes khác
# - Node sẽ được mark là SchedulingDisabled

# Xem pods đã chuyển chưa
kubectl get pods -n nginx-demo -o wide
# Không còn pod nào trên k8s-worker-1

# Xem node status
kubectl get nodes
# k8s-worker-1 hiển thị: Ready,SchedulingDisabled
```

### Bước 3.2: Xóa node khỏi cluster

```bash
# Xóa node khỏi cluster
kubectl delete node k8s-worker-1

# Xem nodes còn lại
kubectl get nodes
# Chỉ còn 3 nodes: master-1, master-2, master-3
```

### Bước 3.3: Cleanup trên node bị xóa (optional)

**Trên Node 4 (k8s-worker-1):**

```bash
ssh root@10.105.196.114

# Reset node về trạng thái clean
kubeadm reset -f

# Xóa config files
rm -rf /etc/kubernetes/
rm -rf ~/.kube/
rm -rf /var/lib/kubelet/
rm -rf /var/lib/etcd/
```

### Bước 3.4: Xóa khỏi Kubespray inventory

**Trên Master Node 1:**

```bash
cd ~/kubespray
nano inventory/mycluster/hosts.ini

# Xóa dòng k8s-worker-1 khỏi [all] và [kube-node]
# Lưu file
```

**CHECKPOINT PHẦN 3**:
- [ ] Node đã được drain thành công (pods di chuyển)
- [ ] Node đã bị xóa khỏi cluster
- [ ] Deployment vẫn chạy bình thường trên các nodes còn lại

---

## PHẦN 4: KIỂM THỬ SHUTDOWN MỘT NODE

### Bước 4.1: Mở 2 terminals để giám sát

**Terminal 1 - Giám sát pods:**
```bash
ssh root@10.105.196.111
watch -n 2 'kubectl get pods -n nginx-demo -o wide'
```

**Terminal 2 - Giám sát nodes:**
```bash
ssh root@10.105.196.111
watch -n 2 'kubectl get nodes'
```

### Bước 4.2: Shutdown node k8s-master-3

**Trên Node 3:**
```bash
# SSH vào node 3
ssh root@10.105.196.113

# Shutdown node
shutdown -h now
```

### Bước 4.3: Quan sát hành vi của cluster

**Sau khi shutdown, quan sát trên Terminal 1 và 2:**

**Sau ~1 phút:**
- Node k8s-master-3 chuyển sang status: NotReady
- Pods trên node này vẫn hiển thị Running (chưa bị xóa)

**TẠI SAO POD VẪN RUNNING KHI NODE ĐÃ TẮT?**

Đây là hành vi BÌNH THƯỜNG của Kubernetes. Giải thích:

1. **kubectl get pods lấy thông tin từ etcd database**, KHÔNG phải từ node thực tế
2. **Khi node tắt đột ngột:**
   - Node không thể gửi heartbeat về API server
   - Kubelet trên node không thể cập nhật trạng thái pod
   - etcd database vẫn lưu trạng thái cũ là "Running"

3. **Kubernetes không update trạng thái pod ngay lập tức vì:**
   - Tránh false positive (node tạm thời mất kết nối mạng)
   - Tránh xóa pod khi node có thể khôi phục nhanh
   - Chờ đợi thời gian grace period (5 phút mặc định)

4. **kubectl chỉ hiển thị trạng thái từ etcd**, không kiểm tra pod có thật sự chạy hay không

**Sơ đồ luồng xử lý:**
```
T+0s:  Node 3 shutdown
       |
       v
T+40s: API Server nhận thấy node không heartbeat
       |
       v
       Node Status: Ready -> NotReady
       |
       v
       Pod Status: VẪN LÀ "Running" (trong etcd)
       |
       v
T+5m:  Pod Eviction Timeout đạt ngưỡng
       |
       v
       Pods trên Node 3: Running -> Terminating
       |
       v
       Deployment Controller: Phát hiện thiếu replicas
       |
       v
       Tạo Pods mới trên Node 1 và Node 2
       |
       v
T+6m:  Pods mới: Pending -> Running
```

**Sau ~5 phút:**
- Kubernetes phát hiện node down quá lâu (vượt quá pod-eviction-timeout)
- Pods trên node k8s-master-3 chuyển sang Terminating
- Deployment controller tạo pods mới trên các nodes còn lại
- Pods mới chuyển sang Running

```bash
# Xem pods sau khi reschedule
kubectl get pods -n nginx-demo -o wide

# Tất cả pods đã chạy trên k8s-master-1 và k8s-master-2
# Không còn pod nào trên k8s-master-3
```

### Bước 4.4: Khởi động lại node

**Bật lại máy k8s-master-3:**
- Boot lại node 3
- SSH vào: `ssh root@10.105.196.113`

```bash
# Kiểm tra kubelet
systemctl status kubelet

# Nếu kubelet không chạy, restart
systemctl restart kubelet

# Trên Master Node 1, xem node status
kubectl get nodes
# k8s-master-3 sẽ chuyển về Ready sau 1-2 phút
```

**CHECKPOINT PHẦN 4**:
- [ ] Đã shutdown node k8s-master-3
- [ ] Kubernetes tự động reschedule pods sang nodes khác
- [ ] Deployment vẫn có đủ 3 replicas running
- [ ] Node khôi phục và rejoin cluster thành công

---

## PHẦN 5: ROLLING UPGRADE NODES

### Bước 5.1: Chuẩn bị rolling upgrade

**Mục tiêu:** Upgrade Kubernetes version mà không downtime

**Chiến lược:**
1. Upgrade từng node một
2. Drain node trước khi upgrade
3. Upgrade kubelet và kubectl
4. Uncordon node sau khi upgrade

### Bước 5.2: Upgrade Node 2 (k8s-master-2)

**Trên Master Node 1:**
```bash
# Drain node 2
kubectl drain k8s-master-2 --ignore-daemonsets --delete-emptydir-data

# Pods sẽ chuyển sang master-1 và master-3
watch kubectl get pods -n nginx-demo -o wide
```

**Trên Node 2:**
```bash
ssh root@10.105.196.112

# Giả sử upgrade từ v1.28.5 lên v1.28.6
# Update package list
apt update

# Kiểm tra version mới
apt-cache madison kubeadm | head -5

# Upgrade kubeadm
apt-mark unhold kubeadm
apt install -y kubeadm=1.28.6-00
apt-mark hold kubeadm

# Upgrade node
kubeadm upgrade node

# Upgrade kubelet và kubectl
apt-mark unhold kubelet kubectl
apt install -y kubelet=1.28.6-00 kubectl=1.28.6-00
apt-mark hold kubelet kubectl

# Restart kubelet
systemctl daemon-reload
systemctl restart kubelet

# Kiểm tra version
kubelet --version
```

**Trên Master Node 1:**
```bash
# Uncordon node 2
kubectl uncordon k8s-master-2

# Xem node version
kubectl get nodes -o wide
# k8s-master-2 hiển thị VERSION: v1.28.6

# Pods sẽ tự động schedule trở lại
```

### Bước 5.3: Lặp lại cho Node 3

**Tương tự, upgrade k8s-master-3:**
```bash
# Drain
kubectl drain k8s-master-3 --ignore-daemonsets --delete-emptydir-data

# SSH vào node 3 và upgrade (tương tự bước 5.2)

# Uncordon
kubectl uncordon k8s-master-3
```

### Bước 5.4: Kiểm tra sau upgrade

```bash
# Xem tất cả nodes
kubectl get nodes -o wide

# Tất cả nodes đã upgrade:
# NAME           STATUS   VERSION
# k8s-master-1   Ready    v1.28.5
# k8s-master-2   Ready    v1.28.6
# k8s-master-3   Ready    v1.28.6

# Kiểm tra nginx vẫn hoạt động
curl http://10.105.196.111:30080

# Xem pods
kubectl get pods -n nginx-demo
# Tất cả pods vẫn Running
```

**CHECKPOINT PHẦN 5**:
- [ ] Đã upgrade node 2 và node 3 thành công
- [ ] Không có downtime trong quá trình upgrade
- [ ] Tất cả nodes hiển thị version mới
- [ ] Deployment nginx vẫn chạy bình thường

---

## PHẦN 6: MÔ PHỎNG NODE DIE VÀ KIỂM TRA RESCHEDULE

### Bước 6.1: Chuẩn bị monitoring

**Terminal 1 - Continuous monitoring:**
```bash
ssh root@10.105.196.111

# Tạo script monitoring chi tiết
cat <<'EOF' > ~/monitor-reschedule.sh
#!/bin/bash
LOG_FILE="/tmp/pod-reschedule.log"
> $LOG_FILE

echo "=== Starting Continuous Monitoring ===" | tee -a $LOG_FILE
while true; do
  TIMESTAMP=$(date "+%Y-%m-%d %H:%M:%S")
  echo "" | tee -a $LOG_FILE
  echo "[$TIMESTAMP] === Pod Status ===" | tee -a $LOG_FILE
  kubectl get pods -n nginx-demo -o wide | tee -a $LOG_FILE
  echo "" | tee -a $LOG_FILE
  echo "[$TIMESTAMP] === Node Status ===" | tee -a $LOG_FILE
  kubectl get nodes | tee -a $LOG_FILE
  sleep 10
done
EOF

chmod +x ~/monitor-reschedule.sh
~/monitor-reschedule.sh
```

**Terminal 2 - Test connection:**
```bash
ssh root@10.105.196.111

# Test continuous connection
while true; do
  TIMESTAMP=$(date "+%H:%M:%S")
  RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" http://10.105.196.111:30080)
  echo "[$TIMESTAMP] HTTP Response: $RESPONSE"
  sleep 2
done
```

### Bước 6.2: Mô phỏng node die đột ngột

**Cách 1: Tắt network interface (mô phỏng mất kết nối mạng):**
```bash
# SSH vào node 3
ssh root@10.105.196.113

# Tắt network interface
ip link set ens33 down

# Node sẽ bị mất kết nối ngay lập tức
```

**Cách 2: Kill kubelet process:**
```bash
ssh root@10.105.196.113

# Kill kubelet
systemctl stop kubelet

# Stop containerd
systemctl stop containerd
```

**Cách 3: Shutdown hard (giả lập power failure):**
```bash
# Từ hypervisor (VMware/VirtualBox), force power off VM
# Hoặc dùng:
echo 1 > /proc/sys/kernel/sysrq
echo b > /proc/sysrq-trigger
```

### Bước 6.3: Quan sát quá trình reschedule

**Timeline thực tế:**

**T+0s (Node die):**
- Node k8s-master-3 mất kết nối
- Pods trên node vẫn hiển thị Running

**T+40s:**
- Master node phát hiện node không respond
- Node status chuyển sang NotReady

**T+5m:**
- Kubernetes đợi 5 phút (default pod eviction timeout)
- Pods trên node chuyển sang Terminating

**T+5m30s:**
- Deployment controller tạo pods mới
- Pods mới được schedule lên k8s-master-1 và k8s-master-2
- Pods mới pull image và start

**T+6m:**
- Pods mới chạy và sẵn sàng nhận traffic
- Service tự động route traffic đến pods mới

```bash
# Xem chi tiết events
kubectl get events -n nginx-demo --sort-by='.lastTimestamp'

# Xem pod reschedule history
kubectl get pods -n nginx-demo -o yaml | grep -A5 "events"
```

### Bước 6.4: Phân tích kết quả

```bash
# Xem log monitoring
cat /tmp/pod-reschedule.log

# Tóm tắt:
# - Thời gian phát hiện node down: ~40s
# - Thời gian chờ trước khi evict pods: 5 phút
# - Thời gian tạo và start pod mới: ~30s
# - Tổng downtime: ~5m30s-6m

# Xem distribution pods mới
kubectl get pods -n nginx-demo -o wide
# Pods đã được phân bổ lại trên 2 nodes còn lại
```

**GIẢI THÍCH KỸ THUẬT VỀ QUÁ TRÌNH RESCHEDULE:**

**1. Tại sao phải đợi 5 phút?**
- Tham số `--pod-eviction-timeout` trong kube-controller-manager (mặc định: 5m)
- Mục đích: Tránh xóa pod khi node tạm thời mất kết nối (network glitch, restart nhanh)
- Nếu node khôi phục trong 5 phút, pods không bị xóa

**2. Components tham gia:**
- **Node Controller**: Theo dõi node health, update node status
- **kubelet**: Gửi heartbeat mỗi 10s (--node-status-update-frequency=10s)
- **API Server**: Nhận heartbeat, cập nhật node status
- **Deployment Controller**: Theo dõi số lượng replicas, tạo pod mới khi thiếu
- **Scheduler**: Chọn node phù hợp cho pod mới

**3. Các timeout quan trọng:**
```bash
# Node status update frequency (kubelet)
--node-status-update-frequency=10s

# Node monitor grace period (node controller)
--node-monitor-grace-period=40s

# Pod eviction timeout (node controller)
--pod-eviction-timeout=5m

# Toleration cho node NotReady (pod)
tolerations:
- key: "node.kubernetes.io/not-ready"
  operator: "Exists"
  effect: "NoExecute"
  tolerationSeconds: 300
```

**4. Làm thế nào để pod THẬT SỰ biết node die?**

Pod KHÔNG THỂ tự biết node die! Vì:
- Container đang chạy trên node đã tắt
- Container process đã bị kill
- Pod chỉ là một object trong etcd database

Chỉ có **API Server + Node Controller** biết node die thông qua:
- Mất heartbeat từ kubelet
- Không thể kết nối TCP đến kubelet port (10250)

### Bước 6.5: Giảm thời gian reschedule (Optional)

**Để giảm thời gian downtime, có thể giảm pod eviction timeout:**

```bash
# Edit kube-controller-manager
kubectl edit -n kube-system deployment kube-controller-manager

# Thêm flag:
# --pod-eviction-timeout=1m

# Hoặc edit trong kubespray inventory trước khi deploy:
# pod_eviction_timeout: 1m
```

**CHECKPOINT PHẦN 6**:
- [ ] Đã mô phỏng node die đột ngột
- [ ] Quan sát được timeline reschedule (~5-6 phút)
- [ ] Pods tự động recreate trên nodes khác
- [ ] Service vẫn hoạt động (có downtime ~5-6 phút)

---

## PHẦN 7: KHÔI PHỤC VÀ BEST PRACTICES

### Bước 7.1: Khôi phục node đã die

**Bật lại node k8s-master-3:**

```bash
# Boot lại máy
# SSH vào
ssh root@10.105.196.113

# Kiểm tra các service
systemctl status kubelet
systemctl status containerd

# Nếu network bị down, bật lại
ip link set ens33 up

# Restart services nếu cần
systemctl restart kubelet

# Trên Master Node 1, kiểm tra
kubectl get nodes
# k8s-master-3 chuyển về Ready
```

### Bước 7.2: Best practices để giảm downtime

**1. Sử dụng Pod Disruption Budgets (PDB):**

```bash
cat <<'EOF' > nginx-pdb.yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: nginx-pdb
  namespace: nginx-demo
spec:
  minAvailable: 2
  selector:
    matchLabels:
      app: nginx
EOF

kubectl apply -f nginx-pdb.yaml

# PDB đảm bảo luôn có ít nhất 2 pods running
```

**2. Sử dụng Health Checks:**

```bash
# Chỉnh sửa deployment với liveness và readiness probes
kubectl edit deployment nginx-demo -n nginx-demo

# Thêm vào container spec:
livenessProbe:
  httpGet:
    path: /
    port: 80
  initialDelaySeconds: 5
  periodSeconds: 5
readinessProbe:
  httpGet:
    path: /
    port: 80
  initialDelaySeconds: 5
  periodSeconds: 5
```

**3. Sử dụng Pod Anti-affinity:**

```bash
# Đảm bảo pods không chạy trên cùng node
kubectl edit deployment nginx-demo -n nginx-demo

# Thêm vào pod spec:
affinity:
  podAntiAffinity:
    preferredDuringSchedulingIgnoredDuringExecution:
    - weight: 100
      podAffinityTerm:
        labelSelector:
          matchLabels:
            app: nginx
        topologyKey: kubernetes.io/hostname
```

**4. Scale deployment nhiều replicas hơn:**

```bash
# Scale lên 5 replicas
kubectl scale deployment nginx-demo --replicas=5 -n nginx-demo

# Với 5 replicas trên 3 nodes, luôn có backup
```

### Bước 7.3: Tóm tắt các thao tác đã học

**Quản lý Nodes:**
```bash
# Thêm node
ansible-playbook -i inventory/mycluster/hosts.ini scale.yml -b

# Drain node (di chuyển pods)
kubectl drain <node-name> --ignore-daemonsets --delete-emptydir-data

# Xóa node
kubectl delete node <node-name>

# Uncordon node (cho phép schedule lại)
kubectl uncordon <node-name>

# Cordon node (ngăn schedule mới)
kubectl cordon <node-name>
```

**Monitoring:**
```bash
# Xem nodes
kubectl get nodes -o wide

# Xem pods và nodes
kubectl get pods -n <namespace> -o wide

# Xem events
kubectl get events -n <namespace> --sort-by='.lastTimestamp'

# Describe node
kubectl describe node <node-name>

# Top nodes (resource usage)
kubectl top nodes
```

**CHECKPOINT PHẦN 7**:
- [ ] Node đã khôi phục và rejoin cluster
- [ ] Đã áp dụng PDB cho deployment
- [ ] Đã thêm health checks
- [ ] Hiểu rõ timeline và cơ chế reschedule

---

## PHỤ LỤC: SCRIPTS TIỆN ÍCH

### Script 1: Quick cluster health check

```bash
cat <<'EOF' > ~/quick-health-check.sh
#!/bin/bash
echo "=== Cluster Health Check ==="
echo ""
echo "Nodes:"
kubectl get nodes
echo ""
echo "Nginx Pods:"
kubectl get pods -n nginx-demo -o wide
echo ""
echo "Nginx Service:"
kubectl get svc -n nginx-demo
echo ""
echo "Testing Nginx:"
curl -s http://10.105.196.111:30080 | head -5
EOF

chmod +x ~/quick-health-check.sh
```

### Script 2: Simulate load

```bash
cat <<'EOF' > ~/load-test.sh
#!/bin/bash
echo "Sending 100 requests to nginx..."
for i in {1..100}; do
  RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" http://10.105.196.111:30080)
  echo "Request $i: $RESPONSE"
  sleep 0.1
done
echo "Load test complete!"
EOF

chmod +x ~/load-test.sh
```

### Script 3: Auto-recovery test

```bash
cat <<'EOF' > ~/test-auto-recovery.sh
#!/bin/bash
echo "=== Testing Auto-Recovery ==="
echo "1. Current state:"
kubectl get pods -n nginx-demo -o wide

echo ""
echo "2. Killing one pod..."
POD=$(kubectl get pods -n nginx-demo -o name | head -1)
kubectl delete $POD -n nginx-demo

echo ""
echo "3. Waiting for recovery..."
sleep 10

echo ""
echo "4. New state:"
kubectl get pods -n nginx-demo -o wide

echo ""
echo "Recovery successful!"
EOF

chmod +x ~/test-auto-recovery.sh
```

---

## KẾT LUẬN

Chúc mừng! Bạn đã hoàn thành Week 7 và học được:

**Đã thực hành:**
- Deploy ứng dụng nginx với 3 replicas
- Thêm node mới vào cluster
- Xóa node khỏi cluster an toàn (drain → delete)
- Kiểm thử shutdown node và quan sát reschedule
- Rolling upgrade nodes không downtime
- Mô phỏng node die và kiểm tra tự động recovery

**Kiến thức quan trọng:**
- **Pod Eviction Timeout**: ~5 phút (default)
- **Node Status Check**: ~40 giây
- **Reschedule Time**: ~5-6 phút tổng cộng
- **Best Practices**: PDB, Health Checks, Anti-affinity, Multiple replicas

**Các bước tiếp theo:**
1. Tìm hiểu về StatefulSets cho stateful apps
2. Cài đặt monitoring (Prometheus + Grafana)
3. Setup auto-scaling (HPA)
4. Implement service mesh (Istio/Linkerd)
5. Backup và disaster recovery strategies

**Tài liệu tham khảo:**
- Kubernetes Best Practices: https://kubernetes.io/docs/concepts/cluster-administration/
- Pod Disruption Budgets: https://kubernetes.io/docs/tasks/run-application/configure-pdb/
- Node Management: https://kubernetes.io/docs/concepts/architecture/nodes/

---

**HOÀN THÀNH WEEK 7!** Bạn đã nắm vững quản lý và tối ưu Kubernetes cluster!
