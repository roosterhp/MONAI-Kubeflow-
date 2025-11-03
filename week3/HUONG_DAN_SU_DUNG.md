# Hướng Dẫn Sử Dụng - Week 3: Tích Hợp EfficientNetV2-S

> **Mục tiêu**: Tích hợp model EfficientNetV2-S từ thư viện timm vào MONAI để phân loại ảnh y khoa 2D

---

## 📁 Các File Đã Tạo

### 1. **Model Wrapper** - `models/efficientnet_wrapper.py`

**Làm gì**: Wrap model EfficientNetV2-S từ timm để dùng với MONAI

**Cách dùng**:
```python
from models.efficientnet_wrapper import EfficientNetV2Wrapper

# Tạo model với 5 classes
model = EfficientNetV2Wrapper(
    num_classes=5,           # Số lớp cần phân loại
    pretrained=True          # Dùng pretrained weights từ ImageNet
)

# Test forward pass
import torch
x = torch.randn(2, 3, 224, 224)  # [batch, channels, H, W]
output = model(x)                 # [batch, num_classes]
print(output.shape)               # torch.Size([2, 5])

# Freeze backbone (stage 1 training)
model.freeze_backbone()

# Unfreeze (stage 2 training)
model.unfreeze_all()

# Lấy parameter groups cho differential learning rate
param_groups = model.get_parameter_groups(
    backbone_lr=1e-4,  # LR thấp cho backbone
    head_lr=1e-3       # LR cao cho classifier head
)
```

**Tính năng**:
- ✅ Load pretrained weights từ ImageNet
- ✅ Freeze/unfreeze backbone
- ✅ Differential learning rates
- ✅ Tương thích với MONAI

---

### 2. **Preprocessing Component** - `components/preprocess/`

**Làm gì**: Xử lý ảnh y khoa thô thành dữ liệu đầu vào cho model

**Cấu trúc dữ liệu đầu vào** (cần chuẩn bị):
```
raw_data/
├── class_0_normal/
│   ├── img001.png
│   ├── img002.png
│   └── ...
├── class_1_pneumonia/
│   ├── img001.png
│   └── ...
├── class_2_covid/
└── ...
```

**Chạy preprocessing**:
```bash
python components/preprocess/preprocess.py \
  --raw-data-path /path/to/raw_data \
  --output-path /path/to/processed_data \
  --image-size 224 224 \
  --train-split 0.7 \
  --val-split 0.2 \
  --test-split 0.1
```

**Kết quả**:
```
processed_data/
├── train/           # 70% data với augmentation
├── val/             # 20% data không augmentation
├── test/            # 10% data không augmentation
├── metadata.json    # Thống kê dataset
└── data_splits.json # Thông tin split
```

**Transforms được áp dụng**:
1. Load ảnh (hỗ trợ PNG, JPG, DICOM)
2. Resize về 224x224
3. Normalize theo ImageNet stats
4. Augmentation (train only):
   - Random rotation
   - Random flip
   - Random zoom

---

### 3. **Docker Images**

**Build preprocessing image**:
```bash
cd components/preprocess
docker build -t efficientnet-preprocess:v1 .

# Test locally
docker run --rm \
  -v /path/to/data:/data \
  efficientnet-preprocess:v1 \
  --raw-data-path /data/raw \
  --output-path /data/processed
```

---

## 🚀 Workflow Từ Đầu Đến Cuối

### **Bước 1: Chuẩn bị môi trường**

```bash
# Clone project
cd week3

# Tạo virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install torch torchvision monai[all] timm
```

### **Bước 2: Test model wrapper**

```bash
# Test model
python models/efficientnet_wrapper.py

# Kết quả mong đợi:
# ✅ Forward pass: input torch.Size([2, 3, 224, 224]) → output torch.Size([2, 5])
# ✅ Freeze/unfreeze: X → Y params
# ✅ All tests passed!
```

### **Bước 3: Chuẩn bị data**

```bash
# Tổ chức data theo cấu trúc:
mkdir -p data/raw/{class_0,class_1,class_2,class_3,class_4}

# Copy ảnh vào từng folder class
# class_0: Normal
# class_1: Pneumonia
# class_2: COVID-19
# ...

# Chạy preprocessing
python components/preprocess/preprocess.py \
  --raw-data-path data/raw \
  --output-path data/processed
```

### **Bước 4: Training** (sẽ implement tiếp)

```bash
# Stage 1: Train classifier head only (5 epochs)
python components/train/train.py \
  --data-path data/processed \
  --stage 1 \
  --epochs 5

# Stage 2: Full fine-tune (20 epochs)
python components/train/train.py \
  --data-path data/processed \
  --stage 2 \
  --epochs 20

# Stage 3: Refinement (5 epochs)
python components/train/train.py \
  --data-path data/processed \
  --stage 3 \
  --epochs 5
```

