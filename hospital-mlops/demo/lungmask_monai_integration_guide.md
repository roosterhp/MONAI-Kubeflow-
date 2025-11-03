# Hướng Dẫn Tích Hợp LungMask vào MONAI Pipeline

## 📋 Tổng Quan

Document này hướng dẫn chi tiết cách tích hợp model segmentation bên ngoài (LungMask R231) vào pipeline MONAI để có một workflow nhất quán, dễ bảo trì và mở rộng.

---

## 🎯 Mục Tiêu

1. **Xây dựng pipeline inference** trong MONAI có thể gọi LungMask như một Transform
2. **Giữ nguyên kiến trúc và trọng số** gốc của LungMask (không training lại)
3. **Đảm bảo tương thích** với hệ thống Dataset, Transform và metadata của MONAI
4. **Tạo output mask** cùng hệ tọa độ, spacing, orientation với ảnh gốc
5. **Chuẩn bị nền tảng** để fine-tune sau này nếu cần

---

## 💡 Ý Nghĩa Của "Tích Hợp Vào MONAI"

### Trước Khi Tích Hợp (Hiện Tại)

```python
# Code hiện tại: Sử dụng LungMask độc lập
from lungmask import LMInferer
import SimpleITK as sitk

# 1. Load image bằng SimpleITK
ct_scan = sitk.ReadImage("patient.nii.gz")

# 2. Apply LungMask trực tiếp
inferer = LMInferer(modelname='R231')
mask = inferer.apply(ct_scan)  # Returns numpy array

# 3. Manual preprocessing/postprocessing
# - Không có transforms pipeline
# - Không có data augmentation
# - Không có batch processing
# - Khó mở rộng cho multi-model workflow
```

**Vấn đề:**
- ❌ Không tận dụng MONAI transforms (preprocessing, augmentation)
- ❌ Không tương thích với MONAI Dataset/DataLoader
- ❌ Khó kết hợp với các models MONAI khác
- ❌ Không có metadata tracking (spacing, orientation)
- ❌ Khó fine-tune hoặc ensemble models

### Sau Khi Tích Hợp (Mục Tiêu)

```python
# Pipeline MONAI với LungMask embedded
from monai.transforms import Compose, LoadImaged, EnsureChannelFirstd
from monai.data import Dataset, DataLoader

# 1. Define transforms pipeline
transforms = Compose([
    LoadImaged(keys=["image"]),
    EnsureChannelFirstd(keys=["image"]),
    Spacingd(keys=["image"], pixdim=(1.5, 1.5, 2.0)),
    ScaleIntensityRanged(keys=["image"], a_min=-1000, a_max=500),
    LungMaskTransformd(keys=["image"], model_name="R231"),  # ← Custom transform!
    # ... có thể thêm postprocessing, morphology, etc.
])

# 2. Dataset và DataLoader
dataset = Dataset(data=[{"image": "patient.nii.gz"}], transform=transforms)
dataloader = DataLoader(dataset, batch_size=4, num_workers=4)

# 3. Process batch
for batch in dataloader:
    images = batch["image"]
    masks = batch["pred"]  # LungMask predictions
    # → Batch processing, parallel loading, metadata preserved
```

**Lợi ích:**
- ✅ **Nhất quán:** Tất cả models dùng chung một pipeline
- ✅ **Mở rộng:** Dễ thêm preprocessing, postprocessing, augmentation
- ✅ **Hiệu năng:** Batch processing, parallel data loading
- ✅ **Metadata:** Tự động track spacing, orientation, affine transform
- ✅ **Fine-tuning:** Dễ dàng thay thế model hoặc ensemble
- ✅ **Production:** Chuẩn hóa workflow cho deployment

---

## 🏗️ Kiến Trúc Tích Hợp

