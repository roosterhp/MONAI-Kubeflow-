# Kubeflow Pipeline Design: Medical Image Classification

## 1. Pipeline Overview

### 1.1 Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                    Kubeflow Pipeline DAG                         │
└──────────────────────────────────────────────────────────────────┘

    ┌─────────────┐
    │ Preprocess  │  Inputs: raw_data_path, output_path
    └──────┬──────┘  Outputs: processed_data_path, dataset_stats
           │
           ▼
    ┌─────────────┐
    │    Train    │  Inputs: processed_data_path, config, model_name
    └──────┬──────┘  Outputs: model_checkpoint, training_metrics
           │
           ├──────────────────┐
           ▼                  ▼
    ┌─────────────┐    ┌─────────────┐
    │  Evaluate   │    │  Register   │
    └──────┬──────┘    └──────┬──────┘
           │                  │
           ├──────────────────┘
           ▼
    ┌─────────────┐
    │   Deploy    │  Outputs: inference_endpoint
    └─────────────┘
```

### 1.2 Component Specifications

| Component | CPU | Memory | GPU | Storage | Duration |
|-----------|-----|--------|-----|---------|----------|
| Preprocess | 2 cores | 8Gi | 0 | 50Gi | 10-30min |
| Train | 4 cores | 16Gi | 1x V100 | 100Gi | 2-4hrs |
| Evaluate | 2 cores | 8Gi | 1x V100 | 20Gi | 15-30min |
| Register | 1 core | 4Gi | 0 | 10Gi | 5min |
| Deploy | 1 core | 2Gi | 0 | 5Gi | 5-10min |

---

## 2. Component 1: Preprocess

### 2.1 Responsibilities
- Load raw medical images (DICOM/PNG/JPG)
- Validate data integrity
- Apply MONAI transforms
- Split train/val/test sets
- Generate dataset statistics
- Cache preprocessed data

### 2.2 Input/Output Schema

**Inputs**:
```yaml
raw_data_path:
  type: String
  description: "Path to raw data directory (PVC mount)"
  example: "/mnt/data/raw/xray_chest"

output_path:
  type: String
  description: "Path to output preprocessed data"
  example: "/mnt/data/processed/xray_chest_v1"

config:
  type: Dict
  description: "Preprocessing configuration"
  schema:
    image_size: [224, 224]
    normalize: true
    augmentation: true
    cache_rate: 1.0
```

**Outputs**:
```yaml
processed_data_path:
  type: String
  description: "Path to preprocessed dataset"

dataset_stats:
  type: Dict
  description: "Dataset statistics"
  schema:
    num_train: 4000
    num_val: 800
    num_test: 200
    num_classes: 5
    class_distribution: {0: 1000, 1: 800, ...}
    mean: [0.485, 0.456, 0.406]
    std: [0.229, 0.224, 0.225]
```

### 2.3 File Structure

```
components/preprocess/
├── Dockerfile
│   # Base: python:3.9-slim
│   # Install: monai[all], nibabel, pydicom
│
├── preprocess.py
│   # Main preprocessing logic
│   class DataPreprocessor:
│       def load_raw_data()
│       def validate_images()
│       def apply_transforms()
│       def split_dataset()
│       def compute_statistics()
│       def save_processed_data()
│
├── transforms.py
│   # MONAI transform definitions
│   def get_train_transforms()
│   def get_val_transforms()
│   def get_test_transforms()
│
└── component.yaml
    # Kubeflow component specification
```

### 2.4 Key Operations

```python
# Pseudo-code structure

# 1. Load and validate
images = load_medical_images(raw_data_path)
validate_dicom_headers(images)
validate_image_sizes(images)

