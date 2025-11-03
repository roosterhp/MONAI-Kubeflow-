# Architecture: EfficientNetV2-S Integration with MONAI

## 1. Model Selection Rationale

### Why EfficientNetV2-S from timm?

#### 1.1 Problem Context
- **Task**: 2D medical image classification (X-ray, Ultrasound)
- **Requirements**:
  - High accuracy on limited medical data (few thousand samples)
  - Fast inference for clinical settings (<100ms)
  - Transfer learning from ImageNet
  - Production-grade stability

#### 1.2 EfficientNetV2-S Advantages

| Criteria | EfficientNetV2-S | MONAI Zoo Models | Hugging Face Models |
|----------|------------------|------------------|---------------------|
| **2D Image Classification** | ✅ Designed for 2D | ❌ Mostly 3D segmentation | ⚠️ Limited medical-specific |
| **ImageNet Pretrained** | ✅ Official weights | ❌ Medical-only | ✅ Available |
| **Speed** | ✅ 2.5x faster than V1 | N/A | ⚠️ Varies |
| **Transfer Learning** | ✅ Excellent | ✅ Good for segmentation | ✅ Good |
| **Model Size** | ✅ 24M params (small) | ⚠️ 50-200M | ⚠️ 80-300M |
| **Medical Imaging Papers** | ✅ 500+ citations | ✅ Native support | ⚠️ Limited validation |
| **Production Readiness** | ✅ PyTorch Hub | ✅ MONAI Bundle | ⚠️ Varies |

**Decision**: EfficientNetV2-S is optimal for 2D medical classification due to:
1. **Best speed/accuracy tradeoff** for clinical deployment
2. **Strong transfer learning** from ImageNet → Medical domain
3. **Small footprint** (24M params) → faster training, lower inference cost
4. **Validated architecture** in medical literature
5. **Not available in MONAI Zoo** (MONAI focuses on 3D segmentation)

#### 1.3 Why NOT MONAI/Hugging Face Models?

**MONAI Model Zoo**:
- Specialized for 3D volumetric data (CT, MRI)
- Segmentation-focused (U-Net, SegResNet, UNETR)
- No pretrained 2D classifiers for X-ray/Ultrasound
- Classification models limited to 3D volumes

**Hugging Face**:
- Vision Transformers (ViT) available but:
  - Require larger datasets (10k+ images)
  - Slower inference (150-300ms)
  - Less validated in medical imaging
- ResNet variants available but outdated vs EfficientNetV2

**External timm Library**:
- 500+ pretrained models including EfficientNetV2
- State-of-the-art architectures
- Active maintenance
- Easy integration with PyTorch/MONAI

---

## 2. Integration Architecture

### 2.1 System Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    Kubeflow Pipeline                        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌────────────┐   ┌────────────┐   ┌────────────┐         │
│  │ Preprocess │──▶│   Train    │──▶│  Evaluate  │         │
│  │ Component  │   │ Component  │   │ Component  │         │
│  └────────────┘   └────────────┘   └────────────┘         │
│                          │                │                 │
│                          ▼                ▼                 │
│                    ┌────────────┐   ┌────────────┐         │
│                    │  Register  │   │   Deploy   │         │
│                    │ Component  │──▶│ Component  │         │
│                    └────────────┘   └────────────┘         │
│                                           │                 │
└───────────────────────────────────────────┼─────────────────┘
                                            ▼
                    ┌──────────────────────────────┐
                    │      KServe / Triton         │
                    │   InferenceService           │
                    ├──────────────────────────────┤
                    │  - Predictor (100%)          │
                    │  - Canary (0→10→50→100%)     │
                    │  - Rollback capability       │
                    └──────────────────────────────┘