```
┌─────────────────────────────────────────────────────────────────┐
│                    MONAI Pipeline Architecture                   │
└─────────────────────────────────────────────────────────────────┘

Input CT Scan (NIfTI)
        │
        ▼
┌──────────────────────┐
│   LoadImaged         │  ← Load image, preserve metadata
│   - spacing          │
│   - orientation      │
│   - affine matrix    │
└──────────────────────┘
        │
        ▼
┌──────────────────────┐
│ EnsureChannelFirstd │  ← Ensure shape: (1, H, W, D)
└──────────────────────┘
        │
        ▼
┌──────────────────────┐
│   Spacingd           │  ← Resample to target spacing
│   (1.5, 1.5, 2.0)    │     (optional, for standardization)
└──────────────────────┘
        │
        ▼
┌──────────────────────┐
│ ScaleIntensityRanged │  ← Window: HU [-1000, 500] → [0, 1]
└──────────────────────┘
        │
        ▼
┌──────────────────────────────────────┐
│   LungMaskTransformd (CUSTOM)        │  ← Wrapper for external model
│                                       │
│   Input:  CT image (MONAI MetaTensor) │
│   ┌───────────────────────────────┐  │
│   │ 1. Extract numpy array        │  │
│   │ 2. Convert to SimpleITK       │  │
│   │ 3. Call LungMask inference    │  │
│   │ 4. Convert back to MetaTensor │  │
│   │ 5. Preserve metadata          │  │
│   └───────────────────────────────┘  │
│   Output: Segmentation mask           │
└──────────────────────────────────────┘
        │
        ▼
┌──────────────────────┐
│ Postprocessing       │  ← Optional: morphology, filtering
│ - Remove small holes │
│ - Connected components│
└──────────────────────┘
        │
        ▼
┌──────────────────────┐
│  SaveImaged          │  ← Save with original metadata
└──────────────────────┘
        │
        ▼
   Output Mask (NIfTI)
```

---

## 📝 Các Bước Tích Hợp Chi Tiết

### Bước 1: Tạo Custom Transform Wrapper

**Mục đích:** Wrap LungMask model thành MONAI Transform để tương thích với pipeline.

**File:** `hospital-mlops/demo/lungmask_transform.py`

**Chức năng:**
1. Nhận input là MONAI MetaTensor (có metadata: spacing, affine, orientation)
2. Chuyển đổi sang SimpleITK Image (format mà LungMask cần)
3. Gọi LungMask inference
4. Chuyển output về MetaTensor và **copy metadata từ input**
5. Đảm bảo output mask có cùng spacing, orientation với ảnh gốc

**Key concepts:**
- `MapTransform`: Transform áp dụng trên dictionary keys
- `MetaTensor`: MONAI's tensor with metadata (spacing, affine, etc.)
- Lazy initialization: Chỉ load model khi cần (tiết kiệm RAM)

### Bước 2: Xây Dựng Pipeline Inference

**Mục đích:** Tạo một workflow chuẩn từ load image → inference → save output.

**Components:**

```python
# 1. Data Loading
LoadImaged(keys=["image"])
# → Tự động đọc NIfTI/DICOM, extract metadata

# 2. Preprocessing
EnsureChannelFirstd(keys=["image"])
# → Đảm bảo shape: (C, H, W, D) thay vì (H, W, D, C)

Spacingd(keys=["image"], pixdim=(1.5, 1.5, 2.0))
# → Resample về spacing chuẩn
# → LƯU Ý: LungMask đã được train với spacing khác nhau,
#   nên có thể skip bước này để giữ spacing gốc

ScaleIntensityRanged(
    keys=["image"],
    a_min=-1000,  # HU min (air)
    a_max=500,    # HU max (soft tissue)
    b_min=0.0,
    b_max=1.0,
    clip=True
)
# → Window CT scan để tăng contrast phổi
# → Clip outliers

# 3. Model Inference
LungMaskTransformd(keys=["image"], model_name="R231")
# → Apply LungMask, output thêm key "pred"

# 4. Postprocessing (Optional)
# - Remove small connected components
# - Fill holes
# - Smooth boundaries
```

### Bước 3: Tạo Dataset và DataLoader

**Mục đích:** Xử lý batch, parallel loading, caching.

