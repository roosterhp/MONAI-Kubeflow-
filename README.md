# Hướng dẫn MONAI + Kubeflow trên Windows - Từ A đến Z

## 🎯 Mục tiêu
Sau khi hoàn thành, bạn sẽ có:
- MONAI chạy được để train model y tế
- Kubeflow Pipeline để quản lý workflow
- Demo hoàn chỉnh phân loại ảnh y tế

---

## PHẦN 1: CHUẨN BỊ MÔI TRƯỜNG 

### Bước 1.1: Cài đặt WSL2 (Windows Subsystem for Linux)

**Tại sao cần WSL2?** Kubernetes chạy tốt nhất trên Linux, WSL2 cho phép bạn chạy Linux trong Windows.

```powershell
# Mở PowerShell với quyền Administrator (chuột phải → Run as Administrator)

# Enable WSL
wsl --install

# Sau khi cài xong, KHỞI ĐỘNG LẠI MÁY
```

**Sau khi restart:**
```powershell
# Kiểm tra WSL đã cài chưa
wsl --list --verbose

# Set WSL2 làm default
wsl --set-default-version 2

# Cài Ubuntu (nếu chưa có)
wsl --install -d Ubuntu-22.04
```

**Lần đầu chạy Ubuntu**, nó sẽ hỏi:
- Username: (tự đặt, ví dụ: `monaiuser`)
- Password: (tự đặt, nhớ kỹ password này)

### Bước 1.2: Cài đặt Docker Desktop

1. **Download Docker Desktop for Windows**
   - Vào: https://www.docker.com/products/docker-desktop
   - Tải bản Windows
   - Dung lượng: ~500MB

2. **Cài đặt Docker Desktop**
   - Chạy file `.exe` vừa tải
   - ✅ Check: "Use WSL 2 instead of Hyper-V"
   - Click "OK" và đợi cài đặt (5-10 phút)
   - **KHỞI ĐỘNG LẠI MÁY** sau khi cài xong

3. **Cấu hình Docker Desktop**
   - Mở Docker Desktop
   - Vào Settings (icon bánh răng)
   - **General**: ✅ "Use the WSL 2 based engine"
   - **Resources → WSL Integration**: 
     - ✅ Enable integration with my default WSL distro
     - ✅ Ubuntu-22.04
   - Click "Apply & Restart"

4. **Kiểm tra Docker**
```powershell
# Mở PowerShell mới
docker --version
# Kết quả: Docker version 24.x.x

docker run hello-world
# Nếu thấy "Hello from Docker!" → OK!
```

### Bước 1.3: Cài đặt kubectl (Kubernetes CLI)

```powershell
# Mở PowerShell với quyền Administrator

# Download kubectl
curl.exe -LO "https://dl.k8s.io/release/v1.28.0/bin/windows/amd64/kubectl.exe"

# Di chuyển kubectl.exe vào thư mục trong PATH
# Tạo thư mục nếu chưa có
mkdir C:\kubectl
move kubectl.exe C:\kubectl\

# Thêm vào PATH
# Vào: System Properties → Environment Variables
# Hoặc dùng PowerShell:
[Environment]::SetEnvironmentVariable("Path", $env:Path + ";C:\kubectl", "User")

# Đóng và mở lại PowerShell mới
kubectl version --client
# Kết quả: Client Version: v1.28.0
```

### Bước 1.4: Cài đặt Minikube

```powershell
# Mở PowerShell với quyền Administrator

# Download Minikube
New-Item -Path 'c:\' -Name 'minikube' -ItemType Directory -Force
Invoke-WebRequest -OutFile 'c:\minikube\minikube.exe' -Uri 'https://github.com/kubernetes/minikube/releases/latest/download/minikube-windows-amd64.exe' -UseBasicParsing

# Thêm vào PATH
[Environment]::SetEnvironmentVariable("Path", $env:Path + ";C:\minikube", "User")

# Đóng và mở lại PowerShell
minikube version
```

### Bước 1.5: Cài đặt Python và pip

