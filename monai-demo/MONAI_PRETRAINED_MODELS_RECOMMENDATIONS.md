# Gợi ý Model MONAI Pretrained và Dataset phù hợp

> **Tài liệu này**: Đề xuất các MONAI pre-trained models và datasets phù hợp cho việc tích hợp model bên ngoài, fine-tuning và deployment

---

## 🎯 TL;DR - Khuyến nghị nhanh

**Cho Spleen Segmentation Task hiện tại:**

| Tiêu chí | Model đề xuất | Dataset đề xuất |
|----------|---------------|-----------------|
| **Quick Start** | MONAI Spleen CT Segmentation | Medical Segmentation Decathlon Task09 |
| **Best Performance** | MONAI Whole Body (channel 1 = spleen) | TotalSegmentator dataset |
| **Multi-organ Future** | MONAI Whole Body CT (104 organs) | TotalSegmentator + BTCV |
| **Research/Custom** | SegResNet from scratch | Custom hospital data |

---

## 📦 MONAI Pre-trained Models - Chi tiết

### **1. MONAI Spleen CT Segmentation** ⭐⭐⭐ BEST FOR SPLEEN

#### Thông tin model
```python
# Download
python -m monai.bundle download "spleen_ct_segmentation" --bundle_dir ./models/

# Hoặc từ Hugging Face
from monai.bundle import download
download(name="spleen_ct_segmentation", source="huggingface")
```

**Đặc điểm:**
- **Architecture**: 3D UNet
- **Training Dataset**: Medical Segmentation Decathlon Task09_Spleen
  - 41 training CT volumes
  - 20 validation volumes
- **Output**: 2 channels (background, spleen)
- **Performance**:
  - Mean Dice: **0.96** (on validation set)
  - Inference time: ~5-8s per volume (GPU)
- **Model size**: ~50MB
- **Input**: CT scans (HU values normalized)
- **Hugging Face**: https://huggingface.co/MONAI/example_spleen_segmentation

**Ưu điểm:**
- ✅ Chuyên biệt cho spleen → độ chính xác cao nhất
- ✅ Model nhẹ, inference nhanh
- ✅ Dễ fine-tune trên custom spleen data
- ✅ Được validate rộng rãi bởi MONAI community

**Nhược điểm:**
- ❌ Chỉ segment spleen (không có organs khác)
- ❌ Cần retrain nếu muốn thêm organs

**Use case phù hợp:**
- Production spleen segmentation pipeline
- Fine-tune với hospital-specific spleen data
- Baseline model cho clinical trials

---

### **2. MONAI Whole Body CT Segmentation** ⭐⭐⭐ BEST FOR MULTI-ORGAN

#### Thông tin model
```python
# Download
python -m monai.bundle download "wholeBody_ct_segmentation" --bundle_dir ./models/

# Load model
from monai.bundle import ConfigParser
config = ConfigParser()
config.read_config("models/wholeBody_ct_segmentation/configs/inference.json")
model = config.get_parsed_content("network_def")
```

**Đặc điểm:**
- **Architecture**: SegResNet ensemble
- **Training Dataset**: TotalSegmentator (1,204 CT volumes)
- **Output**: 105 channels (0=background, 1=spleen, 2-104=other organs)
- **Performance**:
  - Mean Dice across all organs: 0.80
  - **Spleen Dice: ~0.94-0.96**
- **Model size**: 500MB (high-res), 200MB (low-res)
- **Inference time**:
  - High-res (1.5mm): ~30s (V100 GPU)
  - Low-res (3.0mm): ~6s (V100 GPU)
- **GPU memory**: 28GB (high-res), 6GB (low-res)

**104 organs bao gồm:**
- Channel 1: **Spleen** ✅
- Channel 2-3: Kidneys (left/right)
- Channel 5: Liver
- Channel 13-17: Lungs (5 lobes)
- Channel 43: Trachea
- ... và 97 organs khác