```python
from monai.data import Dataset, DataLoader, CacheDataset

# Option A: Simple Dataset (no caching)
dataset = Dataset(data=data_dicts, transform=transforms)

# Option B: CacheDataset (cache preprocessed data)
dataset = CacheDataset(
    data=data_dicts,
    transform=transforms,
    cache_rate=1.0,  # Cache 100% data in RAM
    num_workers=4
)

# DataLoader with parallel workers
dataloader = DataLoader(
    dataset,
    batch_size=2,      # LungMask trên CPU: batch size nhỏ
    num_workers=4,     # Parallel loading
    collate_fn=pad_list_data_collate  # Xử lý variable sizes
)
```

### Bước 4: Kiểm Tra Alignment (Ảnh - Mask)

**Vấn đề:** Đảm bảo output mask có cùng spacing, orientation, origin với ảnh gốc.

**Cách kiểm tra:**

```python
import SimpleITK as sitk

# Load original image và predicted mask
original_img = sitk.ReadImage("patient.nii.gz")
pred_mask = sitk.ReadImage("patient_pred.nii.gz")

# Check 1: Spacing
print("Original spacing:", original_img.GetSpacing())
print("Predicted spacing:", pred_mask.GetSpacing())
assert original_img.GetSpacing() == pred_mask.GetSpacing()

# Check 2: Size
print("Original size:", original_img.GetSize())
print("Predicted size:", pred_mask.GetSize())
assert original_img.GetSize() == pred_mask.GetSize()

# Check 3: Origin
print("Original origin:", original_img.GetOrigin())
print("Predicted origin:", pred_mask.GetOrigin())
assert original_img.GetOrigin() == pred_mask.GetOrigin()

# Check 4: Direction (orientation matrix)
print("Original direction:", original_img.GetDirection())
print("Predicted direction:", pred_mask.GetDirection())
assert original_img.GetDirection() == pred_mask.GetDirection()

# Visual check: Overlay
import matplotlib.pyplot as plt

img_array = sitk.GetArrayFromImage(original_img)
mask_array = sitk.GetArrayFromImage(pred_mask)

slice_idx = img_array.shape[0] // 2
plt.imshow(img_array[slice_idx], cmap='gray')
plt.imshow(mask_array[slice_idx], cmap='Reds', alpha=0.5)
plt.title("Alignment Check: Image + Mask Overlay")
plt.savefig("alignment_check.png")
```

**Kết quả mong đợi:**
- ✅ All assertions pass
- ✅ Visual overlay: mask khớp hoàn toàn với lung boundaries

### Bước 5: Đo Hiệu Năng

**Metrics cần đo:**

1. **Accuracy:**
   - Dice Score (so với ground truth nếu có)
   - Hausdorff Distance
   - Surface Distance

2. **Speed:**
   - Inference time per scan
   - Throughput (scans/hour)
   - RAM usage

3. **Robustness:**
   - Performance trên different spacings
   - Performance trên different scan protocols
   - Performance trên pathological cases

**Code ví dụ:**

```python
import time
import psutil
from monai.metrics import DiceMetric

# 1. Dice Score
dice_metric = DiceMetric(include_background=False, reduction="mean")

for batch in dataloader:
    preds = batch["pred"]
    labels = batch["label"]  # Ground truth (if available)

    dice_metric(y_pred=preds, y=labels)

dice_score = dice_metric.aggregate().item()
print(f"Average Dice: {dice_score:.4f}")

# 2. Inference time
start_time = time.time()
for batch in dataloader:
    pred = model(batch["image"])
inference_time = time.time() - start_time
print(f"Inference time: {inference_time:.2f}s")

# 3. RAM usage
process = psutil.Process()
ram_usage = process.memory_info().rss / 1024**3  # GB
print(f"RAM usage: {ram_usage:.2f} GB")
```

---

## 🔬 Pipeline Ví Dụ Chi Tiết

### Use Case 1: Single Inference (Test)

```python
from monai.transforms import Compose, LoadImaged, EnsureChannelFirstd
from lungmask_transform import LungMaskTransformd

# Define pipeline
transforms = Compose([
    LoadImaged(keys=["image"]),
    EnsureChannelFirstd(keys=["image"]),
    LungMaskTransformd(keys=["image"], model_name="R231", output_key="pred"),
])

# Apply to single patient
data = {"image": "patient_001.nii.gz"}
result = transforms(data)

# Access results
image = result["image"]  # Original image (MetaTensor)
pred = result["pred"]    # Lung mask (MetaTensor)

print(f"Image shape: {image.shape}")
print(f"Prediction shape: {pred.shape}")
print(f"Spacing: {pred.meta['pixdim']}")
```