1. **Download Python**
   - Vào: https://www.python.org/downloads/
   - Tải Python 3.10 hoặc 3.11
   - **QUAN TRỌNG**: ✅ Check "Add Python to PATH" khi cài

2. **Kiểm tra Python**
```powershell
python --version
# Kết quả: Python 3.10.x hoặc 3.11.x

pip --version
# Kết quả: pip 23.x.x
```

---

## PHẦN 2: KHỞI ĐỘNG KUBERNETES

### Bước 2.1: Start Minikube

```powershell
# Mở PowerShell với quyền Administrator

# Start Minikube với Docker driver
minikube start --driver=docker --cpus=4 --memory=6144 --disk-size=20g

# Quá trình này mất 5-10 phút lần đầu
# Bạn sẽ thấy:
# ✓ minikube v1.x.x on Windows
# ✓ Using the docker driver
# ✓ Starting control plane node minikube in cluster minikube
# ✓ Done! kubectl is now configured to use "minikube" cluster
```

**Nếu gặp lỗi "Docker driver is not running":**
```powershell
# Đảm bảo Docker Desktop đang chạy
# Mở Docker Desktop, đợi logo whale xanh
# Thử lại: minikube start
```

### Bước 2.2: Kiểm tra Kubernetes

```powershell
# Check cluster status
minikube status
# Kết quả:
# minikube
# type: Control Plane
# host: Running
# kubelet: Running
# apiserver: Running

# Check nodes
kubectl get nodes
# NAME       STATUS   ROLES           AGE   VERSION
# minikube   Ready    control-plane   1m    v1.28.0

# Check pods trong tất cả namespaces
kubectl get pods --all-namespaces
```

---

## PHẦN 3: CÀI ĐẶT KUBEFLOW PIPELINES 

### Bước 3.1: Deploy Kubeflow Pipelines

```powershell
# Mở PowerShell thường (không cần Administrator)

# Set version
$PIPELINE_VERSION = "2.0.5"

# Deploy cluster-scoped resources
kubectl apply -k "github.com/kubeflow/pipelines/manifests/kustomize/cluster-scoped-resources?ref=$PIPELINE_VERSION"

# Đợi CRDs được tạo (30 giây)
Start-Sleep -Seconds 30

# Deploy Kubeflow Pipelines
kubectl apply -k "github.com/kubeflow/pipelines/manifests/kustomize/env/platform-agnostic?ref=$PIPELINE_VERSION"

# Quá trình này mất 5-10 phút
```

### Bước 3.2: Kiểm tra Kubeflow Pods

```powershell
# Xem các pods trong namespace kubeflow
kubectl get pods -n kubeflow

# Đợi đến khi TẤT CẢ pods ở trạng thái Running (có thể mất 5-10 phút)
# Dùng lệnh này để watch real-time:
kubectl get pods -n kubeflow --watch

# Khi thấy tất cả đều Running, nhấn Ctrl+C để thoát watch mode
```

**Các pods quan trọng cần Running:**
- `ml-pipeline-xxx`
- `ml-pipeline-ui-xxx`
- `mysql-xxx`
- `minio-xxx`

### Bước 3.3: Truy cập Kubeflow UI

```powershell
# Mở một PowerShell MỚI (giữ cửa sổ này luôn mở)
kubectl port-forward -n kubeflow svc/ml-pipeline-ui 8080:80

# Bạn sẽ thấy: Forwarding from 127.0.0.1:8080 -> 3000
# KHÔNG ĐÓNG cửa sổ này!
```

**Mở trình duyệt:**
- Vào: http://localhost:8080
- Bạn sẽ thấy Kubeflow Pipelines Dashboard

**✅ CHECKPOINT**: Nếu thấy giao diện Kubeflow → Thành công!

---

## PHẦN 4: CÀI ĐẶT MONAI 

### Bước 4.1: Tạo Virtual Environment