# 2. Define transforms
train_transforms = Compose([
    LoadImage(),
    EnsureChannelFirst(),
    Resize((224, 224)),
    ScaleIntensity(minv=0, maxv=1),
    Normalize(mean=IMAGENET_MEAN, std=IMAGENET_STD),
    # Augmentation
    RandRotate(prob=0.5, range_x=(-15, 15)),
    RandFlip(prob=0.5, spatial_axis=1),
    RandZoom(prob=0.3, min_zoom=0.9, max_zoom=1.1),
])

# 3. Create datasets
train_dataset = CacheDataset(
    data=train_files,
    transform=train_transforms,
    cache_rate=1.0,
)

# 4. Compute statistics
dataset_stats = {
    "num_samples": len(train_dataset),
    "class_distribution": compute_class_dist(train_dataset),
    "mean": compute_mean(train_dataset),
    "std": compute_std(train_dataset),
}

# 5. Save
save_dataset(train_dataset, output_path / "train")
save_metadata(dataset_stats, output_path / "metadata.json")
```

### 2.5 Component YAML

```yaml
name: preprocess-medical-images
description: Preprocess medical images using MONAI

inputs:
  - {name: raw_data_path, type: String}
  - {name: output_path, type: String}
  - {name: config, type: JsonObject}

outputs:
  - {name: processed_data_path, type: String}
  - {name: dataset_stats, type: JsonObject}

implementation:
  container:
    image: efficientnet-preprocess:v1
    command:
      - python
      - /app/preprocess.py
      - --raw-data-path
      - {inputValue: raw_data_path}
      - --output-path
      - {inputValue: output_path}
      - --config
      - {inputValue: config}
    resources:
      requests:
        cpu: "2"
        memory: "8Gi"
      limits:
        cpu: "4"
        memory: "16Gi"
```

### 2.6 Definition of Done

- [ ] All images loaded successfully (0 errors)
- [ ] DICOM metadata validated
- [ ] Train/val/test split created (stratified)
- [ ] Dataset statistics computed and saved
- [ ] Preprocessed data cached on PVC
- [ ] Transforms validated with sample images
- [ ] Component runs successfully in Kubeflow

---

## 3. Component 2: Train

### 3.1 Responsibilities
- Load timm EfficientNetV2-S model
- Integrate with MONAI training engine
- Two-stage fine-tuning (freeze → full)
- Model checkpointing
- MLflow logging
- Early stopping

### 3.2 Input/Output Schema

**Inputs**:
```yaml
processed_data_path:
  type: String
  description: "Path to preprocessed dataset"

config:
  type: Dict
  schema:
    model_name: "efficientnetv2_rw_s"
    num_classes: 5
    pretrained: true
    max_epochs: 30
    batch_size: 32
    learning_rate: 1e-4
    optimizer: "AdamW"
    scheduler: "CosineAnnealingLR"

output_model_path:
  type: String
  description: "Path to save model checkpoints"
```

**Outputs**:
```yaml
model_checkpoint_path:
  type: String
  description: "Path to best model checkpoint"

training_metrics:
  type: Dict
  schema:
    best_val_loss: 0.234
    best_val_acc: 0.901
    total_epochs: 28
    early_stopped: true
    training_time_hours: 3.2
```

### 3.3 File Structure

```
components/train/
├── Dockerfile
│   # Base: pytorch/pytorch:2.1.0-cuda11.8-cudnn8-runtime
│   # Install: monai[all], timm, mlflow
│
├── train.py
│   # Main training script
│   def main():
│       - Load config
│       - Setup data loaders
│       - Initialize model
│       - Two-stage training
│       - Save checkpoints
│
├── model_wrapper.py
│   class EfficientNetV2Wrapper(nn.Module):
│       def __init__(model_name, num_classes, pretrained):
│           self.backbone = timm.create_model(...)
│       def forward(x):
│           return self.backbone(x)
│
├── trainer.py
│   class TwoStageTrainer:
│       def stage1_freeze_backbone()
│       def stage2_full_finetune()
│       def stage3_refinement()
│
└── component.yaml
```

### 3.4 Model Wrapper Implementation

```python
# Pseudo-code structure