**Ưu điểm:**
- ✅ Multi-organ segmentation → future-proof
- ✅ State-of-the-art architecture (SegResNet)
- ✅ Có sẵn trong project của bạn (`hospital-mlops/pretrained-models/wholeBody_ct_segmentation/`)
- ✅ Hỗ trợ TensorRT acceleration
- ✅ Transfer learning cho custom organs

**Nhược điểm:**
- ❌ Model lớn (500MB)
- ❌ Cần GPU memory cao (28GB cho high-res)
- ❌ Inference chậm hơn spleen-only model

**Use case phù hợp:**
- Hospital-wide multi-organ segmentation system
- Research projects cần nhiều anatomical structures
- Fine-tune cho specific organ subset

**Cách extract chỉ spleen:**
```python
# Inference
output = model(ct_volume)  # Shape: [B, 105, H, W, D]

# Extract spleen only (channel 1)
spleen_mask = output[:, 1:2, ...]  # Shape: [B, 1, H, W, D]

# Or argmax then filter
pred_labels = torch.argmax(output, dim=1)  # [B, H, W, D]
spleen_only = (pred_labels == 1).float()
```

---

### **3. MONAI SegResNet (Generic Architecture)** ⭐⭐ CUSTOMIZABLE

#### Thông tin
```python
from monai.networks.nets import SegResNet

# Create model from scratch
model = SegResNet(
    spatial_dims=3,
    in_channels=1,
    out_channels=2,  # background + spleen
    init_filters=32,
    blocks_down=[1, 2, 2, 4],
    blocks_up=[1, 1, 1],
    dropout_prob=0.2,
)
```

**Đặc điểm:**
- **Architecture**: Residual encoder + VAE decoder
- **Training**: Train from scratch hoặc từ ImageNet weights
- **Flexibility**: Customize số channels, depth, filters
- **Performance**: Phụ thuộc vào training data và hyperparameters

**Ưu điểm:**
- ✅ Hoàn toàn tùy chỉnh architecture
- ✅ Best cho custom medical imaging tasks
- ✅ State-of-the-art performance khi trained well

**Nhược điểm:**
- ❌ Cần train from scratch hoặc với custom pretrained weights
- ❌ Yêu cầu large training dataset
- ❌ Tốn thời gian training (nhiều epochs)

**Use case phù hợp:**
- Custom medical imaging tasks không có pretrained models
- Research với novel architectures
- Fine-grained control over model design

---

### **4. MONAI UNETR (Transformer-based)** ⭐⭐ RESEARCH

#### Thông tin
```python
from monai.networks.nets import UNETR

model = UNETR(
    in_channels=1,
    out_channels=2,
    img_size=(96, 96, 96),
    feature_size=16,
    hidden_size=768,
    mlp_dim=3072,
    num_heads=12,
    pos_embed="perceptron",
)
```

**Đặc điểm:**
- **Architecture**: Vision Transformer encoder + CNN decoder
- **Training**: Có pretrained weights từ self-supervised learning
- **Performance**: State-of-the-art cho nhiều medical imaging tasks
- **Model size**: ~300-400MB

**Ưu điểm:**
- ✅ Transformer architecture → better long-range dependencies
- ✅ Self-supervised pretrained weights available
- ✅ Excellent performance on small datasets (with pretraining)

**Nhược điểm:**
- ❌ Lớn và chậm hơn CNN-based models
- ❌ Cần GPU memory cao
- ❌ Khó fine-tune hơn U-Net variants

---

## 📊 Datasets - Phù hợp cho Fine-tuning

### **1. Medical Segmentation Decathlon - Task09_Spleen** ⭐⭐⭐ PERFECT

**Download:**
```bash
# Official link
wget https://drive.google.com/uc?id=1jzeNU1EKnK81PyTsrx0ujfNl-t0Jo8uE -O Task09_Spleen.tar
tar -xvf Task09_Spleen.tar
```