```powershell
# Mở PowerShell mới, di chuyển đến thư mục làm việc
cd C:\Users\YOUR_USERNAME\Documents
mkdir monai-kubeflow-demo
cd monai-kubeflow-demo

# Tạo virtual environment
python -m venv venv

# Activate virtual environment
.\venv\Scripts\Activate.ps1

# Nếu gặp lỗi execution policy:
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
# Sau đó thử lại activate

# Khi thành công, bạn sẽ thấy (venv) ở đầu dòng lệnh
```

### Bước 4.2: Cài đặt MONAI và dependencies

```powershell
# Trong PowerShell đã activate venv

# Upgrade pip trước
python -m pip install --upgrade pip

# Cài PyTorch (CPU version cho demo, nhẹ hơn)
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu

# Cài MONAI
pip install monai[all]

# Cài thêm dependencies cần thiết
pip install nibabel matplotlib scikit-image pillow

# Cài Kubeflow Pipeline SDK
pip install kfp==2.0.5

# Kiểm tra installation
python -c "import monai; print(f'MONAI version: {monai.__version__}')"
python -c "import torch; print(f'PyTorch version: {torch.__version__}')"
```

### Bước 4.3: Download Sample Data

```powershell
# Tạo script download data
New-Item -Path "download_data.py" -ItemType File

```powershell
# Chạy script download
python download_data.py

# Đợi 2-3 phút, data sẽ được tải về thư mục data/
```

---

## PHẦN 5: TẠO MONAI TRAINING SCRIPT (15 phút)

### Bước 5.1: Tạo Training Script đơn giản

Tạo file `train_simple.py`:

### Bước 5.2: Chạy Training Script

```powershell
# Đảm bảo bạn đang ở trong venv
# Nếu chưa activate:
.\venv\Scripts\Activate.ps1

# Chạy training
python train_simple.py

# Training sẽ mất khoảng 5-10 phút
# Bạn sẽ thấy:
# - Progress của mỗi epoch
# - Training loss và accuracy
# - Validation accuracy
# - Best model được lưu
```

**✅ CHECKPOINT**: Nếu training chạy xong, bạn sẽ có:
- File `best_model.pth` (model đã train)
- File `training_curves.png` (biểu đồ training)

---

## PHẦN 6: TẠO KUBEFLOW PIPELINE 

### Bước 6.1: Tạo Dockerfile cho MONAI
### Bước 6.2: Build Docker Image

**LƯU Ý**: Bạn cần tạo tài khoản Docker Hub trước

1. **Tạo tài khoản Docker Hub**
   - Vào: https://hub.docker.com/signup
   - Đăng ký tài khoản miễn phí
   - Nhớ username của bạn

2. **Login Docker Hub**
```powershell
# Login vào Docker Hub
docker login
# Nhập username và password
```

3. **Build và Push Image**
```powershell
# Thay YOUR_DOCKERHUB_USERNAME bằng username của bạn
$DOCKER_USERNAME = "YOUR_DOCKERHUB_USERNAME"

# Build image
docker build -t ${DOCKER_USERNAME}/monai-training:v1 .

# Quá trình build mất 5-10 phút

# Push image lên Docker Hub
docker push ${DOCKER_USERNAME}/monai-training:v1

# Quá trình push mất 3-5 phút
```

### Bước 6.3: Tạo Kubeflow Pipeline Script

Tạo file `monai_pipeline.py`:

**LƯU Ý**: Nhớ thay `YOUR_DOCKERHUB_USERNAME` bằng username Docker Hub của bạn!

### Bước 6.4: Compile Pipeline

```powershell
# Compile pipeline
python monai_pipeline.py

