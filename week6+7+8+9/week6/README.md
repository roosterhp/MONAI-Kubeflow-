# Hướng dẫn Cài đặt Kubernetes Cluster với Kubespray

## Mục tiêu
Sau khi hoàn thành, bạn sẽ có:
- Kubernetes cluster 3 nodes chạy high availability (HA)
- Control plane được replicate trên 3 master nodes
- etcd cluster để đảm bảo tính sẵn sàng cao
- Cluster sẵn sàng cho production workloads

**Cấu hình cluster:**
- Master node 1: 10.105.196.111
- Master node 2: 10.105.196.112
- Master node 3: 10.105.196.113

---

## PHẦN 1: CHUẨN BỊ VÀ CẤU HÌNH NETWORK CHO TẤT CẢ 3 NODES

### Bước 1.1: Enable SSH cho user root

**Thực hiện trên TẤT CẢ 3 nodes (111, 112, 113):**

```bash
# SSH vào từng node (dùng user thường trước)
ssh username@10.105.196.111  # Node 1
# Lặp lại cho Node 2 và 3

# Trên MỖI node, chỉnh sửa SSH config
sudo nano /etc/ssh/sshd_config

# Tìm và sửa các dòng sau:
PermitRootLogin yes
PasswordAuthentication yes

# Lưu file (Ctrl+O, Enter, Ctrl+X)

# Restart SSH service
sudo systemctl restart sshd

# Set password cho root (nếu chưa có)
sudo passwd root
```

**Kiểm tra:**
```bash
# Test SSH với root
ssh root@10.105.196.111
# Phải login được
```

### Bước 1.2: Cấu hình IP tĩnh (Static IP) để không tự động cấp phát DHCP

**Trên Master Node 1 (10.105.196.111):**

```bash
# SSH vào node 1 với root
ssh root@10.105.196.111

# Kiểm tra tên network interface
ip a

# Giả sử interface là ens33 hoặc eth0, chỉnh sửa netplan
sudo nano /etc/netplan/00-installer-config.yaml

# Cấu hình như sau (thay ens33 bằng interface thực tế):
network:
  ethernets:
    ens33:
      dhcp4: no
      addresses:
        - 10.105.196.111/24
      gateway4: 10.105.196.1
      nameservers:
        addresses:
          - 8.8.8.8
          - 8.8.4.4
  version: 2

# Lưu file và apply
sudo netplan apply

# Kiểm tra IP
ip a | grep 10.105.196.111
```

**Trên Master Node 2 (10.105.196.112):**

```bash
ssh root@10.105.196.112

sudo nano /etc/netplan/00-installer-config.yaml

# Cấu hình:
network:
  ethernets:
    ens33:
      dhcp4: no
      addresses:
        - 10.105.196.112/24
      gateway4: 10.105.196.1
      nameservers:
        addresses:
          - 8.8.8.8
          - 8.8.4.4
  version: 2

sudo netplan apply
```

**Trên Master Node 3 (10.105.196.113):**

```bash
ssh root@10.105.196.113

sudo nano /etc/netplan/00-installer-config.yaml

# Cấu hình:
network:
  ethernets:
    ens33:
      dhcp4: no
      addresses:
        - 10.105.196.113/24
      gateway4: 10.105.196.1
      nameservers:
        addresses:
          - 8.8.8.8
          - 8.8.4.4
  version: 2

sudo netplan apply
```

### Bước 1.3: Cấu hình /etc/hosts trên TẤT CẢ 3 nodes

**Trên TẤT CẢ 3 nodes, chỉnh sửa /etc/hosts:**

```bash
# Trên Node 1
ssh root@10.105.196.111
sudo nano /etc/hosts

# Nội dung file /etc/hosts:
127.0.0.1       localhost
127.0.1.1       k8s-master-1

10.105.196.111 k8s-master-1
10.105.196.112 k8s-master-2
10.105.196.113 k8s-master-3

# The following lines are desirable for IPv6 capable hosts
::1             ip6-localhost ip6-loopback
ff00::0         ip6-localnet
ff00::0         ip6-mcastprefix
ff02::1         ip6-allnodes
ff02::2         ip6-allrouters
```