**Thông tin:**
- **Source**: http://medicaldecathlon.com/
- **Organ**: Spleen only
- **Modality**: CT scans
- **Size**:
  - Training: 41 volumes (~2.5GB)
  - Testing: 20 volumes (~1.2GB)
- **Annotations**: Expert-level manual segmentation
- **Format**: NIfTI (.nii.gz)
- **License**: CC BY-SA 4.0 (free for research & commercial)

**Đặc điểm dataset:**
- High-quality annotations
- Diverse patient demographics
- Various CT scanner manufacturers
- Different imaging protocols

**Ưu điểm:**
- ✅ Chuyên biệt cho spleen
- ✅ Gold standard annotations
- ✅ Widely used benchmark → comparable results
- ✅ Đủ lớn cho fine-tuning

**Cách sử dụng:**
```python
# Data structure
Task09_Spleen/
├── imagesTr/
│   ├── spleen_1.nii.gz
│   ├── spleen_2.nii.gz
│   └── ... (41 files)
├── labelsTr/
│   ├── spleen_1.nii.gz
│   └── ...
├── imagesTs/
│   └── ... (20 test files)
└── dataset.json  # Metadata

# Load with MONAI
from monai.data import Dataset, load_decathlon_datalist

data_list = load_decathlon_datalist(
    data_list_file_path="Task09_Spleen/dataset.json",
    data_list_key="training",
    base_dir="Task09_Spleen"
)
```

**Gợi ý sử dụng:**
- **Baseline training**: Train from scratch hoặc fine-tune MONAI spleen model
- **Validation**: Compare với published results (Dice 0.96)
- **Data augmentation**: Add your hospital data to this dataset

---

### **2. TotalSegmentator Dataset** ⭐⭐⭐ COMPREHENSIVE

**Download:**
```bash
# Install TotalSegmentator tool
pip install TotalSegmentator

# Download specific subset (e.g., 10 samples)
wget https://zenodo.org/record/6802614/files/Totalsegmentator_dataset_v201.zip
```

**Thông tin:**
- **Source**: https://github.com/wasserth/TotalSegmentator
- **Organs**: 104 anatomical structures (including spleen)
- **Size**:
  - Full dataset: 1,228 CT scans (~300GB)
  - Subset v1.0: 117 scans (~30GB)
- **Annotations**: Semi-automated + manual correction
- **Format**: NIfTI (.nii.gz)
- **License**: CC BY 4.0

**104 organs bao gồm:**
- Spleen, liver, kidneys, pancreas
- Lungs (5 lobes)
- Heart chambers
- Major vessels
- Vertebrae
- Ribs, bones
- Muscles

**Ưu điểm:**
- ✅ Massive multi-organ dataset
- ✅ Same dataset used by MONAI Whole Body model
- ✅ Excellent for multi-task learning
- ✅ Future-proof cho expanded clinical needs

**Nhược điểm:**
- ❌ Rất lớn (300GB full dataset)
- ❌ Download lâu, cần storage lớn
- ❌ Processing phức tạp (104 labels)

**Cách sử dụng với MONAI:**
```python
# Đã có sẵn merged labels trong project của bạn
# wholeBody_ct_segmentation/configs/metadata.json

# Extract spleen-only from multi-label
import nibabel as nib
import numpy as np

# Load multi-label file
img = nib.load("merged_labels.nii.gz")
labels = img.get_fdata()

# Extract spleen only (label=1)
spleen_mask = (labels == 1).astype(np.uint8)

# Save
spleen_img = nib.Nifti1Image(spleen_mask, img.affine)
nib.save(spleen_img, "spleen_only.nii.gz")
```

---

### **3. BTCV (Beyond The Cranial Vault)** ⭐⭐ MULTI-ORGAN

**Download:**
```bash
# Requires Synapse account (free registration)
# https://www.synapse.org/#!Synapse:syn3193805/wiki/217789
```

