# External Model Integration & Fine-tuning Guide
## MONAI + Kubeflow Workflow

> **Mục tiêu tuần**: Tích hợp model bên ngoài (non-Hugging Face), fine-tuning, đánh giá và cập nhật deployment

---

## 📋 Tổng quan

Tài liệu này hướng dẫn chi tiết quy trình tích hợp một model bên ngoài (không phải từ Hugging Face) vào MONAI framework, fine-tune với dữ liệu tùy chỉnh, đánh giá hiệu suất và cập nhật model đang chạy trên Kubeflow.

---

## 🎯 Các bước thực hiện

### **Bước 1: Lựa chọn và Tích hợp Model Bên Ngoài**

#### 1.1 Các tùy chọn model phù hợp với Medical Imaging

**A. nnU-Net (Recommended for Medical Segmentation)**
- **Nguồn**: https://github.com/MIC-DKFZ/nnUNet
- **Ưu điểm**:
  - State-of-the-art cho medical image segmentation
  - Tự động tối ưu hóa preprocessing và augmentation
  - Đã được chứng minh hiệu quả trên nhiều organ segmentation tasks
- **Tích hợp**: Wrap nnU-Net architecture vào MONAI network

**B. 3D U-Net Variants**
- **Nguồn**: PyTorch implementation hoặc custom architecture
- **Ưu điểm**: Kiến trúc proven cho 3D medical imaging
- **Tích hợp**: Implement trực tiếp bằng PyTorch và wrap với MONAI

**C. TransUNet / UNETR Variants**
- **Nguồn**: Custom implementation hoặc research papers
- **Ưu điểm**: Transformer-based, hiệu quả với long-range dependencies
- **Tích hợp**: Custom implementation với MONAI training framework

**D. ResUNet / Attention U-Net**
- **Nguồn**: GitHub implementations, research papers
- **Ưu điểm**: Enhanced feature extraction với attention mechanisms
- **Tích hợp**: PyTorch to MONAI adapter pattern

#### 1.2 Cấu trúc tích hợp

```python
# File: monai-demo/models/external_model_wrapper.py

import torch
import torch.nn as nn
from monai.networks.nets import BasicUNet
from typing import Optional, Sequence

class ExternalModelWrapper(nn.Module):
    """
    Wrapper class để tích hợp external model vào MONAI ecosystem

    Hỗ trợ:
    - Custom architecture từ bên ngoài
    - Pretrained weights loading
    - MONAI-compatible input/output
    """

    def __init__(
        self,
        spatial_dims: int = 3,
        in_channels: int = 1,
        out_channels: int = 2,
        features: Sequence[int] = (32, 64, 128, 256, 512),
        external_weights_path: Optional[str] = None,
        freeze_encoder: bool = False
    ):
        super().__init__()

        # TODO: Replace with actual external model architecture
        # Example: nnU-Net, custom 3D U-Net, TransUNet, etc.
        self.model = self._build_external_model(
            spatial_dims, in_channels, out_channels, features
        )

        # Load pretrained weights if provided
        if external_weights_path:
            self._load_external_weights(external_weights_path)

        # Optionally freeze encoder for transfer learning
        if freeze_encoder:
            self._freeze_encoder()

    def _build_external_model(self, spatial_dims, in_channels, out_channels, features):
        """Build or import external model architecture"""
        # Placeholder - replace with actual external model
        return BasicUNet(
            spatial_dims=spatial_dims,
            in_channels=in_channels,
            out_channels=out_channels,
            features=features,
        )

    def _load_external_weights(self, weights_path: str):
        """Load weights from external source (not Hugging Face)"""
        checkpoint = torch.load(weights_path, map_location='cpu')

        # Handle different checkpoint formats
        if 'state_dict' in checkpoint:
            state_dict = checkpoint['state_dict']
        elif 'model' in checkpoint:
            state_dict = checkpoint['model']
        else:
            state_dict = checkpoint

        # Load with potential key mapping
        self.model.load_state_dict(state_dict, strict=False)
        print(f"✅ Loaded external weights from: {weights_path}")

    def _freeze_encoder(self):
        """Freeze encoder layers for transfer learning"""
        for name, param in self.model.named_parameters():
            if 'encoder' in name or 'down' in name:
                param.requires_grad = False
        print("🔒 Encoder layers frozen for transfer learning")

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.model(x)
```

---

### **Bước 2: Chuẩn bị Dữ liệu Fine-tuning**