**Lưu và làm tương tự cho Node 2:**

```bash
ssh root@10.105.196.112
sudo nano /etc/hosts

# Nội dung file /etc/hosts (chỉ khác dòng 127.0.1.1):
127.0.0.1       localhost
127.0.1.1       k8s-master-2

10.105.196.111 k8s-master-1
10.105.196.112 k8s-master-2
10.105.196.113 k8s-master-3

::1             ip6-localhost ip6-loopback
ff00::0         ip6-localnet
ff00::0         ip6-mcastprefix
ff02::1         ip6-allnodes
ff02::2         ip6-allrouters
```

**Lưu và làm tương tự cho Node 3:**

```bash
ssh root@10.105.196.113
sudo nano /etc/hosts

# Nội dung file /etc/hosts:
127.0.0.1       localhost
127.0.1.1       k8s-master-3

10.105.196.111 k8s-master-1
10.105.196.112 k8s-master-2
10.105.196.113 k8s-master-3

::1             ip6-localhost ip6-loopback
ff00::0         ip6-localnet
ff00::0         ip6-mcastprefix
ff02::1         ip6-allnodes
ff02::2         ip6-allrouters
```

**Kiểm tra:**
```bash
# Từ bất kỳ node nào, ping các nodes khác
ping -c 2 k8s-master-1
ping -c 2 k8s-master-2
ping -c 2 k8s-master-3
```

### Bước 1.4: Set hostname cho từng node

**Trên Node 1:**
```bash
ssh root@10.105.196.111
sudo hostnamectl set-hostname k8s-master-1
```

**Trên Node 2:**
```bash
ssh root@10.105.196.112
sudo hostnamectl set-hostname k8s-master-2
```

**Trên Node 3:**
```bash
ssh root@10.105.196.113
sudo hostnamectl set-hostname k8s-master-3
```

** CHECKPOINT PHẦN 1**:
- [ ] SSH với root hoạt động trên cả 3 nodes
- [ ] IP tĩnh đã cấu hình (10.105.196.111, 112, 113)
- [ ] /etc/hosts đã cấu hình đúng trên cả 3 nodes
- [ ] Hostname đã set đúng
- [ ] Ping được giữa các nodes

---

## PHẦN 2: DISABLE SWAP TRÊN TẤT CẢ 3 NODES

**Kubernetes yêu cầu swap phải bị disable.**

**Thực hiện trên TẤT CẢ 3 nodes:**

```bash
# Trên từng node (111, 112, 113)
ssh root@10.105.196.111  # Node 1
# Lặp lại cho Node 2 và 3

# Disable swap ngay lập tức
swapoff -a

# Disable swap vĩnh viễn (comment dòng swap trong /etc/fstab)
sed -i '/ swap / s/^\(.*\)$/#\1/g' /etc/fstab

# Kiểm tra swap đã tắt
free -h
# Dòng Swap phải hiển thị: Swap: 0B 0B 0B

# Xem /etc/fstab để confirm
cat /etc/fstab | grep swap
# Dòng swap phải bị comment (#)
```

** CHECKPOINT PHẦN 2**:
- [ ] Swap đã disable trên cả 3 nodes (free -h shows 0B)
- [ ] /etc/fstab đã comment dòng swap

---

## PHẦN 3: CÀI ĐẶT ANSIBLE TRÊN MASTER NODE 1

### Bước 3.1: Cài đặt Python và Ansible

**Trên Master Node 1 (10.105.196.111) ONLY:**