### Use Case 2: Batch Processing

```python
from monai.data import Dataset, DataLoader

# Prepare data list
data_list = [
    {"image": "patient_001.nii.gz"},
    {"image": "patient_002.nii.gz"},
    {"image": "patient_003.nii.gz"},
]

# Create dataset
dataset = Dataset(data=data_list, transform=transforms)

# DataLoader
dataloader = DataLoader(dataset, batch_size=2, num_workers=4)

# Process batch
for i, batch in enumerate(dataloader):
    images = batch["image"]
    preds = batch["pred"]

    print(f"Batch {i}: {images.shape} → {preds.shape}")

    # Save predictions
    for j in range(len(preds)):
        output_path = f"prediction_{i*2+j}.nii.gz"
        # Save with metadata preserved (see SaveImaged)
```

### Use Case 3: Với Validation (Ground Truth)

```python
from monai.metrics import DiceMetric

# Data với labels
data_list = [
    {"image": "patient_001.nii.gz", "label": "patient_001_gt.nii.gz"},
    {"image": "patient_002.nii.gz", "label": "patient_002_gt.nii.gz"},
]

# Transforms cho cả image và label
transforms = Compose([
    LoadImaged(keys=["image", "label"]),
    EnsureChannelFirstd(keys=["image", "label"]),
    LungMaskTransformd(keys=["image"], model_name="R231", output_key="pred"),
])

dataset = Dataset(data=data_list, transform=transforms)

# Compute Dice
dice_metric = DiceMetric(include_background=False)
for data in dataset:
    pred = data["pred"]
    label = data["label"]

    dice_metric(y_pred=pred[None], y=label[None])  # Add batch dim

avg_dice = dice_metric.aggregate().item()
print(f"Average Dice: {avg_dice:.4f}")
```

---

## ⚙️ Hướng Mở Rộng Để Fine-Tune

### Option 1: Fine-Tune LungMask Weights

**Khi nào cần:**
- Dice score < 0.90 trên hospital data
- Scan protocols khác với training data (VD: low-dose CT, contrast-enhanced)
- Cần segment lungs với pathology đặc biệt (fibrosis, emphysema)

**Workflow:**

```python
# 1. Export LungMask model architecture
# LungMask uses UNet-like architecture
# Có thể re-implement trong MONAI hoặc dùng ONNX export

# 2. Load pretrained weights
# lungmask model weights → PyTorch state_dict

# 3. Fine-tune với MONAI Trainer
from monai.networks.nets import UNet
from monai.losses import DiceLoss
from monai.inferers import sliding_window_inference

model = UNet(
    spatial_dims=3,
    in_channels=1,
    out_channels=3,  # Background, Left Lung, Right Lung
    channels=(16, 32, 64, 128, 256),
    strides=(2, 2, 2, 2),
)

# Load LungMask pretrained weights (if exportable)
# model.load_state_dict(lungmask_weights)

# Fine-tune
optimizer = torch.optim.Adam(model.parameters(), lr=1e-4)
loss_function = DiceLoss(to_onehot_y=True, softmax=True)

for epoch in range(num_epochs):
    for batch in train_loader:
        optimizer.zero_grad()
        outputs = model(batch["image"])
        loss = loss_function(outputs, batch["label"])
        loss.backward()
        optimizer.step()
```

### Option 2: Ensemble với MONAI Models

**Mục đích:** Kết hợp predictions từ nhiều models để tăng accuracy.

```python
from lungmask_transform import LungMaskTransformd
from monai_model_transform import MONAISegmentationTransformd

# Pipeline với ensemble
transforms = Compose([
    LoadImaged(keys=["image"]),
    EnsureChannelFirstd(keys=["image"]),

    # Model 1: LungMask
    LungMaskTransformd(keys=["image"], output_key="pred1"),

    # Model 2: MONAI Whole Body CT (if GPU available)
    MONAISegmentationTransformd(keys=["image"], output_key="pred2"),

    # Ensemble: Average predictions
    Lambdad(keys=["pred1", "pred2"], func=lambda x, y: (x + y) / 2, output_key="pred_ensemble"),
])
```

