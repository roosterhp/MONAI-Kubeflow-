# Option 1: Thay Thế Trực Tiếp (Direct Replacement)

## Tổng Quan

Option 1 là phương pháp **đơn giản nhất**: thay thế trực tiếp model MONAI bằng **MedicalNet 3D-ResNet50** (model pretrained thật từ Tencent) **KHÔNG CẦN wrapper**.

>> **ĐÃ TRIỂN KHAI**: MedicalNet 3D-ResNet50 (46M tham số, pretrained trên 23 datasets y tế)

## Khi Nào Dùng

- Model external đã là `torch.nn.Module` (MedicalNet là PyTorch)
- Input/output shape tương thích sẵn (1 channel cho CT, 3D spatial dims)
- Model đã được train trên medical data tương tự (23 medical datasets)
- Muốn giải pháp đơn giản nhất với ít code nhất (chỉ 3 dòng thay đổi)

## Ưu Điểm

- **Đơn giản nhất** - chỉ 3 dòng code thay đổi
- Không cần viết wrapper hoặc adapter
- Giữ nguyên 100% MONAI infrastructure
- Nhanh - không có overhead
- Dễ maintain
- Real pretrained model (MedicalNet từ Tencent)

## Các File Trong Thư Mục

### File Demo

- **`demo_baseline.py`** - TRƯỚC: MONAI DenseNet121 (7M params, chưa train)
- **`demo_with_external.py`** - SAU: MedicalNet 3D-ResNet50 (46M params, pretrained)

### File Model (MỚI)

- **`models/medicalnet_resnet.py`** - Kiến trúc MedicalNet 3D-ResNet50
- **`models/__init__.py`** - Khởi tạo package

### File Test (MỚI)

- **`test_medicalnet.py`** - Unit tests cho MedicalNet model

### Tiện Ích (MỚI)

- **`download_pretrained_weights.py`** - Download MedicalNet pretrained weights

## Giải Thích Từng File

### 1. `demo_baseline.py` - Demo Baseline MONAI

**Mục đích**: Chạy baseline với model MONAI DenseNet121 (chưa train) để so sánh

**Các phase**:
- PHASE 1: Setup và load dữ liệu CT scans
- PHASE 2: MONAI Transforms (preprocessing ảnh y tế)
- PHASE 3: Model Setup - MONAI DenseNet121 (baseline chưa train)
- PHASE 4: Inference với MONAI SimpleInferer

**Kết quả**: Avg confidence ~0.566 (random, chưa train)

### 2. `demo_with_external.py` - Demo với MedicalNet

**Mục đích**: Thay thế model MONAI bằng MedicalNet 3D-ResNet50 (external model)

**Điểm khác biệt chính**:
- PHASE 3: Dùng external model MedicalNet thay vì MONAI built-in
- PHASE 4: Inference dùng CÙNG MONAI inferer nhưng model KHÁC

**Chỉ 3 dòng code thay đổi**:
```python
# TRƯỚC:
from monai.networks.nets import DenseNet121
model = DenseNet121(spatial_dims=3, in_channels=1, out_channels=2)

# SAU:
from models.medicalnet_resnet import resnet50_medicalnet
model = resnet50_medicalnet(num_classes=2, pretrained=True)
```

**Kết quả mong đợi**: 87-93% accuracy (với pretrained weights)

### 3. `models/medicalnet_resnet.py` - Kiến Trúc MedicalNet

**Mục đích**: Định nghĩa kiến trúc 3D-ResNet50 của MedicalNet

**Chức năng**:
- Class `Bottleneck3D`: 3D bottleneck block cho ResNet
- Class `ResNet3D`: Backbone 3D-ResNet với các layers [3, 4, 6, 3]
- Function `resnet50_medicalnet()`: Tạo model và load pretrained weights

**Tham số**: 46,159,170 (~46M params)

### 4. `test_medicalnet.py` - Unit Tests

**Mục đích**: Test model MedicalNet hoạt động đúng

**Các tests**:
- Test 1: Model load thành công
- Test 2: Forward pass hoạt động: (1, 1, 96, 96, 96) -> (1, 2)
- Test 3: Tương thích với MONAI SimpleInferer
- Test 4: Confidence scores hợp lệ

### 5. `download_pretrained_weights.py` - Download Weights

**Mục đích**: Script để download pretrained weights của MedicalNet

**Hướng dẫn**:
```bash
python download_pretrained_weights.py
# Hoặc download thủ công:
# 1. Vào: https://github.com/Tencent/MedicalNet
# 2. Download: resnet_50_23dataset.pth (~185MB)
# 3. Đặt tại: pretrained_weights/medicalnet/resnet_50_23dataset.pth
```

## Cách Chạy

### Quick Start

```bash
cd week4/option1

# Test MedicalNet model
python test_medicalnet.py

# Chạy MONAI baseline (để so sánh)
python demo_baseline.py

# Chạy với MedicalNet (Option 1)
python demo_with_external.py
```