```bash
# SSH vào node 1
ssh root@10.105.196.111

# Update package list
apt update

# Cài Python và pip
apt install -y python3 python3-pip python3-venv

# Cài Ansible qua pip
pip3 install ansible

# Hoặc cài Ansible qua apt
apt install -y ansible

# Kiểm tra Ansible version
ansible --version
# Phải thấy: ansible [core 2.x.x] hoặc cao hơn
```

** CHECKPOINT PHẦN 3**:
- [ ] Python3 đã cài đặt trên Master 1
- [ ] Ansible đã cài đặt trên Master 1
- [ ] ansible --version hoạt động

---

## PHẦN 4: TẠO SSH KEY VÀ CHIA SẺ ĐẾN CÁC NODES

### Bước 4.1: Tạo SSH key trên Master Node 1

**Trên Master Node 1:**

```bash
ssh root@10.105.196.111

# Tạo SSH key (ed25519 - bảo mật cao)
ssh-keygen -t ed25519 -C "k8s-cluster-admin" -f ~/.ssh/id_ed25519 -N ""

# Hoặc dùng RSA nếu muốn
# ssh-keygen -t rsa -b 4096 -f ~/.ssh/id_rsa -N ""

# Kiểm tra key đã tạo
ls -la ~/.ssh/
# Phải thấy: id_ed25519 (private key) và id_ed25519.pub (public key)
```

### Bước 4.2: Copy SSH key đến các nodes khác

```bash
# Vẫn trên Master Node 1

# Copy key đến chính Node 1 (localhost)
ssh-copy-id -i ~/.ssh/id_ed25519.pub root@10.105.196.111
# Nhập password root của node 1

# Copy key đến Node 2
ssh-copy-id -i ~/.ssh/id_ed25519.pub root@10.105.196.112
# Nhập password root của node 2

# Copy key đến Node 3
ssh-copy-id -i ~/.ssh/id_ed25519.pub root@10.105.196.113
# Nhập password root của node 3
```

### Bước 4.3: Test SSH passwordless

```bash
# Từ Master Node 1, test kết nối không cần password

ssh root@10.105.196.111 "hostname"
# Kết quả: k8s-master-1 (KHÔNG hỏi password)

ssh root@10.105.196.112 "hostname"
# Kết quả: k8s-master-2 (KHÔNG hỏi password)

ssh root@10.105.196.113 "hostname"
# Kết quả: k8s-master-3 (KHÔNG hỏi password)
```

** CHECKPOINT PHẦN 4**:
- [ ] SSH key đã tạo trên Master 1
- [ ] SSH key đã copy đến tất cả nodes
- [ ] SSH passwordless hoạt động (không hỏi password)

---

## PHẦN 5: CLONE KUBESPRAY VÀ CẤU HÌNH

### Bước 5.1: Clone Kubespray repository

**Trên Master Node 1:**

```bash
# Di chuyển về thư mục home
cd ~

# Clone Kubespray
git clone https://github.com/kubernetes-sigs/kubespray.git

# Di chuyển vào thư mục Kubespray
cd kubespray

# Checkout version ổn định (v2.24)
git checkout release-2.24

# Kiểm tra branch
git branch
# Phải thấy: * release-2.24
```

### Bước 5.2: Cài đặt dependencies

```bash
# Vẫn trong thư mục kubespray
cd ~/kubespray

# Tạo virtual environment (recommended)
python3 -m venv venv

# Activate venv
source venv/bin/activate

# Cài dependencies
pip install -r requirements.txt

# Quá trình này mất 2-5 phút
```

### Bước 5.3: Tạo file hosts.ini

**Tạo file hosts.ini với cấu hình của bạn:**