#### 2.1 Cấu trúc dữ liệu

```
monai-demo/
├── data/
│   ├── custom_dataset/
│   │   ├── train/
│   │   │   ├── images/
│   │   │   │   ├── patient_001.nii.gz
│   │   │   │   ├── patient_002.nii.gz
│   │   │   │   └── ...
│   │   │   └── labels/
│   │   │       ├── patient_001.nii.gz
│   │   │       ├── patient_002.nii.gz
│   │   │       └── ...
│   │   ├── val/
│   │   │   ├── images/
│   │   │   └── labels/
│   │   └── test/
│   │       ├── images/
│   │       └── labels/
│   └── data_splits.json
```

#### 2.2 Data preprocessing script

```python
# File: monai-demo/scripts/prepare_custom_data.py

import json
from pathlib import Path
from monai.data import Dataset, DataLoader
from monai.transforms import (
    Compose, LoadImaged, EnsureChannelFirstd, Spacingd,
    Orientationd, ScaleIntensityRanged, CropForegroundd,
    RandCropByPosNegLabeld, RandRotate90d, RandFlipd,
    ToTensord, EnsureTyped
)

class CustomDataPreparation:
    """Prepare custom dataset for MONAI training"""

    def __init__(self, data_root: str, cache_dir: str = "/mnt/data/cache"):
        self.data_root = Path(data_root)
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True, parents=True)

    def create_data_dicts(self):
        """Create data dictionaries for train/val/test"""
        splits = {}

        for split in ['train', 'val', 'test']:
            image_dir = self.data_root / split / 'images'
            label_dir = self.data_root / split / 'labels'

            data_dicts = []
            for img_path in sorted(image_dir.glob('*.nii.gz')):
                label_path = label_dir / img_path.name
                if label_path.exists():
                    data_dicts.append({
                        'image': str(img_path),
                        'label': str(label_path)
                    })

            splits[split] = data_dicts
            print(f"✅ {split}: {len(data_dicts)} samples")

        # Save splits
        splits_file = self.data_root / 'data_splits.json'
        with open(splits_file, 'w') as f:
            json.dump(splits, f, indent=2)

        return splits

    def get_train_transforms(self):
        """Training transforms with augmentation"""
        return Compose([
            LoadImaged(keys=["image", "label"]),
            EnsureChannelFirstd(keys=["image", "label"]),
            Spacingd(keys=["image", "label"], pixdim=(1.5, 1.5, 2.0), mode=("bilinear", "nearest")),
            Orientationd(keys=["image", "label"], axcodes="RAS"),
            ScaleIntensityRanged(keys=["image"], a_min=-57, a_max=164, b_min=0.0, b_max=1.0, clip=True),
            CropForegroundd(keys=["image", "label"], source_key="image"),
            RandCropByPosNegLabeld(
                keys=["image", "label"],
                label_key="label",
                spatial_size=(96, 96, 96),
                pos=1,
                neg=1,
                num_samples=4,
            ),
            RandRotate90d(keys=["image", "label"], prob=0.5, spatial_axes=(0, 2)),
            RandFlipd(keys=["image", "label"], prob=0.5, spatial_axis=0),
            RandFlipd(keys=["image", "label"], prob=0.5, spatial_axis=1),
            RandFlipd(keys=["image", "label"], prob=0.5, spatial_axis=2),
            EnsureTyped(keys=["image", "label"]),
        ])

    def get_val_transforms(self):
        """Validation transforms (no augmentation)"""
        return Compose([
            LoadImaged(keys=["image", "label"]),
            EnsureChannelFirstd(keys=["image", "label"]),
            Spacingd(keys=["image", "label"], pixdim=(1.5, 1.5, 2.0), mode=("bilinear", "nearest")),
            Orientationd(keys=["image", "label"], axcodes="RAS"),
            ScaleIntensityRanged(keys=["image"], a_min=-57, a_max=164, b_min=0.0, b_max=1.0, clip=True),
            CropForegroundd(keys=["image", "label"], source_key="image"),
            EnsureTyped(keys=["image", "label"]),
        ])

if __name__ == "__main__":
    prep = CustomDataPreparation(data_root="/mnt/data/custom_dataset")
    splits = prep.create_data_dicts()
    print("✅ Data preparation complete!")
```

---

### **Bước 3: Fine-tuning Script**

#### 3.1 Training configuration