**Thông tin:**
- **Source**: MICCAI 2015 Multi-Atlas Labeling Challenge
- **Organs**: 13 abdominal organs (including spleen)
- **Size**:
  - Training: 30 CT scans
  - Testing: 20 CT scans
- **Annotations**: Multi-atlas expert segmentation
- **Format**: NIfTI (.nii.gz)

**13 organs:**
1. Spleen ✅
2. Right kidney
3. Left kidney
4. Gallbladder
5. Esophagus
6. Liver
7. Stomach
8. Aorta
9. Inferior vena cava
10. Portal and splenic veins
11. Pancreas
12. Right adrenal gland
13. Left adrenal gland

**Ưu điểm:**
- ✅ High-quality multi-organ annotations
- ✅ Benchmark dataset → published baselines
- ✅ Smaller size, faster to work with

**Nhược điểm:**
- ❌ Chỉ 30 training volumes (nhỏ)
- ❌ Abdominal only (không có lungs, heart, etc.)
- ❌ Cần registration (free) để download

---

### **4. Custom Hospital Data** ⭐⭐⭐ BEST FOR PRODUCTION

**Khuyến nghị:**
- **Minimum size**: 50-100 CT scans để fine-tune pretrained model
- **Annotations**:
  - Manual segmentation bởi radiologists
  - Hoặc pseudo-labels từ pretrained model + manual correction
- **Quality**: Hospital-specific data → best performance in production

**Quy trình chuẩn bị:**
```python
# 1. Deidentify DICOM data
from pydicom import dcmread
# Remove patient info, dates, etc.

# 2. Convert DICOM to NIfTI
import dicom2nifti
dicom2nifti.convert_directory("dicom_folder/", "nifti_folder/")

# 3. Quality check
# - Check orientation (RAS)
# - Check spacing consistency
# - Verify HU value range

# 4. Create annotations
# Option A: Use MONAI Label + 3D Slicer for manual annotation
# Option B: Generate pseudo-labels with pretrained model, then correct

# 5. Split data
# - Train: 70%
# - Validation: 15%
# - Test: 15%
```

---

## 🎯 Khuyến nghị cụ thể cho Project của bạn

### **Scenario 1: Quick Start - Spleen Only**

**Model:** MONAI Spleen CT Segmentation
**Dataset:** Medical Decathlon Task09_Spleen

**Workflow:**
1. Download model từ Hugging Face
2. Download Task09_Spleen dataset
3. Fine-tune trên hospital data (nếu có) với ~20 epochs
4. Deploy vào Kubeflow pipeline

**Estimated time:** 1-2 ngày

**Code:**
```python
# Download
python -m monai.bundle download "spleen_ct_segmentation" --source "huggingface"

# Fine-tune
python -m monai.bundle run \
  --config_file configs/train.json \
  --dataset_dir /path/to/Task09_Spleen \
  --max_epochs 20
```

---

### **Scenario 2: Production-Ready - Sử dụng model đã có**

**Model:** MONAI Whole Body CT Segmentation (đã có trong project)
**Dataset:** TotalSegmentator (hoặc hospital data)

**Workflow:**
1. Sử dụng model đã download: `hospital-mlops/pretrained-models/wholeBody_ct_segmentation/`
2. Extract spleen channel (channel 1)
3. Fine-tune trên custom data nếu cần
4. Update Kubeflow pipeline

**Estimated time:** 2-3 ngày

**Code:**
```python
# Load existing model
model_path = "hospital-mlops/pretrained-models/wholeBody_ct_segmentation/models/model.pt"
config_path = "hospital-mlops/pretrained-models/wholeBody_ct_segmentation/configs/inference.json"

from monai.bundle import ConfigParser
config = ConfigParser()
config.read_config(config_path)
model = config.get_parsed_content("network_def")
model.load_state_dict(torch.load(model_path))

# Extract spleen
output = model(ct_volume)
spleen = output[:, 1:2, ...]  # Channel 1
```

---

### **Scenario 3: Research & Custom - Train from Scratch**