```bash
# Tạo thư mục inventory của bạn
mkdir -p ~/kubespray/inventory/mycluster

# Tạo file hosts.ini
cat <<'EOF' > ~/kubespray/inventory/mycluster/hosts.ini
[all]
k8s-master-1 ansible_host=10.105.196.111 ip=10.105.196.111
k8s-master-2 ansible_host=10.105.196.112 ip=10.105.196.112
k8s-master-3 ansible_host=10.105.196.113 ip=10.105.196.113

[kube-master]
k8s-master-1

[kube-node]
k8s-master-1
k8s-master-2
k8s-master-3

[etcd]
k8s-master-1

[k8s-cluster:children]
kube-node
kube-master

[calico-rr]

[vault]
k8s-master-1
EOF
```

**Giải thích cấu hình:**
- **[all]**: Tất cả nodes trong cluster
- **[kube-master]**: Node chạy control plane (chỉ master-1)
- **[kube-node]**: Nodes chạy workload (cả 3 nodes)
- **[etcd]**: Node chạy etcd (chỉ master-1 - single etcd)
- **[k8s-cluster:children]**: Tất cả nodes thuộc k8s cluster

### Bước 5.4: Copy các file cấu hình mẫu

```bash
# Copy group_vars từ sample
cp -rfp ~/kubespray/inventory/sample/group_vars ~/kubespray/inventory/mycluster/
```

** CHECKPOINT PHẦN 5**:
- [ ] Kubespray đã clone (release-2.24)
- [ ] Dependencies đã cài đặt
- [ ] File hosts.ini đã tạo với cấu hình đúng

---

## PHẦN 6: KIỂM TRA VÀ CHẠY ANSIBLE PLAYBOOK

### Bước 6.1: Test Ansible connectivity

```bash
# Trong thư mục kubespray, venv active
cd ~/kubespray
source venv/bin/activate

# Test ping tất cả hosts
ansible all -i inventory/mycluster/hosts.ini -m ping

# Kết quả mong đợi:
# k8s-master-1 | SUCCESS => {"changed": false, "ping": "pong"}
# k8s-master-2 | SUCCESS => {"changed": false, "ping": "pong"}
# k8s-master-3 | SUCCESS => {"changed": false, "ping": "pong"}
```

**Nếu gặp lỗi "Failed to connect":**
```bash
# Kiểm tra SSH key
ssh-add ~/.ssh/id_ed25519

# Test SSH thủ công
ssh root@10.105.196.111 "echo OK"
ssh root@10.105.196.112 "echo OK"
ssh root@10.105.196.113 "echo OK"
```

### Bước 6.2: Chạy Ansible playbook để cài Kubernetes

**LƯU Ý:** Quá trình này mất 20-40 phút.

```bash
# Đảm bảo đang trong thư mục kubespray và venv active
cd ~/kubespray
source venv/bin/activate

# Chạy playbook cluster.yml
ansible-playbook -i inventory/mycluster/hosts.ini cluster.yml -b -v

# Options:
# -i: chỉ định inventory file (hosts.ini)
# -b: become (dùng sudo privileges)
# -v: verbose output
```

**Trong quá trình chạy, bạn sẽ thấy:**
```
PLAY [Check Ansible version]
TASK [Gathering Facts]
PLAY [Gather facts]
PLAY [Install container runtime]
PLAY [Install etcd]
PLAY [Install Kubernetes components]
PLAY [Configure control plane]
PLAY [Install network plugin]
...
```

### Bước 6.3: Chờ deployment hoàn tất

**Khi playbook chạy xong, bạn sẽ thấy:**
```
PLAY RECAP ***
k8s-master-1   : ok=XXX  changed=YYY  unreachable=0    failed=0
k8s-master-2   : ok=XXX  changed=YYY  unreachable=0    failed=0
k8s-master-3   : ok=XXX  changed=YYY  unreachable=0    failed=0
```

** SUCCESS** khi: `unreachable=0` và `failed=0` cho TẤT CẢ nodes!

** CHECKPOINT PHẦN 6**:
- [ ] Ansible ping test thành công
- [ ] Ansible playbook đã chạy xong không có lỗi
- [ ] PLAY RECAP hiển thị failed=0 cho tất cả nodes

---