```python
# File: monai-demo/training/finetune_config.py

from dataclasses import dataclass
from typing import Optional

@dataclass
class FinetuneConfig:
    """Configuration for fine-tuning external model"""

    # Model
    model_name: str = "external_model"
    spatial_dims: int = 3
    in_channels: int = 1
    out_channels: int = 2  # background + spleen
    features: tuple = (32, 64, 128, 256, 512)

    # External weights
    pretrained_weights_path: Optional[str] = None
    freeze_encoder: bool = False

    # Training
    max_epochs: int = 100
    batch_size: int = 2
    learning_rate: float = 1e-4
    weight_decay: float = 1e-5

    # Data
    data_root: str = "/mnt/data/custom_dataset"
    cache_dir: str = "/mnt/data/cache"
    num_workers: int = 4

    # Validation
    val_interval: int = 5
    save_interval: int = 10

    # Output
    output_dir: str = "/mnt/data/models/finetuned"
    experiment_name: str = "external_model_finetune"

    # MLflow tracking
    mlflow_tracking_uri: str = "http://localhost:5000"
    mlflow_experiment_name: str = "spleen_segmentation_finetuning"
```

#### 3.2 Main training script

```python
# File: monai-demo/training/train_external_model.py

import torch
import mlflow
from pathlib import Path
from torch.optim import Adam
from torch.optim.lr_scheduler import CosineAnnealingLR
from monai.data import DataLoader, Dataset, CacheDataset
from monai.losses import DiceCELoss
from monai.metrics import DiceMetric
from monai.inferers import sliding_window_inference
from monai.utils import set_determinism

import sys
sys.path.append(str(Path(__file__).parent.parent))
from models.external_model_wrapper import ExternalModelWrapper
from scripts.prepare_custom_data import CustomDataPreparation
from training.finetune_config import FinetuneConfig

class ExternalModelTrainer:
    """Trainer for fine-tuning external model with MONAI"""

    def __init__(self, config: FinetuneConfig):
        self.config = config
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

        # Setup reproducibility
        set_determinism(seed=42)

        # Setup output directory
        self.output_dir = Path(config.output_dir) / config.experiment_name
        self.output_dir.mkdir(exist_ok=True, parents=True)

        # Initialize MLflow
        mlflow.set_tracking_uri(config.mlflow_tracking_uri)
        mlflow.set_experiment(config.mlflow_experiment_name)

    def setup_data(self):
        """Setup data loaders"""
        print("📊 Setting up data loaders...")

        data_prep = CustomDataPreparation(
            data_root=self.config.data_root,
            cache_dir=self.config.cache_dir
        )

        # Load or create data splits
        splits = data_prep.create_data_dicts()

        # Create datasets with caching
        train_ds = CacheDataset(
            data=splits['train'],
            transform=data_prep.get_train_transforms(),
            cache_rate=1.0,
            num_workers=self.config.num_workers
        )

        val_ds = CacheDataset(
            data=splits['val'],
            transform=data_prep.get_val_transforms(),
            cache_rate=1.0,
            num_workers=self.config.num_workers
        )

        # Create data loaders
        self.train_loader = DataLoader(
            train_ds,
            batch_size=self.config.batch_size,
            shuffle=True,
            num_workers=0,  # Already cached
            pin_memory=True
        )

        self.val_loader = DataLoader(
            val_ds,
            batch_size=1,
            shuffle=False,
            num_workers=0,
            pin_memory=True
        )

        print(f"✅ Train: {len(train_ds)} samples, Val: {len(val_ds)} samples")

    def setup_model(self):
        """Setup model, loss, optimizer"""
        print("🔧 Setting up model and training components...")

        # Model
        self.model = ExternalModelWrapper(
            spatial_dims=self.config.spatial_dims,
            in_channels=self.config.in_channels,
            out_channels=self.config.out_channels,
            features=self.config.features,
            external_weights_path=self.config.pretrained_weights_path,
            freeze_encoder=self.config.freeze_encoder
        ).to(self.device)

        # Loss function
        self.loss_function = DiceCELoss(
            to_onehot_y=True,
            softmax=True,
            squared_pred=True,
            smooth_nr=1e-5,
            smooth_dr=1e-5,
        )

        # Optimizer
        self.optimizer = Adam(
            self.model.parameters(),
            lr=self.config.learning_rate,
            weight_decay=self.config.weight_decay
        )

        # Scheduler
        self.scheduler = CosineAnnealingLR(
            self.optimizer,
            T_max=self.config.max_epochs,
            eta_min=1e-6
        )

        # Metric
        self.dice_metric = DiceMetric(
            include_background=False,
            reduction="mean",
            get_not_nans=False
        )

        print(f"✅ Model parameters: {sum(p.numel() for p in self.model.parameters()):,}")

    def train_epoch(self, epoch: int):
        """Train one epoch"""
        self.model.train()
        epoch_loss = 0

        for batch_idx, batch in enumerate(self.train_loader):
            inputs = batch["image"].to(self.device)
            labels = batch["label"].to(self.device)

            # Forward
            self.optimizer.zero_grad()
            outputs = self.model(inputs)
            loss = self.loss_function(outputs, labels)

            # Backward
            loss.backward()
            self.optimizer.step()

            epoch_loss += loss.item()

            if (batch_idx + 1) % 10 == 0:
                print(f"  Batch [{batch_idx + 1}/{len(self.train_loader)}] Loss: {loss.item():.4f}")

        avg_loss = epoch_loss / len(self.train_loader)
        return avg_loss

    def validate(self, epoch: int):
        """Validation"""
        self.model.eval()
        val_loss = 0

        with torch.no_grad():
            for batch in self.val_loader:
                inputs = batch["image"].to(self.device)
                labels = batch["label"].to(self.device)

                # Sliding window inference
                outputs = sliding_window_inference(
                    inputs=inputs,
                    roi_size=(96, 96, 96),
                    sw_batch_size=4,
                    predictor=self.model,
                    overlap=0.5
                )

                # Calculate loss
                loss = self.loss_function(outputs, labels)
                val_loss += loss.item()

                # Calculate Dice
                outputs = torch.argmax(outputs, dim=1, keepdim=True)
                self.dice_metric(y_pred=outputs, y=labels)

        avg_val_loss = val_loss / len(self.val_loader)
        dice_score = self.dice_metric.aggregate().item()
        self.dice_metric.reset()

        return avg_val_loss, dice_score

    def train(self):
        """Main training loop"""
        print("🚀 Starting training...")

        with mlflow.start_run(run_name=self.config.experiment_name):
            # Log config
            mlflow.log_params({
                "max_epochs": self.config.max_epochs,
                "batch_size": self.config.batch_size,
                "learning_rate": self.config.learning_rate,
                "model": self.config.model_name,
                "freeze_encoder": self.config.freeze_encoder
            })

            best_dice = 0.0

            for epoch in range(1, self.config.max_epochs + 1):
                print(f"\n📅 Epoch {epoch}/{self.config.max_epochs}")

                # Train
                train_loss = self.train_epoch(epoch)
                print(f"  Train Loss: {train_loss:.4f}")
                mlflow.log_metric("train_loss", train_loss, step=epoch)

                # Validate
                if epoch % self.config.val_interval == 0:
                    val_loss, dice_score = self.validate(epoch)
                    print(f"  Val Loss: {val_loss:.4f}, Dice: {dice_score:.4f}")

                    mlflow.log_metric("val_loss", val_loss, step=epoch)
                    mlflow.log_metric("dice_score", dice_score, step=epoch)

                    # Save best model
                    if dice_score > best_dice:
                        best_dice = dice_score
                        best_model_path = self.output_dir / "best_model.pth"
                        torch.save({
                            'epoch': epoch,
                            'model_state_dict': self.model.state_dict(),
                            'optimizer_state_dict': self.optimizer.state_dict(),
                            'dice_score': dice_score,
                        }, best_model_path)
                        print(f"  ✅ Best model saved! Dice: {dice_score:.4f}")
                        mlflow.log_artifact(str(best_model_path))

                # Learning rate step
                self.scheduler.step()
                mlflow.log_metric("learning_rate", self.scheduler.get_last_lr()[0], step=epoch)

                # Save checkpoint
                if epoch % self.config.save_interval == 0:
                    checkpoint_path = self.output_dir / f"checkpoint_epoch_{epoch}.pth"
                    torch.save({
                        'epoch': epoch,
                        'model_state_dict': self.model.state_dict(),
                        'optimizer_state_dict': self.optimizer.state_dict(),
                    }, checkpoint_path)

            print(f"\n✅ Training complete! Best Dice: {best_dice:.4f}")
            mlflow.log_metric("best_dice", best_dice)

if __name__ == "__main__":
    config = FinetuneConfig()
    trainer = ExternalModelTrainer(config)
    trainer.setup_data()
    trainer.setup_model()
    trainer.train()
```