### **Bước 5: Evaluation** (sẽ implement tiếp)

```bash
# Đánh giá model trên test set
python components/evaluate/evaluate.py \
  --model-path models/best_model.pth \
  --test-data-path data/processed/test

# Kết quả:
# AUC: 0.942
# F1: 0.889
# Accuracy: 0.901
# ECE: 0.082
```

### **Bước 6: Deployment** (sẽ implement tiếp)

```bash
# Export sang ONNX
python models/export_onnx.py \
  --model-path models/best_model.pth \
  --output-path models/model.onnx

# Deploy lên KServe
kubectl apply -f deployment/inferenceservice.yaml
```

---

## 📊 Hiểu Về Model Architecture

### **EfficientNetV2-S là gì?**

- **Kiến trúc**: CNN hiện đại, tối ưu cho tốc độ và độ chính xác
- **Kích thước**: 24M parameters
- **Input**: Ảnh 224x224, 3 channels (RGB)
- **Output**: Logits cho số classes (VD: 5 classes)
- **Pretrained**: Đã train trên ImageNet với 1.28M ảnh

### **Tại sao dùng EfficientNetV2-S?**

| Tiêu chí | EfficientNetV2-S | MONAI Models | ViT (HuggingFace) |
|----------|------------------|--------------|-------------------|
| **Phù hợp 2D** | ✅ Rất tốt | ❌ Chủ yếu 3D | ✅ Tốt |
| **Tốc độ** | ✅ Nhanh (45ms) | N/A | ❌ Chậm (150ms) |
| **Kích thước** | ✅ Nhỏ (24M) | ⚠️ Lớn (50-200M) | ❌ Rất lớn (80-300M) |
| **Transfer learning** | ✅ Xuất sắc | ✅ Tốt | ⚠️ Cần nhiều data |

**Kết luận**: EfficientNetV2-S là lựa chọn tốt nhất cho:
- Ảnh X-quang, siêu âm (2D)
- Cần tốc độ inference nhanh (<100ms)
- Dataset nhỏ/trung bình (1000-10000 ảnh)

---

## 🔧 Cấu Hình Training

### **Two-Stage Fine-tuning**

**Tại sao cần 2 stage?**
- Stage 1: Adapt classifier nhanh với backbone frozen
- Stage 2: Fine-tune toàn bộ model để học features chuyên biệt

**Stage 1** (5 epochs, ~30 phút):
```python
model.freeze_backbone()  # Đóng băng backbone
optimizer = AdamW(model.parameters(), lr=1e-3)  # LR cao

# Train classifier head
# Val accuracy: ~75% sau 5 epochs
```

**Stage 2** (20 epochs, ~2-3 giờ):
```python
model.unfreeze_all()  # Mở khóa tất cả

# Differential learning rates
optimizer = AdamW([
    {'params': backbone_params, 'lr': 1e-4},  # LR thấp
    {'params': head_params, 'lr': 1e-3}       # LR cao
], weight_decay=0.01)

# Train toàn bộ
# Val accuracy: ~90% sau 20 epochs
```

**Stage 3** (5 epochs, ~30 phút):
```python
optimizer = AdamW(model.parameters(), lr=1e-5)  # LR rất thấp

# Refinement
# Val accuracy: ~92% sau 5 epochs
```

**Total training time**: ~4 giờ (với GPU V100)

---

## 📈 Metrics Đánh Giá

### **AUC-ROC** (Area Under ROC Curve)
- **Ý nghĩa**: Khả năng phân biệt giữa các class
- **Mục tiêu**: > 0.90
- **Tốt**: > 0.95

### **F1 Score**
- **Ý nghĩa**: Cân bằng giữa Precision và Recall
- **Mục tiêu**: > 0.85
- **Tốt**: > 0.90

### **Accuracy**
- **Ý nghĩa**: Tỷ lệ dự đoán đúng
- **Mục tiêu**: > 0.85
- **Tốt**: > 0.90

### **ECE** (Expected Calibration Error) ⭐ QUAN TRỌNG
- **Ý nghĩa**: Model có tự tin đúng mức không?
- **VD**: Model dự đoán 85% → Thực tế đúng ~85%
- **Mục tiêu**: < 0.10
- **Tốt**: < 0.05
- **Tại sao quan trọng**: Y tế cần prediction đáng tin cậy!

---

## 🐛 Troubleshooting