# Bạn sẽ thấy:
# ✓ Pipeline compiled successfully!
# Output: monai_pipeline.yaml
```

---

## PHẦN 7: CHẠY PIPELINE TRÊN KUBEFLOW 

### Bước 7.1: Upload Pipeline qua UI

1. **Mở Kubeflow UI**: http://localhost:8080

2. **Upload Pipeline**:
   - Click "Pipelines" ở sidebar trái
   - Click "+ Upload pipeline"
   - Pipeline name: `MONAI Medical Classification`
   - Click "Upload a file"
   - Chọn file `monai_pipeline.yaml`
   - Click "Create"

3. **Create Run**:
   - Click vào pipeline vừa tạo
   - Click "+ Create run"
   - Run name: `monai-demo-run-1`
   - Experiment: Click "Create new experiment"
     - Name: `medical-imaging`
     - Click "Next"
   - Parameters: Để mặc định
   - Click "Start"

### Bước 7.2: Monitor Pipeline Run

1. **Xem Progress**:
   - Pipeline sẽ hiển thị dạng graph
   - Mỗi component là một node
   - Màu xanh = Running
   - Màu xanh lá = Completed
   - Màu đỏ = Failed

2. **Xem Logs**:
   - Click vào từng node
   - Tab "Logs" để xem output
   - Tab "Input/Output" để xem parameters

**✅ CHECKPOINT**: Pipeline chạy thành công khi tất cả nodes màu xanh lá!

---

## PHẦN 8: DEMO ĐẦY ĐỦ - TEST INFERENCE 

### Bước 8.1: Tạo Inference Script

Tạo file `inference.py`:

### Bước 8.2: Chạy inference:
```powershell
python inference_demo.py
```

---

## PHẦN 9: TROUBLESHOOTING - GIẢI QUYẾT VẤN ĐỀ THƯỜNG GẶP

### 🚨 Vấn đề 1: "Input directory not found: /mnt/data/weekly_input"

**Nguyên nhân**: Pipeline không tìm thấy thư mục dữ liệu đầu vào do volume mounting chưa được cấu hình đúng.

**Giải pháp**:

#### Bước 9.1: Kiểm tra Minikube Volume Mounting
```powershell
# Kiểm tra Minikube đang chạy
minikube status

# Dừng Minikube nếu đang chạy
minikube stop

# Khởi động lại với volume mounting (thay YOUR_WINDOWS_PATH bằng đường dẫn thực tế)
$WINDOWS_PATH = "C:\Users\YOUR_USERNAME\Documents\monai-kubeflow-demo\hospital-mlops\covid-demo\data"
minikube start --driver=docker --mount-string="$WINDOWS_PATH:/mnt/data" --cpus=4 --memory=6144

# Xác nhận volume đã được mount
minikube ssh "ls -la /mnt/data"
```

#### Bước 9.2: Cấu hình PVC/PV cho Kubernetes
```powershell
# Apply persistent volume configuration
kubectl apply -f hospital-mlops/covid-demo/kubernetes/pv.yaml
kubectl apply -f hospital-mlops/covid-demo/kubernetes/pvc.yaml

# Kiểm tra PVC status
kubectl get pvc

# Nếu PVC đang ở trạng thái "Pending", kiểm tra PV
kubectl get pv
```

#### Bước 9.3: Chuẩn bị dữ liệu đầu vào
```powershell
# Tạo thư mục cấu trúc đúng
mkdir -p "hospital-mlops/covid-demo/data/input"
mkdir -p "hospital-mlops/covid-demo/data/output"

# Copy hoặc download các file CT scan mẫu
# Ví dụ: lung_001.nii.gz, lung_002.nii.gz, etc.
```

### 🚨 Vấn đề 2: Pipeline pods bị "CrashLoopBackOff"

**Nguyên nhân**: Pods không thể start do lỗi cấu hình hoặc thiếu resources.

**Giải pháp**:
```powershell
# Xem logs của pod
kubectl describe pod <pod-name> -n kubeflow
kubectl logs <pod-name> -n kubeflow

# Kiểm tra resource limits
kubectl describe nodes

# Tăng resources nếu cần
# Edit deployment để tăng memory/cpu limits
```

### 🚨 Vấn đề 3: Docker build quá chậm (15-20 phút)

**Nguyên nhân**: Build Docker từ đầu mỗi lần, không có layer caching.

**Giải pháp**:
```powershell
# Sử dụng Docker build đã tối ưu
cd hospital-mlops/covid-demo
.\scripts\build_optimized.sh