---

### **Bước 4: Evaluation Framework**

```python
# File: monai-demo/evaluation/evaluate_model.py

import torch
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
from monai.inferers import sliding_window_inference
from monai.metrics import DiceMetric, HausdorffDistanceMetric
from monai.data import DataLoader, Dataset
import json

class ModelEvaluator:
    """Comprehensive evaluation for trained models"""

    def __init__(self, model_path: str, test_data: list, output_dir: str):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model = self._load_model(model_path)
        self.test_data = test_data
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True, parents=True)

        # Metrics
        self.dice_metric = DiceMetric(include_background=False, reduction="mean_batch")
        self.hd_metric = HausdorffDistanceMetric(include_background=False, percentile=95)

    def _load_model(self, model_path: str):
        """Load trained model"""
        from models.external_model_wrapper import ExternalModelWrapper

        model = ExternalModelWrapper(
            spatial_dims=3,
            in_channels=1,
            out_channels=2
        ).to(self.device)

        checkpoint = torch.load(model_path, map_location=self.device)
        model.load_state_dict(checkpoint['model_state_dict'])
        model.eval()

        print(f"✅ Model loaded from: {model_path}")
        return model

    def evaluate(self):
        """Run comprehensive evaluation"""
        results = {
            'per_sample': [],
            'aggregated': {}
        }

        with torch.no_grad():
            for idx, data in enumerate(self.test_data):
                print(f"\n📊 Evaluating sample {idx + 1}/{len(self.test_data)}")

                inputs = data["image"].unsqueeze(0).to(self.device)
                labels = data["label"].unsqueeze(0).to(self.device)

                # Inference
                outputs = sliding_window_inference(
                    inputs=inputs,
                    roi_size=(96, 96, 96),
                    sw_batch_size=4,
                    predictor=self.model,
                    overlap=0.5
                )

                predictions = torch.argmax(outputs, dim=1, keepdim=True)

                # Calculate metrics
                dice = self.dice_metric(y_pred=predictions, y=labels).item()
                hd95 = self.hd_metric(y_pred=predictions, y=labels).item()

                sample_result = {
                    'sample_id': idx,
                    'dice_score': float(dice),
                    'hausdorff_95': float(hd95)
                }
                results['per_sample'].append(sample_result)

                print(f"  Dice: {dice:.4f}, HD95: {hd95:.2f}mm")

        # Aggregate results
        dice_scores = [r['dice_score'] for r in results['per_sample']]
        hd_scores = [r['hausdorff_95'] for r in results['per_sample']]

        results['aggregated'] = {
            'mean_dice': float(np.mean(dice_scores)),
            'std_dice': float(np.std(dice_scores)),
            'median_dice': float(np.median(dice_scores)),
            'mean_hd95': float(np.mean(hd_scores)),
            'std_hd95': float(np.std(hd_scores))
        }

        # Save results
        results_file = self.output_dir / 'evaluation_results.json'
        with open(results_file, 'w') as f:
            json.dump(results, f, indent=2)

        print(f"\n✅ Evaluation complete!")
        print(f"📊 Mean Dice: {results['aggregated']['mean_dice']:.4f} ± {results['aggregated']['std_dice']:.4f}")
        print(f"📊 Mean HD95: {results['aggregated']['mean_hd95']:.2f} ± {results['aggregated']['std_hd95']:.2f} mm")

        return results
```