```

### 2.2 Component Breakdown

#### Component 1: Preprocess
**Input**: Raw medical images (DICOM/PNG/JPG)
**Output**: Preprocessed tensors + metadata
**Tech Stack**: MONAI transforms + PyTorch

**Key Operations**:
```python
# Pseudo-structure
Compose([
    LoadImage(),
    EnsureChannelFirst(),
    ScaleIntensity(minv=0, maxv=1),
    Resize((224, 224)),              # EfficientNetV2-S input size
    RandRotate(prob=0.5),
    RandFlip(prob=0.5),
    Normalize(mean=[0.485, 0.456, 0.406],  # ImageNet stats
              std=[0.229, 0.224, 0.225]),
])
```

#### Component 2: Train
**Input**: Preprocessed data + config
**Output**: Fine-tuned model checkpoint
**Tech Stack**: MONAI Engine + timm model

**Model Wrapper Structure**:
```python
# Pseudo-structure
class EfficientNetV2Wrapper(nn.Module):
    """
    Wraps timm EfficientNetV2-S for MONAI compatibility
    """
    def __init__(self, num_classes, pretrained=True):
        # Load timm model
        self.backbone = timm.create_model(
            'efficientnetv2_rw_s',
            pretrained=pretrained,
            num_classes=num_classes
        )

    def forward(self, x):
        return self.backbone(x)
```

**Training Strategy**:
1. **Stage 1**: Freeze backbone, train head (5 epochs)
2. **Stage 2**: Unfreeze, full fine-tune (20 epochs)
3. **Stage 3**: Low LR refinement (5 epochs)

#### Component 3: Evaluate
**Input**: Model checkpoint + test data
**Output**: Medical metrics JSON
**Tech Stack**: scikit-learn + custom metrics

**Metrics Computed**:
```python
# Pseudo-structure
metrics = {
    "auc_roc": compute_auc(y_true, y_pred_proba),
    "f1_score": f1_score(y_true, y_pred),
    "accuracy": accuracy_score(y_true, y_pred),
    "sensitivity": recall_score(y_true, y_pred),
    "specificity": compute_specificity(y_true, y_pred),
    "ece": expected_calibration_error(y_true, y_pred_proba),
    "confusion_matrix": confusion_matrix(y_true, y_pred),
    "per_class_metrics": {
        class_name: {
            "precision": ...,
            "recall": ...,
            "f1": ...
        }
    }
}
```

**Expected Calibration Error (ECE)**:
- Critical for medical AI - measures prediction confidence reliability
- Formula: `ECE = Σ |accuracy(bin_i) - confidence(bin_i)| * |bin_i| / n`
- Target: ECE < 0.10 (well-calibrated)

#### Component 4: Register
**Input**: Validated model + metadata
**Output**: Model registry entry (MLflow/custom)
**Tech Stack**: MLflow Model Registry

**Metadata Stored**:
```yaml
model:
  name: efficientnetv2-s-xray
  version: v1.2.3
  architecture: efficientnetv2_rw_s
  input_shape: [1, 3, 224, 224]
  num_classes: 5

training:
  dataset: xray_chest_5class
  train_samples: 5000
  val_samples: 1000
  epochs: 30

metrics:
  auc: 0.942
  f1: 0.889
  accuracy: 0.901
  ece: 0.082

export:
  torchscript: model.pt
  onnx: model.onnx
  triton_ready: true
```

#### Component 5: Deploy
**Input**: Model artifacts + InferenceService spec
**Output**: Running KServe endpoint
**Tech Stack**: KServe + Triton/TorchServe

**Deployment Flow**:
```
Register → Export → Build Container → Deploy InferenceService
```

---

## 3. Model Export Strategy

### 3.1 TorchScript Export

**Purpose**: Native PyTorch deployment (TorchServe)

**Process**:
```python
# Pseudo-structure
# 1. Load trained model
model = EfficientNetV2Wrapper.load_from_checkpoint("best_model.ckpt")
model.eval()

# 2. Trace with example input
example_input = torch.randn(1, 3, 224, 224)
traced_model = torch.jit.trace(model, example_input)

# 3. Save
traced_model.save("model.pt")