### Option 3: Post-Processing Refinement

**Thay vì fine-tune model, cải thiện output bằng post-processing:**

```python
from monai.transforms import (
    KeepLargestConnectedComponentd,
    FillHolesd,
    MedianSmoothd,
)

# Add postprocessing to pipeline
transforms = Compose([
    LoadImaged(keys=["image"]),
    EnsureChannelFirstd(keys=["image"]),
    LungMaskTransformd(keys=["image"], output_key="pred"),

    # Postprocessing
    KeepLargestConnectedComponentd(keys=["pred"]),  # Remove small islands
    FillHolesd(keys=["pred"]),                      # Fill internal holes
    MedianSmoothd(keys=["pred"], radius=1),         # Smooth boundaries
])
```

---

## 🎯 Tóm Tắt Workflow

```
┌─────────────────────────────────────────────────────────────┐
│                    COMPLETE WORKFLOW                         │
└─────────────────────────────────────────────────────────────┘

Phase 1: Development (CURRENT)
├── 1. Test LungMask standalone ✅
│   └── python demo/test_lungmask.py
├── 2. Integrate into MONAI pipeline
│   └── Create LungMaskTransformd wrapper
├── 3. Validate alignment and accuracy
│   └── Check spacing, orientation, Dice score
└── 4. Benchmark performance
    └── Measure speed, RAM, throughput

Phase 2: Optimization (OPTIONAL)
├── 1. Add preprocessing/postprocessing
│   └── Morphology, filtering, smoothing
├── 2. Ensemble với MONAI models (if GPU)
│   └── Combine LungMask + Whole Body CT
└── 3. Fine-tune if needed
    └── If Dice < 0.90 on hospital data

Phase 3: Deployment (FUTURE)
├── 1. Export pipeline to production
│   └── Docker container, FastAPI service
├── 2. Integration với PACS/DICOM
│   └── Automatic segmentation on new scans
└── 3. Monitoring and retraining
    └── Track performance, retrain quarterly
```

---

## 📊 Checklist Tích Hợp

- [ ] **Bước 1:** Tạo `LungMaskTransformd` class
  - [ ] Input: MONAI MetaTensor
  - [ ] Output: MetaTensor with metadata preserved
  - [ ] Handle spacing, orientation correctly

- [ ] **Bước 2:** Test alignment
  - [ ] Spacing matches: `original.GetSpacing() == pred.GetSpacing()`
  - [ ] Size matches: `original.GetSize() == pred.GetSize()`
  - [ ] Origin matches: `original.GetOrigin() == pred.GetOrigin()`
  - [ ] Direction matches: `original.GetDirection() == pred.GetDirection()`
  - [ ] Visual overlay: mask aligns with lung boundaries

- [ ] **Bước 3:** Benchmark performance
  - [ ] Dice score ≥ 0.95 (target)
  - [ ] Inference time ≤ 150s/scan (CPU)
  - [ ] RAM usage ≤ 4 GB

- [ ] **Bước 4:** Create end-to-end pipeline
  - [ ] Load → Preprocess → Inference → Postprocess → Save
  - [ ] Batch processing support
  - [ ] Error handling

- [ ] **Bước 5:** Documentation
  - [ ] Usage examples
  - [ ] API documentation
  - [ ] Troubleshooting guide

---

## 🔗 Next Steps

1. **Xem code implementation:**
   - `lungmask_transform.py`: Custom Transform wrapper
   - `monai_pipeline_example.py`: End-to-end pipeline demo

2. **Run example:**
   ```bash
   cd hospital-mlops/demo
   python monai_pipeline_example.py
   ```

3. **Đọc thêm:**
   - MONAI Transforms: https://docs.monai.io/en/stable/transforms.html
   - MONAI MetaTensor: https://docs.monai.io/en/stable/data.html#metatensor
   - LungMask Documentation: https://github.com/JoHof/lungmask

---

**Tác giả:** AI Assistant
**Ngày:** 2025-01-21
**Version:** 1.0