**Model:** SegResNet hoặc UNETR
**Dataset:** Combination (Task09 + TotalSegmentator + Hospital data)

**Workflow:**
1. Aggregate multiple datasets
2. Train SegResNet from scratch hoặc ImageNet weights
3. Extensive validation
4. Production deployment

**Estimated time:** 1-2 tuần

---

## 📋 Comparison Table - Final Recommendation

| Tiêu chí | Spleen CT Seg | Whole Body CT | SegResNet Scratch |
|----------|---------------|---------------|-------------------|
| **Accuracy (Spleen)** | ⭐⭐⭐⭐⭐ 0.96 | ⭐⭐⭐⭐ 0.94 | ⭐⭐⭐ 0.85-0.95 |
| **Speed** | ⭐⭐⭐⭐⭐ 5-8s | ⭐⭐⭐ 30s | ⭐⭐⭐⭐ 10-15s |
| **Model Size** | ⭐⭐⭐⭐⭐ 50MB | ⭐⭐ 500MB | ⭐⭐⭐⭐ 100MB |
| **Multi-organ** | ❌ Spleen only | ✅ 104 organs | ✅ Customizable |
| **Fine-tune Ease** | ⭐⭐⭐⭐⭐ Easy | ⭐⭐⭐⭐ Medium | ⭐⭐ Hard |
| **GPU Memory** | ⭐⭐⭐⭐⭐ 8GB | ⭐⭐ 28GB | ⭐⭐⭐⭐ 12GB |
| **Production Ready** | ✅ Yes | ✅ Yes | ⚠️ Needs validation |
| **Setup Time** | ⭐⭐⭐⭐⭐ 1 day | ⭐⭐⭐⭐ 2 days | ⭐⭐ 1-2 weeks |

---

## 🚀 Khuyến nghị cuối cùng

### **Cho dự án hiện tại (Spleen Segmentation on Kubeflow):**

**Lựa chọn tốt nhất: MONAI Whole Body CT Segmentation (đã có sẵn!)**

**Lý do:**
1. ✅ **Đã download sẵn** trong project: `hospital-mlops/pretrained-models/wholeBody_ct_segmentation/`
2. ✅ **Spleen performance tốt**: Dice ~0.94-0.96
3. ✅ **Future-proof**: 104 organs → mở rộng dễ dàng
4. ✅ **Production-ready**: MONAI official, well-tested
5. ✅ **Hỗ trợ low-res version**: Nếu GPU memory hạn chế

**Dataset:**
- **Primary**: Medical Decathlon Task09_Spleen (để validate)
- **Secondary**: Custom hospital data (để fine-tune cho production)

**Timeline:**
- **Ngày 1**: Setup data preprocessing pipeline
- **Ngày 2**: Implement model wrapper và inference
- **Ngày 3**: Fine-tuning (optional) trên custom data
- **Ngày 4**: Evaluation và metrics
- **Ngày 5**: Update Kubeflow pipeline và deployment

---

## 📚 Resources

**Downloads:**
```bash
# MONAI Spleen model (Hugging Face)
huggingface-cli download MONAI/example_spleen_segmentation --local-dir ./models/spleen_ct_seg

# Medical Decathlon Task09
wget https://drive.google.com/uc?id=1jzeNU1EKnK81PyTsrx0ujfNl-t0Jo8uE -O Task09_Spleen.tar

# Check what you already have
ls -lh hospital-mlops/pretrained-models/wholeBody_ct_segmentation/models/
```

**Documentation:**
- MONAI Bundle: https://docs.monai.io/en/stable/bundle.html
- Model Zoo: https://github.com/Project-MONAI/model-zoo
- Medical Decathlon: http://medicaldecathlon.com/
- TotalSegmentator: https://github.com/wasserth/TotalSegmentator

---

**Tạo bởi**: MONAI Integration Team
**Ngày**: 2025-10-31
**Version**: 1.0