# 4. Validate
loaded = torch.jit.load("model.pt")
assert torch.allclose(loaded(example_input), model(example_input))
```

**Advantages**:
- Native PyTorch execution
- Easy debugging
- Good for TorchServe backend

**Disadvantages**:
- Python-only deployment
- Slower than ONNX/TensorRT

### 3.2 ONNX Export

**Purpose**: Cross-framework deployment (Triton Inference Server)

**Process**:
```python
# Pseudo-structure
torch.onnx.export(
    model,
    example_input,
    "model.onnx",
    export_params=True,
    opset_version=13,
    input_names=['input'],
    output_names=['output'],
    dynamic_axes={
        'input': {0: 'batch_size'},
        'output': {0: 'batch_size'}
    }
)

# Validate with ONNX Runtime
import onnxruntime as ort
session = ort.InferenceSession("model.onnx")
onnx_output = session.run(None, {'input': input_numpy})
```

**Advantages**:
- Cross-platform (C++, Java, etc.)
- Optimized for Triton
- TensorRT conversion possible

**Disadvantages**:
- Some ops not supported (requires simplification)
- Harder to debug

### 3.3 Format Selection

| Backend | Format | Latency (p95) | Throughput | Recommendation |
|---------|--------|---------------|------------|----------------|
| TorchServe | TorchScript | 80ms | 50 req/s | ✅ Development |
| Triton | ONNX | 45ms | 120 req/s | ✅ Production |
| Triton | TensorRT | 25ms | 200 req/s | ⭐ Production (GPU) |

**Decision**: Primary = ONNX for Triton, Fallback = TorchScript

---

## 4. MONAI Integration Points

### 4.1 Data Loading (MONAI Strength)

```python
# Use MONAI's medical imaging loaders
from monai.data import Dataset, DataLoader, CacheDataset

# MONAI handles DICOM, NIfTI, PNG, JPG automatically
train_ds = CacheDataset(
    data=train_files,
    transform=train_transforms,  # MONAI transforms
    cache_rate=1.0,
)

train_loader = DataLoader(
    train_ds,
    batch_size=32,
    shuffle=True,
    num_workers=4,
)
```

### 4.2 Transforms (MONAI Strength)

```python
from monai.transforms import (
    Compose, LoadImaged, EnsureChannelFirstd,
    ScaleIntensityd, Resized, RandRotated
)

# MONAI transforms are medical-imaging aware
train_transforms = Compose([
    LoadImaged(keys=["image"]),          # Handles DICOM metadata
    EnsureChannelFirstd(keys=["image"]), # Handles grayscale/RGB
    ScaleIntensityd(keys=["image"]),     # Medical intensity windowing
    Resized(keys=["image"], spatial_size=(224, 224)),
    RandRotated(keys=["image"], prob=0.5, range_x=0.2),
])
```

### 4.3 Training Engine (MONAI Strength)

```python
from monai.engines import SupervisedTrainer

# MONAI engine handles:
# - Mixed precision
# - Gradient accumulation
# - Model checkpointing
# - TensorBoard logging

trainer = SupervisedTrainer(
    device=device,
    max_epochs=30,
    train_data_loader=train_loader,
    network=efficientnet_wrapper,  # Our timm model
    optimizer=optimizer,
    loss_function=loss_fn,
    inferer=SimpleInferer(),
    amp=True,  # Automatic Mixed Precision
)

trainer.run()
```

### 4.4 Integration Pattern

```
┌───────────────────────────────────────┐
│      MONAI Framework (Wrapper)        │
├───────────────────────────────────────┤
│                                       │
│  Data Loaders ─────┐                 │
│  Transforms ───────┼──▶ Training     │
│  Training Engine ──┘     Pipeline    │
│                            │          │
│                            ▼          │
│                    ┌────────────────┐ │
│                    │ timm Model     │ │
│                    │ EfficientNetV2 │ │
│                    └────────────────┘ │
│                                       │
└───────────────────────────────────────┘
```

**Key Insight**: MONAI provides medical imaging infrastructure, timm provides SOTA architecture

---

## 5. Data Structure Requirements

### 5.1 Expected Input Format

```
data/
├── train/
│   ├── class_0/
│   │   ├── img_001.png
│   │   ├── img_002.png
│   │   └── ...
│   ├── class_1/
│   │   └── ...
│   └── class_N/
│       └── ...
├── val/
│   └── (same structure)
└── test/
    └── (same structure)