## PHẦN 7: CẤU HÌNH KUBECTL VÀ KIỂM TRA CLUSTER

### Bước 7.1: Copy kubectl config

**Trên Master Node 1:**

```bash
# Tạo thư mục .kube
mkdir -p ~/.kube

# Copy config từ cluster
cp -i /etc/kubernetes/admin.conf ~/.kube/config

# Set permissions
chmod 600 ~/.kube/config

# Kiểm tra config
cat ~/.kube/config | head -10
```

### Bước 7.2: Cài đặt kubectl (nếu chưa có)

```bash
# Kiểm tra kubectl
kubectl version --client

# Nếu chưa có, cài đặt:
curl -LO "https://dl.k8s.io/release/v1.28.5/bin/linux/amd64/kubectl"
chmod +x kubectl
mv kubectl /usr/local/bin/

# Verify
kubectl version --client
```

### Bước 7.3: Kiểm tra cluster

```bash
# Xem cluster info
kubectl cluster-info

# Kết quả mong đợi:
# Kubernetes control plane is running at https://10.105.196.111:6443

# Xem nodes
kubectl get nodes

# Kết quả mong đợi:
# NAME           STATUS   ROLES           AGE   VERSION
# k8s-master-1   Ready    control-plane   5m    v1.28.x

# Xem tất cả pods
kubectl get pods --all-namespaces

# Tất cả pods phải ở trạng thái Running
```

### Bước 7.4: Kiểm tra từng component

```bash
# Xem nodes chi tiết
kubectl get nodes -o wide

# Xem pods trong kube-system
kubectl get pods -n kube-system

# Các pods quan trọng:
# - kube-apiserver-k8s-master-1
# - kube-controller-manager-k8s-master-1
# - kube-scheduler-k8s-master-1
# - etcd-k8s-master-1
# - calico-node-xxx
# - coredns-xxx

# Xem component status
kubectl get componentstatuses

# Xem events
kubectl get events --all-namespaces
```

### Bước 7.5: Test deploy application

```bash
# Tạo namespace test
kubectl create namespace test-app

# Deploy nginx
kubectl create deployment nginx --image=nginx:latest --replicas=2 -n test-app

# Xem deployment
kubectl get deployments -n test-app

# Xem pods
kubectl get pods -n test-app -o wide

# Expose service
kubectl expose deployment nginx --port=80 --type=NodePort -n test-app

# Xem service và NodePort
kubectl get svc -n test-app

# Test truy cập (thay <NodePort> bằng port thực tế)
curl http://10.105.196.111:<NodePort>

# Xóa test app
kubectl delete namespace test-app
```

** CHECKPOINT PHẦN 7**:
- [ ] kubectl config đã cấu hình
- [ ] kubectl get nodes hiển thị node với STATUS=Ready
- [ ] Tất cả pods trong kube-system ở trạng thái Running
- [ ] Test deployment nginx thành công

---

## PHẦN 8: XỬ LÝ SỰ CỐ THƯỜNG GẶP

### Vấn đề 1: Ansible ping test fail

**Lỗi:** "Failed to connect to the host via ssh"

**Giải pháp:**
```bash
# Kiểm tra SSH key
ssh-add ~/.ssh/id_ed25519

# Test SSH thủ công
ssh root@10.105.196.111 "hostname"
ssh root@10.105.196.112 "hostname"
ssh root@10.105.196.113 "hostname"

# Kiểm tra SSH service đang chạy trên các nodes
systemctl status sshd

# Kiểm tra /etc/hosts có đúng không
cat /etc/hosts
```

### Vấn đề 2: Node hiển thị NotReady

**Nguyên nhân:** Network plugin chưa ready

**Giải pháp:**
```bash
# Kiểm tra kubelet
systemctl status kubelet

# Restart kubelet
systemctl restart kubelet

# Xem logs kubelet
journalctl -u kubelet -f

# Kiểm tra calico pods
kubectl get pods -n kube-system | grep calico

# Restart calico nếu cần
kubectl delete pod -n kube-system -l k8s-app=calico-node
```