### Với Pretrained Weights (Tuỳ Chọn)

```bash
# Download MedicalNet weights thủ công
# 1. Vào: https://github.com/Tencent/MedicalNet
# 2. Download: resnet_50_23dataset.pth (~185MB)
# 3. Đặt tại: pretrained_weights/medicalnet/resnet_50_23dataset.pth

# Chạy demo (sẽ tự động load pretrained weights)
python demo_with_external.py
# Kết quả mong đợi: 87-93% accuracy
```

## So Sánh TRƯỚC & SAU

### TRƯỚC: MONAI Model

```python
from monai.networks.nets import DenseNet121
from monai.inferers import SimpleInferer

# MONAI model
model = DenseNet121(
    spatial_dims=3,
    in_channels=1,
    out_channels=2
)

# Inference
inferer = SimpleInferer()
output = inferer(inputs=batch["image"], network=model)
```

### SAU: MedicalNet Model (Direct)

```python
# Load MedicalNet 3D-ResNet50 (REAL pretrained model)
from models.medicalnet_resnet import resnet50_medicalnet

model = resnet50_medicalnet(num_classes=2, pretrained=True)

# Cùng inferer, cùng transforms, cùng DataLoader
# CHỈ THAY ĐỔI: model!
inferer = SimpleInferer()  # Giống!
output = inferer(inputs=batch["image"], network=model)  # Giống!
```

**Chỉ 3 dòng code thay đổi!**

## Điều Kiện Cần

Model external phải thỏa mãn:

1. `isinstance(model, torch.nn.Module)` = True (MedicalNet là PyTorch)
2. Input shape: `(Batch, 1, Depth, Height, Width)` - 3D CT grayscale (tương thích)
3. Output shape: `(Batch, num_classes)` - Classification logits (tương thích)
4. Đã train trên medical CT data hoặc domain tương tự (23 medical datasets)

**MedicalNet đáp ứng TẤT CẢ yêu cầu!**

Nếu KHÔNG thỏa mãn -> Dùng **Option 2 (Wrapper)** hoặc **Option 3 (Ensemble)**

## So Sánh với Options Khác

| Tiêu Chí | Option 1 | Option 2 | Option 3 |
|----------|----------|----------|----------|
| **Độ đơn giản** | Rất đơn giản | Trung bình | Phức tạp |
| **Code changes** | **3 dòng** | 30 dòng | 50+ dòng |
| **Yêu cầu tương thích** | Cao | Thấp | Rất thấp |
| **Pretrained Medical** | 23 datasets | Không | Không |
| **Accuracy mong đợi** | **87-93%** | 80-85% | 90-95% |
| **Tốc độ inference** | Nhanh | Nhanh | Chậm (3x) |
| **Trạng thái** | **HOÀN THÀNH** | Pending | Pending |

## Khi Nào KHÔNG Dùng Option 1

- Model pretrained trên ImageNet (3 channels RGB) -> **Dùng Option 2**
- Model input/output shape khác -> **Dùng Option 2**
- Muốn accuracy tối đa -> **Dùng Option 3**
- Không có external model tương thích -> **Dùng Option 2** hoặc train lại

## Chi Tiết MedicalNet

**Nguồn**: Tencent/MedicalNet (GitHub)
- Paper: "Med3D: Transfer Learning for 3D Medical Image Analysis" (2019)
- GitHub: https://github.com/Tencent/MedicalNet
- ArXiv: https://arxiv.org/abs/1904.00625

**Pretrained trên 23 medical datasets:**
- CT segmentation (gan, phổi, tụy)
- MRI segmentation (não, tim)
- Phát hiện nodule phổi
- Và nhiều tác vụ y tế khác

## Kết Quả Triển Khai

| Metric | Giá Trị | Trạng Thái |
|--------|---------|-----------|
| **Model** | MedicalNet 3D-ResNet50 | Đã triển khai |
| **Tham số** | 46,159,170 (~46M) | Đã xác minh |
| **Code changes** | **3 dòng** | Đã xác minh |
| **Thời gian inference** | ~0.15-0.25s (CPU) | Đã test |
| **Tương thích MONAI** | 100% | Đã xác minh |
| **Accuracy mong đợi** | 87-93% (với pretrained) | Cần xác minh |

## Bước Tiếp Theo

1. Chạy demo để hiểu cách hoạt động
2. Nếu có external compatible model -> Dùng Option 1!
3. Nếu không -> Xem Option 2 (Wrapper) hoặc Option 3 (Ensemble)
4. Download pretrained weights để cải thiện accuracy
5. Fine-tune model trên dữ liệu của bạn

## Tham Khảo

- **Paper**: Chen et al. (2019) "Med3D: Transfer Learning for 3D Medical Image Analysis"
- **GitHub**: https://github.com/Tencent/MedicalNet
- **ArXiv**: https://arxiv.org/abs/1904.00625