```

Or JSON-based (MONAI style):
```json
{
  "training": [
    {
      "image": "train/img_001.png",
      "label": 0,
      "metadata": {
        "patient_id": "P001",
        "age": 45,
        "modality": "X-ray"
      }
    }
  ],
  "validation": [...],
  "testing": [...]
}
```

### 5.2 Preprocessing Requirements

| Step | Operation | Rationale |
|------|-----------|-----------|
| 1 | Resize to 224x224 | EfficientNetV2-S input size |
| 2 | Normalize (ImageNet stats) | Match pretraining distribution |
| 3 | Channel adjustment | Convert grayscale → RGB if needed |
| 4 | Intensity windowing | Medical image specific (HU, etc.) |
| 5 | Augmentation | RandRotate, RandFlip, RandZoom |

---

## 6. Technical Specifications

### 6.1 Model Specs

```yaml
Model:
  Architecture: EfficientNetV2-S (timm)
  Parameters: 24M
  Input: [batch, 3, 224, 224]
  Output: [batch, num_classes]

Pretrained:
  Source: ImageNet-1K
  Top-1 Accuracy: 83.9%
  Top-5 Accuracy: 96.7%

Fine-tuning:
  Trainable Params: 24M (full) or 2M (head-only)
  Expected Training Time: 2-4 hours (single V100)
  Memory: ~8GB GPU
```

### 6.2 Training Hyperparameters

```yaml
Optimizer:
  Type: AdamW
  LR: 1e-4 (backbone) / 1e-3 (head)
  Weight Decay: 0.01

Scheduler:
  Type: CosineAnnealingLR
  T_max: 30 epochs
  Eta_min: 1e-6

Loss:
  Type: CrossEntropyLoss with Label Smoothing (0.1)

Augmentation:
  RandRotate: prob=0.5, range=(-15°, 15°)
  RandFlip: prob=0.5, spatial_axis=1
  RandZoom: prob=0.3, min=0.9, max=1.1
  ColorJitter: prob=0.3, brightness=0.2, contrast=0.2
```

### 6.3 Inference Specs

```yaml
Input:
  Format: PNG/JPG/DICOM
  Size: 224x224 (auto-resized)
  Channels: 3 (grayscale auto-converted)

Output:
  Format: JSON
  Structure:
    predictions:
      - class: "Normal"
        probability: 0.85
      - class: "Pneumonia"
        probability: 0.12
    confidence: 0.85
    model_version: "v1.2.3"
    latency_ms: 45
```

---

## 7. Design Decisions Summary

| Decision | Rationale |
|----------|-----------|
| **timm EfficientNetV2-S** | Best speed/accuracy for 2D medical classification |
| **MONAI wrapper** | Leverage medical imaging infrastructure |
| **Two-stage training** | Faster convergence, better transfer learning |
| **ONNX export** | Production-grade serving with Triton |
| **ECE metric** | Critical for clinical decision support |
| **Canary deployment** | Safe rollout for medical applications |
| **Kubeflow pipeline** | Reproducible MLOps workflow |

---

## 8. Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| **Domain shift** (ImageNet → Medical) | High | Two-stage fine-tuning, extensive validation |
| **Small dataset** (<5k images) | Medium | Strong augmentation, early stopping |
| **Class imbalance** | High | Weighted loss, stratified sampling |
| **Model overconfidence** | Critical | ECE monitoring, temperature scaling |
| **Deployment latency** | Medium | ONNX optimization, TensorRT conversion |
| **Model drift** | High | Continuous monitoring, retraining triggers |

---

## Next Steps

1. Review `PIPELINE_DESIGN.md` for implementation details
2. Check `DEPLOYMENT.md` for KServe configuration
3. Follow `5DAY_PLAN.md` for execution timeline