### Vấn đề 3: Ansible playbook timeout

**Lỗi:** "Timeout waiting for node to be ready"

**Giải pháp:**
```bash
# Tăng timeout trong group_vars
vi ~/kubespray/inventory/mycluster/group_vars/k8s_cluster/k8s-cluster.yml

# Thêm:
kubelet_status_timeout: 300

# Chạy lại playbook
ansible-playbook -i inventory/mycluster/hosts.ini cluster.yml -b -v
```

### Vấn đề 4: Pods stuck ở Pending

**Nguyên nhân:** Taint trên master node

**Giải pháp:**
```bash
# Xem taints
kubectl describe node k8s-master-1 | grep Taints

# Remove taint để cho phép schedule pods lên master
kubectl taint nodes k8s-master-1 node-role.kubernetes.io/control-plane:NoSchedule-
```

### Vấn đề 5: DNS không hoạt động

**Giải pháp:**
```bash
# Kiểm tra coredns pods
kubectl get pods -n kube-system -l k8s-app=kube-dns

# Restart coredns
kubectl rollout restart deployment coredns -n kube-system

# Test DNS
kubectl run busybox --image=busybox:1.28 --rm -it --restart=Never -- nslookup kubernetes.default
```

### Reset Cluster (khi cần cài lại)

**LƯU Ý: Lệnh này sẽ XÓA toàn bộ cluster!**

```bash
cd ~/kubespray
source venv/bin/activate

# Chạy reset playbook
ansible-playbook -i inventory/mycluster/hosts.ini reset.yml -b -v

# Sau khi reset xong, có thể cài lại
ansible-playbook -i inventory/mycluster/hosts.ini cluster.yml -b -v
```

---

## PHỤ LỤC: LỆNH THƯỜNG DÙNG

### Quản lý Nodes

```bash
# Xem nodes
kubectl get nodes
kubectl get nodes -o wide

# Describe node
kubectl describe node k8s-master-1

# Xem resource usage
kubectl top nodes
```

### Quản lý Pods

```bash
# Xem pods
kubectl get pods --all-namespaces
kubectl get pods -n kube-system

# Describe pod
kubectl describe pod <pod-name> -n <namespace>

# Xem logs
kubectl logs <pod-name> -n <namespace>
kubectl logs -f <pod-name> -n <namespace>  # Follow logs

# Exec vào pod
kubectl exec -it <pod-name> -n <namespace> -- /bin/bash
```

### Quản lý Services

```bash
# Xem services
kubectl get svc --all-namespaces

# Describe service
kubectl describe svc <service-name> -n <namespace>

# Port forward
kubectl port-forward svc/<service-name> 8080:80 -n <namespace>
```

### Cluster Info

```bash
# Cluster info
kubectl cluster-info
kubectl cluster-info dump

# Xem events
kubectl get events --all-namespaces --sort-by='.lastTimestamp'

# API resources
kubectl api-resources
```

---

## KẾT LUẬN

Chúc mừng! Bạn đã cài đặt thành công Kubernetes cluster sử dụng Kubespray.

**Cluster của bạn bây giờ có:**
-  3 nodes (10.105.196.111, 112, 113)
-  1 master node (k8s-master-1)
-  3 worker nodes (master-1, master-2, master-3)
-  etcd running trên master-1
-  Calico network plugin
-  CoreDNS

**Các bước tiếp theo:**
1. Deploy ứng dụng của bạn
2. Cài đặt monitoring (Prometheus + Grafana)
3. Cài đặt logging (EFK stack)
4. Setup Ingress controller
5. Cấu hình backup cho etcd

**Tài liệu tham khảo:**
- Kubespray: https://kubespray.io/
- Kubernetes: https://kubernetes.io/docs/
- Calico: https://docs.projectcalico.org/

---