# Hoặc dùng NGC base image cho GPU
.\scripts\build_optimized.sh ngc

# Kiểm tra Dockerfile đã tối ưu
cat config/Dockerfile.optimized
```

### 🚨 Vấn đề 4: Kubeflow UI không thể truy cập (localhost:8080)

**Nguyên nhân**: Port forwarding không được thiết lập đúng.

**Giải pháp**:
```powershell
# Mở cửa sổ PowerShell mới và giữ mở
kubectl port-forward -n kubeflow svc/ml-pipeline-ui 8080:80

# Kiểm tra service đang chạy
kubectl get svc -n kubeflow

# Nếu service không tồn tại, deploy lại Kubeflow
kubectl apply -k "github.com/kubeflow/pipelines/manifests/kustomize/env/platform-agnostic?ref=2.0.5"
```

### 🚨 Vấn đề 5: Memory error khi xử lý CT scans

**Nguyên nhân**: CT scans quá lớn cho memory allocated.

**Giải pháp**:
```powershell
# Tăng Minikube memory
minikube stop
minikube start --driver=docker --memory=8192 --cpus=4

# Hoặc configure resource limits trong deployment
# Edit file YAML để tăng memory limits
```

### 🔧 Verification Steps - Kiểm tra sau khi fix

#### Bước 9.4: Test Data Access
```powershell
# Test truy cập data từ trong Minikube
minikube ssh "ls -la /mnt/data/weekly_input"
minikube ssh "find /mnt/data -name '*.nii.gz'"

# Test từ container
docker run --rm -v /host/path:/data covid-pipeline:v1 ls -la /data
```

#### Bước 9.5: Test Pipeline Component
```powershell
# Test individual components locally
cd hospital-mlops/covid-demo
python components/load_data.py lung_001
python components/lung_segment.py lung_001
python components/covid_detect_enhanced.py lung_001
```

#### Bước 9.6: Test Full Pipeline
```bash
# Run pipeline locally first
python run_pipeline_simple.py

# Nếu thành công, deploy lên Kubeflow
python pipeline.py
```

### 📋 Health Checklist

Trước khi chạy pipeline, đảm bảo:

- [ ] **Minikube đang chạy**: `minikube status`
- [ ] **Volume mounted đúng**: `minikube ssh "ls /mnt/data"`
- [ ] **Docker image built**: `docker images | grep covid-pipeline`
- [ ] **Kubeflow pods running**: `kubectl get pods -n kubeflow`
- [ ] **Input data có sẵn**: `ls hospital-mlops/covid-demo/data/input/`
- [ ] **PVC bound**: `kubectl get pvc` (status: Bound)
- [ ] **Port forwarding active**: `kubectl port-forward` running

### 🆘 Khi cần hỗ trợ thêm

1. **Check logs luôn**:
   ```powershell
   # Pipeline logs
   kubectl get pods -n kubeflow
   kubectl logs <pod-name> -n kubeflow

   # System logs
   minikube logs
   docker logs <container-name>
   ```

2. **Reset environment nếu cần**:
   ```powershell
   # Reset Minikube
   minikube delete
   minikube start --driver=docker --mount-string="YOUR_PATH:/mnt/data"

   # Reset Kubernetes
   kubectl delete all --all -n kubeflow
   ```

3. **Documentation tham khảo**:
   - `./docs/project-overview-pdr.md` - Tổng quan project
   - `./docs/troubleshooting-guide.md` - Hướng dẫn chi tiết
   - `./docs/deployment-guide.md` - Hướng dẫn deployment

**✅ Success Indicator**: Pipeline chạy thành công khi tất cả components trong Kubeflow UI hiển thị màu xanh lá!

---

## 📁 CẤU TRÚC FOLDER CỦA PROJECT

### 🏥 Hospital MLOps - Production Pipeline
```
hospital-mlops/
├── README.md                    # Tổng quan hệ thống AI cho bệnh viện
├── covid-demo/                  # Pipeline COVID-19 detection hoàn chỉnh
│   ├── README.md               # Chi tiết pipeline (lung seg → detection → viz)
│   ├── components/             # Core components (load, segment, detect, visualize)
│   ├── config/                 # Docker, requirements
│   ├── data/                   # Input/output CT scans
│   ├── kubernetes/             # PV, PVC configs
│   └── pipeline.py             # Kubeflow pipeline definition
├── demo/                       # Comparison demos (Rule-based vs MONAI)
├── deployment/                 # FastAPI inference service
│   └── README.md               # Deployment guide
└── pretrained-models/          # Downloaded MONAI models
```
**➡️ Xem chi tiết**: [hospital-mlops/README.md](hospital-mlops/README.md) và [hospital-mlops/covid-demo/README.md](hospital-mlops/covid-demo/README.md)

---

### 📚 Week-by-Week Learning Path

#### Week 3 - External Model Integration
```
week3/
├── README.md                   # EfficientNetV2-S integration với MONAI
├── components/                 # Kubeflow components (preprocess, train, evaluate)
├── models/                     # Model wrappers
├── pipeline/                   # Pipeline definitions
└── deployment/                 # KServe deployment manifests
```
**➡️ Xem chi tiết**: [week3/README.md](week3/README.md)

#### Week 4 - Model Replacement & Ensemble
```
week4/
├── README.md                   # So sánh 3 options tích hợp external models
├── option1/                    # Direct Replacement
│   └── README.md
├── option2/                    # Wrapper Adapter (RECOMMENDED)
│   └── README.md
└── option3/                    # Ensemble (Best Accuracy)
    └── README.md