---

### **Bước 5: Update Kubeflow Pipeline**

#### 5.1 Tạo Docker image mới với fine-tuned model

```dockerfile
# File: monai-demo/Dockerfile.finetuned

FROM pytorch/pytorch:2.1.0-cuda11.8-cudnn8-runtime

# Install dependencies
RUN pip install --no-cache-dir \
    monai[all]==1.3.0 \
    nibabel \
    matplotlib \
    mlflow

# Copy model and code
WORKDIR /app
COPY models/ /app/models/
COPY components/ /app/components/
COPY training/finetuned_models/best_model.pth /app/models/best_model.pth

# Set environment
ENV PYTHONUNBUFFERED=1
ENV MODEL_PATH=/app/models/best_model.pth

CMD ["python", "/app/components/inference.py"]
```

#### 5.2 Update inference component

```python
# File: monai-demo/components/inference_finetuned.py

import torch
import sys
from pathlib import Path

# Add models to path
sys.path.append('/app')
from models.external_model_wrapper import ExternalModelWrapper

def load_finetuned_model(model_path: str = "/app/models/best_model.pth"):
    """Load fine-tuned external model"""
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    model = ExternalModelWrapper(
        spatial_dims=3,
        in_channels=1,
        out_channels=2
    ).to(device)

    checkpoint = torch.load(model_path, map_location=device)
    model.load_state_dict(checkpoint['model_state_dict'])
    model.eval()

    print(f"✅ Fine-tuned model loaded from: {model_path}")
    print(f"   Epoch: {checkpoint.get('epoch', 'N/A')}")
    print(f"   Dice Score: {checkpoint.get('dice_score', 'N/A'):.4f}")

    return model

# Update inference logic to use fine-tuned model
# ... (rest of inference code)
```