### **Lỗi: CUDA out of memory**
```bash
# Giải pháp 1: Giảm batch size
--batch-size 16  # thay vì 32

# Giải pháp 2: Dùng mixed precision
--amp true

# Giải pháp 3: Train trên CPU (chậm hơn)
--device cpu
```

### **Lỗi: timm model not found**
```bash
# Download thủ công pretrained weights
mkdir -p ~/.cache/torch/hub/checkpoints
wget https://github.com/rwightman/pytorch-image-models/releases/download/v0.1-effv2-weights/efficientnetv2_rw_s_ra2-36bf1e4d.pth \
  -O ~/.cache/torch/hub/checkpoints/efficientnetv2_rw_s_ra2-36bf1e4d.pth
```

### **Lỗi: Data loading chậm**
```bash
# Tăng cache rate
--cache-rate 1.0  # Cache toàn bộ vào RAM

# Giảm num_workers nếu RAM thiếu
--num-workers 2
```

---

## 📝 Checklist Triển Khai

### **Ngày 1: Setup & Integration**
- [ ] Clone project và setup environment
- [ ] Test `efficientnet_wrapper.py`
- [ ] Chuẩn bị data theo cấu trúc yêu cầu
- [ ] Chạy preprocessing thành công
- [ ] Build Docker image preprocessing

### **Ngày 2: Training**
- [ ] Implement training script
- [ ] Chạy Stage 1 training (5 epochs)
- [ ] Chạy Stage 2 training (20 epochs)
- [ ] Val accuracy > 0.85
- [ ] Model checkpoint saved

### **Ngày 3: Evaluation**
- [ ] Implement evaluation script
- [ ] AUC > 0.90 ✓
- [ ] F1 > 0.85 ✓
- [ ] ECE < 0.10 ✓
- [ ] Export sang ONNX thành công

### **Ngày 4: Pipeline**
- [ ] Tạo Kubeflow pipeline YAML
- [ ] Submit pipeline thành công
- [ ] Tất cả components chạy OK
- [ ] Deploy InferenceService

### **Ngày 5: Production**
- [ ] Canary deployment (10% → 50% → 100%)
- [ ] Latency < 100ms
- [ ] Test rollback < 2 phút
- [ ] Setup monitoring

---

## 💡 Tips Quan Trọng

### **Data Quality**
- ✅ Ít nhất 100 ảnh/class
- ✅ Ảnh rõ nét, không bị crop sai
- ✅ Class balance (tránh 1 class quá nhiều)
- ✅ Annotate chính xác

### **Training**
- ✅ Luôn bắt đầu với pretrained weights
- ✅ Dùng mixed precision để tiết kiệm memory
- ✅ Monitor train/val gap (tránh overfit)
- ✅ Save best model (theo val accuracy)

### **Evaluation**
- ✅ Test set PHẢI tách biệt
- ✅ Không được tuning trên test set
- ✅ Report đầy đủ metrics (AUC, F1, ECE)
- ✅ Phân tích confusion matrix

### **Deployment**
- ✅ Validate ONNX trước khi deploy
- ✅ Test với sample data trước
- ✅ Setup monitoring ngay từ đầu
- ✅ Có kế hoạch rollback

---

## 🎓 Học Thêm

### **PyTorch & MONAI**
- [MONAI Documentation](https://docs.monai.io/)
- [PyTorch Tutorials](https://pytorch.org/tutorials/)

### **Model Architecture**
- [EfficientNetV2 Paper](https://arxiv.org/abs/2104.00298)
- [timm Documentation](https://timm.fast.ai/)

### **Deployment**
- [KServe Documentation](https://kserve.github.io/website/)
- [Triton Inference Server](https://github.com/triton-inference-server)

---

## ❓ Câu Hỏi Thường Gặp

**Q: Cần GPU không?**
A: Khuyến khích có GPU (V100/A100), nhưng có thể train trên CPU (chậm hơn 10-20 lần).

**Q: Cần bao nhiêu data?**
A: Tối thiểu 1000 ảnh (100 ảnh/class), lý tưởng 5000+ ảnh.

**Q: Training mất bao lâu?**
A: ~4 giờ với GPU V100, ~2 ngày với CPU.

**Q: Accuracy thấp hơn mong đợi?**
A: Kiểm tra: data quality, class balance, hyperparameters, augmentation.

**Q: Làm sao biết model overfit?**
A: Train accuracy >> Val accuracy (gap > 10%).

---

**Tiếp theo**: Tôi sẽ tạo các file training, evaluation, và deployment components!

**File này sẽ được cập nhật khi có thêm components mới.**

**Ngày tạo**: 2025-10-31
**Phiên bản**: 1.0.0