```
**➡️ Xem chi tiết**: [week4/README.md](week4/README.md)

**Key Takeaway**: Chỉ cần ~10 dòng code để tăng accuracy từ 82% → 94%!

#### Week 5 - Clean Pipeline Implementation
```
week5/
├── README.md                   # Clean COVID-19 pipeline với ensemble
├── components/                 # Simplified components
├── config/                     # Requirements, Dockerfile
├── data/                       # Input/output structure
├── run_pipeline_simple.py     # Local testing runner
└── pipeline.py                # Kubeflow pipeline
```
**➡️ Xem chi tiết**: [week5/README.md](week5/README.md)

#### Week 6-9 - Production Deployment & Scaling
```
week6+7+8+9/
├── README.md                  # Tổng quan 4 tuần
├── week6/                     # Database & Storage
│   ├── README.md             # Database deployment guide
│   └── mysql-*.yaml          # MySQL configs
├── week7/                     # Horizontal Pod Autoscaling
│   ├── README.md             # HPA guide
│   ├── kubeflow-hpa-config.yaml
│   └── *-autoscaling.sh      # Test & monitor scripts
├── week8/                     # Deployment Strategies
│   ├── README.md             # Deployment guide
│   └── kubeflow-deployments-config.yaml
└── week9/                     # Production Testing
    ├── README.md             # Testing guide
    └── test-*.sh             # Database tests
```
**➡️ Xem chi tiết**: [week6+7+8+9/README.md](week6+7+8+9/README.md)

**Topics**: Week 6 (Database), Week 7 (HPA), Week 8 (Deploy), Week 9 (Testing)

#### Week 10 - CI/CD & GitOps
```
week10/
├── README.md              # Tổng quan CI/CD & GitOps
├── argocd/               # ArgoCD configurations
│   ├── argocd-projects.yaml
│   └── simple-test-app.yaml
└── scripts/              # Automation scripts
    ├── create-release.sh
    └── test-argocd-comprehensive.sh