class EfficientNetV2Wrapper(nn.Module):
    """
    Wraps timm EfficientNetV2 for MONAI compatibility
    """

    def __init__(
        self,
        model_name: str = "efficientnetv2_rw_s",
        num_classes: int = 5,
        pretrained: bool = True,
    ):
        super().__init__()

        # Load timm model
        self.model = timm.create_model(
            model_name,
            pretrained=pretrained,
            num_classes=num_classes,
        )

        # Store metadata
        self.num_classes = num_classes
        self.model_name = model_name

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Args:
            x: [batch, 3, 224, 224]
        Returns:
            logits: [batch, num_classes]
        """
        return self.model(x)

    def freeze_backbone(self):
        """Freeze all layers except classifier"""
        for name, param in self.model.named_parameters():
            if "classifier" not in name:
                param.requires_grad = False

    def unfreeze_all(self):
        """Unfreeze all parameters"""
        for param in self.model.parameters():
            param.requires_grad = True
```

### 3.5 Training Strategy

#### Stage 1: Head-Only (5 epochs)
```python
# Freeze backbone
model.freeze_backbone()

# High learning rate for head
optimizer = AdamW([
    {'params': model.model.classifier.parameters(), 'lr': 1e-3}
])

# Train 5 epochs
trainer = SupervisedTrainer(
    max_epochs=5,
    network=model,
    optimizer=optimizer,
    loss_function=CrossEntropyLoss(label_smoothing=0.1),
)
```

#### Stage 2: Full Fine-tune (20 epochs)
```python
# Unfreeze all
model.unfreeze_all()

# Lower learning rate for backbone, higher for head
optimizer = AdamW([
    {'params': model.model.features.parameters(), 'lr': 1e-4},
    {'params': model.model.classifier.parameters(), 'lr': 1e-3},
], weight_decay=0.01)

scheduler = CosineAnnealingLR(optimizer, T_max=20)

# Train 20 epochs
trainer = SupervisedTrainer(
    max_epochs=20,
    network=model,
    optimizer=optimizer,
    lr_scheduler=scheduler,
)
```

#### Stage 3: Refinement (5 epochs)
```python
# Very low learning rate
optimizer = AdamW(model.parameters(), lr=1e-5)

# Train 5 epochs
trainer = SupervisedTrainer(max_epochs=5, ...)
```

### 3.6 MLflow Integration

```python
# Pseudo-code structure

import mlflow

mlflow.set_experiment("medical-image-classification")

with mlflow.start_run(run_name="efficientnetv2-xray-v1"):
    # Log parameters
    mlflow.log_params({
        "model": "efficientnetv2_rw_s",
        "num_classes": 5,
        "max_epochs": 30,
        "batch_size": 32,
        "optimizer": "AdamW",
    })

    # Training loop
    for epoch in range(max_epochs):
        train_loss = train_epoch()
        val_loss, val_acc = validate_epoch()

        # Log metrics
        mlflow.log_metrics({
            "train_loss": train_loss,
            "val_loss": val_loss,
            "val_acc": val_acc,
        }, step=epoch)

        # Save checkpoint
        if val_acc > best_acc:
            torch.save(model.state_dict(), "best_model.pth")
            mlflow.log_artifact("best_model.pth")

    # Log final model
    mlflow.pytorch.log_model(model, "model")
```

### 3.7 Component YAML

```yaml
name: train-efficientnet
description: Train EfficientNetV2-S with two-stage fine-tuning

inputs:
  - {name: processed_data_path, type: String}
  - {name: config, type: JsonObject}
  - {name: output_model_path, type: String}

outputs:
  - {name: model_checkpoint_path, type: String}
  - {name: training_metrics, type: JsonObject}

implementation:
  container:
    image: efficientnet-train:v1
    command:
      - python
      - /app/train.py
      - --data-path
      - {inputValue: processed_data_path}
      - --config
      - {inputValue: config}
      - --output-path
      - {inputValue: output_model_path}
    resources:
      requests:
        cpu: "4"
        memory: "16Gi"
        nvidia.com/gpu: "1"
      limits:
        cpu: "8"
        memory: "32Gi"
        nvidia.com/gpu: "1"
```

### 3.8 Definition of Done

- [ ] Model loads successfully with pretrained weights
- [ ] Two-stage training completes without errors
- [ ] Best model checkpoint saved
- [ ] Training metrics logged to MLflow
- [ ] Validation accuracy > 85%
- [ ] No overfitting (train/val gap < 5%)
- [ ] Component runs successfully on GPU node

---

## 4. Component 3: Evaluate

### 4.1 Responsibilities
- Load test dataset
- Run inference on test set
- Compute medical metrics (AUC, F1, Accuracy, ECE)
- Generate confusion matrix
- Validate model calibration
- Create evaluation report

### 4.2 Input/Output Schema

**Inputs**:
```yaml
model_checkpoint_path:
  type: String
  description: "Path to trained model"

test_data_path:
  type: String
  description: "Path to test dataset"

output_metrics_path:
  type: String
  description: "Path to save metrics"
```

**Outputs**:
```yaml
metrics:
  type: Dict
  schema:
    auc_roc: 0.942
    f1_score: 0.889
    accuracy: 0.901
    sensitivity: 0.912
    specificity: 0.885
    ece: 0.082
    confusion_matrix: [[100, 5], [8, 87]]
    per_class_metrics:
      Normal: {precision: 0.95, recall: 0.90, f1: 0.92}
      Pneumonia: {precision: 0.88, recall: 0.92, f1: 0.90}

report_path:
  type: String
  description: "Path to evaluation report (PDF)"
```

### 4.3 File Structure

```
components/evaluate/
├── Dockerfile
│
├── evaluate.py
│   # Main evaluation script
│   def evaluate_model():
│       - Load model
│       - Run inference
│       - Compute metrics
│       - Generate report
│
├── medical_metrics.py
│   # Medical-specific metrics
│   def compute_auc(y_true, y_pred_proba)
│   def compute_ece(y_true, y_pred_proba)
│   def compute_sensitivity_specificity()
│   def calibration_curve()
│
├── visualization.py
│   # Generate plots
│   def plot_confusion_matrix()
│   def plot_roc_curve()
│   def plot_calibration_curve()
│
└── component.yaml
```

### 4.4 Metrics Implementation

#### Expected Calibration Error (ECE)
```python
# Pseudo-code structure

def compute_ece(y_true, y_pred_proba, n_bins=10):
    """
    Compute Expected Calibration Error
    Measures how well predicted probabilities match actual outcomes
    """
    # Create bins
    bins = np.linspace(0, 1, n_bins + 1)

    ece = 0.0
    for i in range(n_bins):
        # Find predictions in this confidence bin
        in_bin = (y_pred_proba >= bins[i]) & (y_pred_proba < bins[i+1])

        if in_bin.sum() > 0:
            # Accuracy in this bin
            bin_acc = y_true[in_bin].mean()

            # Average confidence in this bin
            bin_conf = y_pred_proba[in_bin].mean()

            # Weighted difference
            ece += np.abs(bin_acc - bin_conf) * in_bin.sum()

    return ece / len(y_true)
```

#### Comprehensive Metrics
```python
# Pseudo-code structure

from sklearn.metrics import (
    roc_auc_score, f1_score, accuracy_score,
    confusion_matrix, classification_report
)

metrics = {
    # Binary/Multi-class classification
    "auc_roc": roc_auc_score(y_true, y_pred_proba, multi_class='ovr'),
    "f1_score": f1_score(y_true, y_pred, average='weighted'),
    "accuracy": accuracy_score(y_true, y_pred),

    # Medical-specific
    "sensitivity": recall_score(y_true, y_pred, average='weighted'),
    "specificity": compute_specificity(y_true, y_pred),

    # Calibration
    "ece": compute_ece(y_true, y_pred_proba),

    # Detailed
    "confusion_matrix": confusion_matrix(y_true, y_pred).tolist(),
    "classification_report": classification_report(y_true, y_pred, output_dict=True),

    # Per-class
    "per_class_metrics": {
        class_name: {
            "precision": precision_score(y_true_class, y_pred_class),
            "recall": recall_score(y_true_class, y_pred_class),
            "f1": f1_score(y_true_class, y_pred_class),
            "support": int(y_true_class.sum()),
        }
        for class_name in class_names
    }
}
```

### 4.5 Validation Thresholds

```python
# Minimum thresholds for production deployment

THRESHOLDS = {
    "auc_roc": 0.90,        # Must be > 0.90
    "f1_score": 0.85,       # Must be > 0.85
    "accuracy": 0.85,       # Must be > 0.85
    "ece": 0.10,            # Must be < 0.10 (well-calibrated)
    "sensitivity": 0.85,    # Critical for medical diagnosis
}

def validate_metrics(metrics):
    """Check if metrics meet thresholds"""
    passed = True

    for metric, threshold in THRESHOLDS.items():
        value = metrics[metric]

        if metric == "ece":
            # Lower is better for ECE
            if value > threshold:
                print(f"❌ {metric}: {value:.3f} > {threshold}")
                passed = False
        else:
            # Higher is better
            if value < threshold:
                print(f"❌ {metric}: {value:.3f} < {threshold}")
                passed = False

    return passed
```

### 4.6 Component YAML

```yaml
name: evaluate-model
description: Evaluate model with medical metrics

inputs:
  - {name: model_checkpoint_path, type: String}
  - {name: test_data_path, type: String}
  - {name: output_metrics_path, type: String}

outputs:
  - {name: metrics, type: JsonObject}
  - {name: report_path, type: String}
  - {name: passed_validation, type: Boolean}

implementation:
  container:
    image: efficientnet-evaluate:v1
    command:
      - python
      - /app/evaluate.py
      - --model-path
      - {inputValue: model_checkpoint_path}
      - --test-data-path
      - {inputValue: test_data_path}
      - --output-path
      - {inputValue: output_metrics_path}
    resources:
      requests:
        cpu: "2"
        memory: "8Gi"
        nvidia.com/gpu: "1"
      limits:
        cpu: "4"
        memory: "16Gi"
        nvidia.com/gpu: "1"
```

### 4.7 Definition of Done

- [ ] All metrics computed successfully
- [ ] AUC > 0.90, F1 > 0.85, Accuracy > 0.85
- [ ] ECE < 0.10 (well-calibrated)
- [ ] Confusion matrix generated
- [ ] Per-class metrics reported
- [ ] Evaluation report PDF created
- [ ] Metrics saved to JSON
- [ ] Validation thresholds passed

---

## 5. Component 4: Register

### 5.1 Responsibilities
- Register model in MLflow Model Registry
- Store model metadata
- Version model artifacts
- Tag model for deployment

### 5.2 Implementation

```python
# Pseudo-code structure

import mlflow

def register_model(
    model_path: str,
    model_name: str,
    metrics: dict,
    metadata: dict
):
    """Register model in MLflow"""

    # Load model
    model_uri = f"file://{model_path}"

    # Register
    registered_model = mlflow.register_model(
        model_uri=model_uri,
        name=model_name
    )

    # Add metadata
    client = mlflow.tracking.MlflowClient()
    client.set_model_version_tag(
        name=model_name,
        version=registered_model.version,
        key="metrics",
        value=json.dumps(metrics)
    )

    # Tag for production if validated
    if metrics["auc_roc"] > 0.90:
        client.set_model_version_tag(
            name=model_name,
            version=registered_model.version,
            key="stage",
            value="Production"
        )

    return registered_model.version
```

### 5.3 Definition of Done

- [ ] Model registered in MLflow
- [ ] Version number assigned
- [ ] Metadata attached (metrics, config)
- [ ] Production tag added if validated
- [ ] Model artifacts accessible

---

## 6. Component 5: Deploy

### 6.1 Responsibilities
- Export model to TorchScript/ONNX
- Build Triton model repository
- Create InferenceService manifest
- Deploy to KServe
- Validate endpoint

### 6.2 Implementation Overview

See `DEPLOYMENT.md` for full details.

### 6.3 Definition of Done

- [ ] Model exported to ONNX
- [ ] Triton model repository created
- [ ] InferenceService deployed
- [ ] Health check passed
- [ ] Test inference successful
- [ ] Latency < 100ms (p95)

---

## 7. Pipeline Orchestration

### 7.1 Complete Pipeline YAML

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Workflow
metadata:
  generateName: efficientnet-classification-
  namespace: kubeflow
spec:
  entrypoint: main
  serviceAccountName: pipeline-runner

  volumes:
    - name: data-volume
      persistentVolumeClaim:
        claimName: data-pvc

  templates:
    - name: main
      dag:
        tasks:
          - name: preprocess
            template: preprocess-component
            arguments:
              parameters:
                - name: raw-data-path
                  value: "/mnt/data/raw/xray_chest"
                - name: output-path
                  value: "/mnt/data/processed/xray_v1"

          - name: train
            template: train-component
            dependencies: [preprocess]
            arguments:
              parameters:
                - name: data-path
                  value: "{{tasks.preprocess.outputs.parameters.processed-data-path}}"

          - name: evaluate
            template: evaluate-component
            dependencies: [train]
            arguments:
              parameters:
                - name: model-path
                  value: "{{tasks.train.outputs.parameters.model-checkpoint-path}}"

          - name: register
            template: register-component
            dependencies: [evaluate]
            when: "{{tasks.evaluate.outputs.parameters.passed-validation}} == true"

          - name: deploy
            template: deploy-component
            dependencies: [register]

    # Component templates defined here...
```

### 7.2 Execution Flow

```
1. Submit pipeline → Argo Workflow created
2. Preprocess starts → Creates PVC artifacts
3. Train starts (depends on preprocess) → GPU pod scheduled
4. Evaluate starts (depends on train) → Metrics computed
5. If evaluation passes → Register model
6. If registered → Deploy to KServe
7. Pipeline completes → Endpoint ready
```

### 7.3 Monitoring

```bash
# Watch pipeline execution
kubectl get workflows -n kubeflow --watch

# Get logs
kubectl logs -n kubeflow <pod-name>

# Check MLflow
open http://mlflow.kubeflow.svc.cluster.local:5000

# Test inference endpoint
curl -X POST http://<endpoint>/v1/models/efficientnet:predict \
  -H "Content-Type: application/json" \
  -d '{"instances": [<image_data>]}'
```

---

## 8. Summary

### Component Checklist

| Component | Input | Output | Duration | GPU |
|-----------|-------|--------|----------|-----|
| Preprocess | Raw images | Processed tensors | 10-30min | No |
| Train | Processed data | Model checkpoint | 2-4hrs | Yes |
| Evaluate | Model + test data | Metrics | 15-30min | Yes |
| Register | Model + metrics | Registry entry | 5min | No |
| Deploy | Registered model | Inference endpoint | 5-10min | No |

### Critical Path

```
Preprocess (30min) → Train (3hrs) → Evaluate (30min) → Deploy (10min)
Total: ~4 hours for full pipeline
```

### Resource Requirements

- **Total CPU**: 12 cores
- **Total Memory**: 40Gi
- **GPU**: 1x V100 or better
- **Storage**: 200Gi PVC

---

Next: Review `DEPLOYMENT.md` for KServe configuration and canary deployment strategy.