#### 5.3 Update Kubeflow pipeline YAML

```yaml
# Changes to spleen_pipeline_v2.yaml

# Update image version
- name: inference
  inputs:
    parameters:
      - name: patient-id
  container:
    image: spleen-pipeline-finetuned:v1  # ← New image with fine-tuned model
    imagePullPolicy: Never
    command: [python, /app/components/inference_finetuned.py]
    args: ["{{inputs.parameters.patient-id}}"]
    volumeMounts:
      - name: data-volume
        mountPath: /mnt/data
```

---

## 🔄 Quy trình Deployment

### 1. Build và Test Locally

```bash
# Build new Docker image
cd monai-demo
docker build -f Dockerfile.finetuned -t spleen-pipeline-finetuned:v1 .

# Load into Minikube
minikube image load spleen-pipeline-finetuned:v1

# Test inference locally
docker run --rm -v $(pwd)/test_data:/mnt/data \
  spleen-pipeline-finetuned:v1 \
  python /app/components/inference_finetuned.py spleen_9
```

### 2. Update Pipeline

```bash
# Apply updated pipeline
kubectl apply -f kubeflow_pipeline/spleen_pipeline_v2.yaml -n kubeflow

# Monitor deployment
kubectl get workflows -n kubeflow --watch

# Check logs
kubectl logs -n kubeflow <workflow-pod-name>
```

### 3. A/B Testing (Optional)

```yaml
# Create separate pipeline versions for comparison
apiVersion: argoproj.io/v1alpha1
kind: Workflow
metadata:
  generateName: model-comparison-
spec:
  templates:
    - name: compare-models
      dag:
        tasks:
          - name: baseline-inference
            template: inference-baseline
          - name: finetuned-inference
            template: inference-finetuned
          - name: compare-results
            template: comparison
            dependencies: [baseline-inference, finetuned-inference]
```

---

## 📊 Monitoring và Validation

### Metrics to track:

1. **Performance Metrics**
   - Dice Score
   - Hausdorff Distance
   - Inference time
   - GPU memory usage

2. **MLflow Tracking**
   - Training curves
   - Validation metrics
   - Model artifacts
   - Hyperparameters

3. **Production Metrics**
   - Pipeline success rate
   - Average processing time per patient
   - Resource utilization

---

## ✅ Checklist

- [ ] **Bước 1**: Chọn external model architecture
- [ ] **Bước 2**: Implement model wrapper
- [ ] **Bước 3**: Chuẩn bị custom dataset
- [ ] **Bước 4**: Configure training parameters
- [ ] **Bước 5**: Run fine-tuning với MLflow tracking
- [ ] **Bước 6**: Evaluate model trên test set
- [ ] **Bước 7**: Build Docker image với fine-tuned model
- [ ] **Bước 8**: Update Kubeflow pipeline
- [ ] **Bước 9**: Deploy và test trên Kubeflow
- [ ] **Bước 10**: Monitor production performance

---

## 🔗 Resources

- **MONAI Documentation**: https://docs.monai.io/
- **nnU-Net GitHub**: https://github.com/MIC-DKFZ/nnUNet
- **Kubeflow Pipelines**: https://www.kubeflow.org/docs/components/pipelines/
- **MLflow**: https://mlflow.org/docs/latest/index.html

---

## 📝 Notes

- **GPU Requirements**: Fine-tuning yêu cầu GPU với ít nhất 8GB VRAM
- **Training Time**: Ước tính 2-4 giờ cho 100 epochs (tùy dataset size)
- **Model Size**: Fine-tuned model khoảng 100-200MB
- **Backup**: Luôn backup pretrained weights trước khi fine-tune

---

**Created**: 2025-10-31
**Last Updated**: 2025-10-31
**Author**: MONAI-Kubeflow Integration Team