```
**➡️ Xem chi tiết**: [week10/README.md](week10/README.md)

**Status**: ✅ **HOÀN THÀNH** (CI/CD & GitOps Automation)

**GitHub Actions CI/CD**:
- ✅ Pipeline CI Tests (lint, test, validation)
- ✅ Docker Build & Push (auto-push to GHCR)
- ✅ Security Scan (Trivy vulnerability scanner)
- ✅ Release Automation (tag-based releases)

**ArgoCD GitOps**:
- ✅ ArgoCD deployed (7/7 pods Running)
- ✅ Auto-sync enabled (sync from GitHub)
- ✅ Demo application deployed

**Docker Images**:
- `ghcr.io/roosterhp/monai-kubeflow/demo-app:latest`
- `ghcr.io/roosterhp/monai-kubeflow/demo-app:v1.0.1`

**Quick Start**:
```bash
# Check workflows
open https://github.com/roosterhp/MONAI-Kubeflow-/actions

# Create release
./week10/scripts/create-release.sh v1.0.2

# Check ArgoCD
kubectl get applications.argoproj.io -n argocd
```

---

### 🔧 Supporting Folders

```
components/                     # Shared components (if any)
└── README.md                  # Component reuse guide

docs/                          # Tài liệu tổng quan project
└── README.md                  # Documentation guide

kubeflow-install/              # Kubeflow installation manifests
└── README.md                  # Installation guide

kubeflow-pipelines/            # Compiled pipeline YAML files
└── README.md                  # How to upload to UI

models/                        # Downloaded pretrained models (500MB-2GB)
└── README.md                  # Model download guide

plans/                         # Implementation plans
├── README.md                  # Planning structure guide
└── YYMMDD-HHMM-feature-name/  # Each feature plan

venv/, monai_env/              # Python virtual environments (DO NOT COMMIT)
```

---

## 🗺️ LEARNING PATH - Lộ trình học

### 👶 Người mới bắt đầu
1. ✅ **Đọc README chính** (file này) → Hiểu tổng quan
2. ✅ **Cài đặt môi trường** → PHẦN 1-4 ở trên
3. ➡️ **Week 4** ([week4/README.md](week4/README.md)) → Hiểu cách tích hợp external models
4. ➡️ **Week 5** ([week5/README.md](week5/README.md)) → Chạy COVID-19 pipeline
5. ➡️ **Production** ([hospital-mlops/covid-demo/](hospital-mlops/covid-demo/)) → Pipeline hoàn chỉnh

### 👨‍💻 Developer muốn deploy
1. ➡️ **Production Pipeline** ([hospital-mlops/covid-demo/README.md](hospital-mlops/covid-demo/README.md))
2. ➡️ **Week 6-9** ([week6+7+8+9/README.md](week6+7+8+9/README.md)) → Database, scaling
3. ➡️ **Week 10** ([week10/README.md](week10/README.md)) → CI/CD, GitOps với ArgoCD
4. ➡️ **Docs** ([docs/](docs/)) → Architecture và deployment

### 🔬 Researcher muốn improve models
1. ➡️ **Week 4** ([week4/README.md](week4/README.md)) → Model replacement strategies
2. ➡️ **Comparison Demo** ([hospital-mlops/demo/](hospital-mlops/demo/)) → Rule-based vs MONAI
3. ➡️ **Pretrained Models** ([models/README.md](models/README.md)) → MONAI Model Zoo

---

## 🎯 Quick Navigation

| Tôi muốn... | Đọc file nào? |
|------------|---------------|
| Hiểu tổng quan project | README.md (file này) |
| Setup môi trường | README.md PHẦN 1-4 |
| Hiểu COVID pipeline | [hospital-mlops/covid-demo/README.md](hospital-mlops/covid-demo/README.md) |
| Tích hợp external models | [week4/README.md](week4/README.md) |
| Deploy production | [week6+7+8+9/README.md](week6+7+8+9/README.md) |
| Setup CI/CD & GitOps | [week10/README.md](week10/README.md) |
| Download pretrained models | [models/README.md](models/README.md) |
| Xem tài liệu kỹ thuật | [docs/README.md](docs/README.md) |
| Tạo implementation plan | [plans/README.md](plans/README.md) |

---

**Last Updated**: 2025-12-28
**Version**: 2.2 (Added Week 10 - CI/CD & GitOps)



