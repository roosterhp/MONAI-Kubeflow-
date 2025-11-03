# 5-Day Implementation Plan: EfficientNetV2-S Medical Classifier

## Overview

**Objective**: Integrate timm.EfficientNetV2-S into MONAI pipeline, fine-tune on medical data, deploy to KServe with canary rollout.

**Timeline**: 5 days (8 hours/day = 40 hours total)

**Team**: 1 ML Engineer

---

## Day 1: Model Integration & Data Preparation

### Objectives
- Integrate EfficientNetV2-S from timm with MONAI
- Prepare data preprocessing pipeline
- Create training component structure

### Tasks

#### Morning (4 hours)

**Task 1.1: Project Setup (1 hour)**
```bash
# Create project structure
mkdir -p week3/{components,models,pipeline,deployment,scripts,tests}

# Setup Python environment
python -m venv venv
source venv/bin/activate
pip install torch torchvision monai[all] timm mlflow onnx onnxruntime

# Verify installations
python -c "import timm; print(timm.list_models('efficientnetv2*'))"
```

**Deliverable**: ✅ Project structure created, dependencies installed

---

**Task 1.2: Model Wrapper Implementation (2 hours)**

```python
# week3/models/efficientnet_wrapper.py

class EfficientNetV2Wrapper(nn.Module):
    """
    Wrapper for timm EfficientNetV2-S
    Compatible with MONAI training engine
    """
    def __init__(self, num_classes=5, pretrained=True):
        super().__init__()
        self.model = timm.create_model(
            'efficientnetv2_rw_s',
            pretrained=pretrained,
            num_classes=num_classes
        )

    def forward(self, x):
        return self.model(x)

    def freeze_backbone(self):
        # Implementation
        pass

    def unfreeze_all(self):
        # Implementation
        pass
```

**Testing**:
```bash
python tests/test_model.py --test-forward-pass
python tests/test_model.py --test-freeze-unfreeze
```

**Deliverable**: ✅ Model wrapper implemented and tested

---

**Task 1.3: MONAI Integration (1 hour)**

```python
# week3/models/monai_integration.py

from monai.engines import SupervisedTrainer
from monai.losses import CrossEntropyLoss

def create_trainer(model, train_loader, val_loader):
    """
    Create MONAI trainer with EfficientNet model
    """
    trainer = SupervisedTrainer(
        device=device,
        max_epochs=30,
        train_data_loader=train_loader,
        network=model,
        optimizer=optimizer,
        loss_function=CrossEntropyLoss(label_smoothing=0.1),
        inferer=SimpleInferer(),
        amp=True,
    )
    return trainer
```

**Deliverable**: ✅ MONAI trainer integrated with timm model

---

#### Afternoon (4 hours)

**Task 1.4: Data Preprocessing Component (3 hours)**

```python
# components/preprocess/preprocess.py

from monai.transforms import Compose, LoadImaged, Resized

class DataPreprocessor:
    def __init__(self, data_path, output_path):
        self.data_path = data_path
        self.output_path = output_path

    def get_transforms(self):
        return Compose([
            LoadImaged(keys=["image"]),
            EnsureChannelFirstd(keys=["image"]),
            Resized(keys=["image"], spatial_size=(224, 224)),
            ScaleIntensityd(keys=["image"]),
            Normalized(keys=["image"],
                      mean=[0.485, 0.456, 0.406],
                      std=[0.229, 0.224, 0.225]),
        ])

    def process(self):
        # Load data
        # Apply transforms
        # Split train/val/test
        # Save to cache
        pass
```

**Build Docker Image**:
```dockerfile
# components/preprocess/Dockerfile

FROM python:3.9-slim
RUN pip install monai[all] nibabel pydicom
COPY preprocess.py /app/
ENTRYPOINT ["python", "/app/preprocess.py"]
```

```bash
docker build -t efficientnet-preprocess:v1 components/preprocess/
```

**Deliverable**: ✅ Preprocessing component Docker image built

---

**Task 1.5: Create Component YAML (1 hour)**

```yaml
# components/preprocess/component.yaml

name: preprocess-medical-images
description: Preprocess 2D medical images

inputs:
  - {name: raw_data_path, type: String}
  - {name: output_path, type: String}

outputs:
  - {name: processed_data_path, type: String}
  - {name: dataset_stats, type: JsonObject}

implementation:
  container:
    image: efficientnet-preprocess:v1
    command: [python, /app/preprocess.py]
    args:
      - --raw-data-path
      - {inputValue: raw_data_path}
      - --output-path
      - {inputValue: output_path}
```

**Deliverable**: ✅ Kubeflow component specification created

---

### Day 1 Definition of Done

- [x] Project structure created
- [x] EfficientNetV2Wrapper implemented and tested
- [x] MONAI integration working
- [x] Preprocessing component Docker image built
- [x] Component YAML specifications created
- [x] Forward pass test passes
- [x] Model can load pretrained weights

**Estimated Hours**: 8 hours

---

## Day 2: Training Component & Fine-tuning

### Objectives
- Create training component
- Implement two-stage fine-tuning
- Setup MLflow tracking
- Run initial training

### Tasks

#### Morning (4 hours)

**Task 2.1: Training Component Implementation (3 hours)**

```python
# components/train/train.py

class TwoStageTrainer:
    def __init__(self, model, train_loader, val_loader):
        self.model = model
        self.train_loader = train_loader
        self.val_loader = val_loader

    def stage1_freeze_backbone(self, epochs=5):
        """Train classifier head only"""
        self.model.freeze_backbone()
        optimizer = AdamW(
            self.model.model.classifier.parameters(),
            lr=1e-3
        )
        self._train(optimizer, epochs)

    def stage2_full_finetune(self, epochs=20):
        """Fine-tune entire model"""
        self.model.unfreeze_all()
        optimizer = AdamW([
            {'params': self.model.model.features.parameters(), 'lr': 1e-4},
            {'params': self.model.model.classifier.parameters(), 'lr': 1e-3}
        ], weight_decay=0.01)
        scheduler = CosineAnnealingLR(optimizer, T_max=epochs)
        self._train(optimizer, epochs, scheduler)

    def stage3_refinement(self, epochs=5):
        """Low learning rate refinement"""
        optimizer = AdamW(self.model.parameters(), lr=1e-5)
        self._train(optimizer, epochs)

    def _train(self, optimizer, epochs, scheduler=None):
        # Training loop with MONAI engine
        pass
```

**Deliverable**: ✅ Two-stage trainer implemented

---

**Task 2.2: MLflow Integration (1 hour)**

```python
# components/train/mlflow_logger.py

import mlflow

class MLflowLogger:
    def __init__(self, experiment_name):
        mlflow.set_experiment(experiment_name)

    def start_run(self, run_name, params):
        self.run = mlflow.start_run(run_name=run_name)
        mlflow.log_params(params)

    def log_metrics(self, metrics, step):
        mlflow.log_metrics(metrics, step=step)

    def log_model(self, model, artifact_path):
        mlflow.pytorch.log_model(model, artifact_path)

    def end_run(self):
        mlflow.end_run()
```

**Deliverable**: ✅ MLflow tracking integrated

---

#### Afternoon (4 hours)

**Task 2.3: Build Training Docker Image (1 hour)**

```dockerfile
# components/train/Dockerfile

FROM pytorch/pytorch:2.1.0-cuda11.8-cudnn8-runtime

RUN pip install --no-cache-dir \
    monai[all]==1.3.0 \
    timm==0.9.10 \
    mlflow==2.9.0

COPY train.py model_wrapper.py trainer.py mlflow_logger.py /app/

ENTRYPOINT ["python", "/app/train.py"]
```

```bash
docker build -t efficientnet-train:v1 components/train/
minikube image load efficientnet-train:v1
```

**Deliverable**: ✅ Training Docker image built and loaded

---

**Task 2.4: Run Initial Training (3 hours)**

```bash
# Prepare sample data
python scripts/prepare_data.py \
  --data-dir /path/to/data \
  --output-dir /mnt/data/processed

# Run training locally first
python components/train/train.py \
  --data-path /mnt/data/processed \
  --num-classes 5 \
  --max-epochs 30 \
  --batch-size 32 \
  --output-path /mnt/data/models/v1

# Monitor in MLflow
open http://localhost:5000
```

**Expected Output**:
```
Stage 1 (5 epochs):  val_acc = 0.75
Stage 2 (20 epochs): val_acc = 0.90
Stage 3 (5 epochs):  val_acc = 0.92

Best model saved: /mnt/data/models/v1/best_model.pth
```

**Deliverable**: ✅ Model trained successfully, val_acc > 0.85

---

### Day 2 Definition of Done

- [x] Two-stage training implemented
- [x] MLflow tracking working
- [x] Training Docker image built
- [x] Initial training completed (30 epochs)
- [x] Best model checkpoint saved
- [x] Validation accuracy > 0.85
- [x] Training metrics logged to MLflow
- [x] No overfitting (train/val gap < 5%)

**Estimated Hours**: 8 hours

---

## Day 3: Evaluation & Model Export

### Objectives
- Implement evaluation component
- Compute medical metrics
- Export model to ONNX
- Validate exported model

### Tasks

#### Morning (4 hours)

**Task 3.1: Evaluation Component (2 hours)**

```python
# components/evaluate/evaluate.py

from sklearn.metrics import (
    roc_auc_score, f1_score, accuracy_score,
    confusion_matrix, classification_report
)

class ModelEvaluator:
    def __init__(self, model_path, test_data_path):
        self.model = load_model(model_path)
        self.test_loader = create_test_loader(test_data_path)

    def evaluate(self):
        y_true, y_pred, y_pred_proba = self._run_inference()

        metrics = {
            "auc_roc": roc_auc_score(y_true, y_pred_proba, multi_class='ovr'),
            "f1_score": f1_score(y_true, y_pred, average='weighted'),
            "accuracy": accuracy_score(y_true, y_pred),
            "sensitivity": recall_score(y_true, y_pred, average='weighted'),
            "ece": self._compute_ece(y_true, y_pred_proba),
            "confusion_matrix": confusion_matrix(y_true, y_pred).tolist(),
        }

        return metrics

    def _compute_ece(self, y_true, y_pred_proba, n_bins=10):
        # Expected Calibration Error implementation
        pass
```

**Deliverable**: ✅ Evaluation component implemented

---

**Task 3.2: Medical Metrics Implementation (1 hour)**

```python
# components/evaluate/medical_metrics.py

def compute_ece(y_true, y_pred_proba, n_bins=10):
    """Expected Calibration Error"""
    bins = np.linspace(0, 1, n_bins + 1)
    ece = 0.0

    for i in range(n_bins):
        in_bin = (y_pred_proba >= bins[i]) & (y_pred_proba < bins[i+1])
        if in_bin.sum() > 0:
            bin_acc = y_true[in_bin].mean()
            bin_conf = y_pred_proba[in_bin].mean()
            ece += np.abs(bin_acc - bin_conf) * in_bin.sum()

    return ece / len(y_true)

def compute_sensitivity_specificity(y_true, y_pred):
    """Sensitivity and Specificity per class"""
    # Implementation
    pass
```

**Deliverable**: ✅ Medical metrics functions implemented

---

**Task 3.3: Run Evaluation (1 hour)**

```bash
python components/evaluate/evaluate.py \
  --model-path /mnt/data/models/v1/best_model.pth \
  --test-data-path /mnt/data/processed/test \
  --output-path /mnt/data/metrics/v1

# Expected output
cat /mnt/data/metrics/v1/metrics.json
{
  "auc_roc": 0.942,
  "f1_score": 0.889,
  "accuracy": 0.901,
  "ece": 0.082,
  "confusion_matrix": [[180, 10, 5, 3, 2],
                       [8, 175, 7, 5, 5],
                       ...],
  "validation": "PASSED"
}
```

**Deliverable**: ✅ Evaluation metrics computed, thresholds passed

---

#### Afternoon (4 hours)

**Task 3.4: ONNX Export Implementation (2 hours)**

```python
# models/export_onnx.py

import torch.onnx

def export_to_onnx(
    model_path: str,
    output_path: str,
    input_shape: tuple = (1, 3, 224, 224)
):
    """Export PyTorch model to ONNX"""

    # Load model
    model = EfficientNetV2Wrapper.load_from_checkpoint(model_path)
    model.eval()

    # Create dummy input
    dummy_input = torch.randn(*input_shape)

    # Export
    torch.onnx.export(
        model,
        dummy_input,
        output_path,
        export_params=True,
        opset_version=13,
        input_names=['input'],
        output_names=['output'],
        dynamic_axes={
            'input': {0: 'batch_size'},
            'output': {0: 'batch_size'}
        }
    )

    print(f"✅ Exported to {output_path}")

    # Validate
    validate_onnx(output_path, dummy_input, model)
```

**Run Export**:
```bash
python models/export_onnx.py \
  --model-path /mnt/data/models/v1/best_model.pth \
  --output-path /mnt/data/models/v1/model.onnx

# Verify file size
ls -lh /mnt/data/models/v1/model.onnx
# Expected: ~24MB
```

**Deliverable**: ✅ ONNX model exported

---

**Task 3.5: ONNX Validation (1 hour)**

```python
# tests/test_onnx_export.py

import onnxruntime as ort

def validate_onnx_model(onnx_path, pytorch_model, test_input):
    """Validate ONNX model matches PyTorch"""

    # PyTorch inference
    pytorch_output = pytorch_model(test_input).detach().numpy()

    # ONNX inference
    session = ort.InferenceSession(onnx_path)
    onnx_output = session.run(
        None,
        {'input': test_input.numpy()}
    )[0]

    # Compare
    diff = np.abs(pytorch_output - onnx_output).max()
    assert diff < 1e-5, f"Max diff: {diff}"

    print(f"✅ Validation passed: max diff = {diff:.2e}")
```

**Run Validation**:
```bash
python tests/test_onnx_export.py --onnx-path /mnt/data/models/v1/model.onnx
# ✅ Validation passed: max diff = 3.42e-07
```

**Deliverable**: ✅ ONNX model validated

---

**Task 3.6: Build Evaluation Docker Image (1 hour)**

```dockerfile
# components/evaluate/Dockerfile

FROM pytorch/pytorch:2.1.0-cuda11.8-cudnn8-runtime

RUN pip install --no-cache-dir \
    monai[all]==1.3.0 \
    scikit-learn==1.3.0 \
    matplotlib==3.8.0

COPY evaluate.py medical_metrics.py visualization.py /app/

ENTRYPOINT ["python", "/app/evaluate.py"]
```

```bash
docker build -t efficientnet-evaluate:v1 components/evaluate/
minikube image load efficientnet-evaluate:v1
```

**Deliverable**: ✅ Evaluation Docker image built

---

### Day 3 Definition of Done

- [x] Evaluation component implemented
- [x] Medical metrics computed (AUC, F1, ECE)
- [x] All metrics exceed thresholds
- [x] ONNX model exported
- [x] ONNX validation passed (diff < 1e-5)
- [x] Evaluation Docker image built
- [x] metrics.json saved
- [x] Model ready for deployment

**Estimated Hours**: 8 hours

---

## Day 4: Kubeflow Pipeline & KServe Deployment

### Objectives
- Create complete Kubeflow pipeline
- Setup Triton model repository
- Deploy initial InferenceService
- Test inference endpoint

### Tasks

#### Morning (4 hours)

**Task 4.1: Complete Pipeline YAML (2 hours)**

```yaml
# pipeline/classification_pipeline.yaml

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
            # ... arguments

          - name: train
            template: train-component
            dependencies: [preprocess]
            # ... arguments

          - name: evaluate
            template: evaluate-component
            dependencies: [train]
            # ... arguments

          - name: register
            template: register-component
            dependencies: [evaluate]
            when: "{{tasks.evaluate.outputs.parameters.passed}} == true"

          - name: deploy
            template: deploy-component
            dependencies: [register]

    # Component templates
    - name: preprocess-component
      # ... preprocess template

    - name: train-component
      # ... train template

    - name: evaluate-component
      # ... evaluate template
```

**Deliverable**: ✅ Complete pipeline YAML created

---

**Task 4.2: Submit Pipeline to Kubeflow (1 hour)**

```bash
# Submit pipeline
kubectl apply -f pipeline/classification_pipeline.yaml -n kubeflow

# Watch execution
kubectl get workflows -n kubeflow --watch

# Get logs
WORKFLOW_NAME=$(kubectl get workflows -n kubeflow -o jsonpath='{.items[0].metadata.name}')
kubectl logs -f -n kubeflow $WORKFLOW_NAME-preprocess

# Expected timeline:
# - Preprocess: 20 min
# - Train: 3 hours
# - Evaluate: 20 min
# - Total: ~4 hours
```

**Deliverable**: ✅ Pipeline submitted and running

---

**Task 4.3: Monitor Pipeline (1 hour)**

```bash
# Check status
kubectl get workflows -n kubeflow

# View in Kubeflow UI
open http://localhost:8080/pipeline

# Check MLflow experiments
open http://localhost:5000
```

**Deliverable**: ✅ Pipeline monitoring setup

---

#### Afternoon (4 hours)

**Task 4.4: Create Triton Model Repository (1 hour)**

```bash
# Create directory structure
mkdir -p triton-models/efficientnet/1

# Copy ONNX model
cp /mnt/data/models/v1/model.onnx triton-models/efficientnet/1/

# Create config
cat > triton-models/efficientnet/config.pbtxt <<EOF
name: "efficientnet"
platform: "onnxruntime_onnx"
max_batch_size: 32

input [
  {
    name: "input"
    data_type: TYPE_FP32
    dims: [ 3, 224, 224 ]
  }
]

output [
  {
    name: "output"
    data_type: TYPE_FP32
    dims: [ 5 ]
  }
]

dynamic_batching {
  preferred_batch_size: [ 8, 16, 32 ]
  max_queue_delay_microseconds: 1000
}
EOF

# Copy to PVC
kubectl cp triton-models/ data-loader:/mnt/data/models/
```

**Deliverable**: ✅ Triton model repository created

---

**Task 4.5: Create InferenceService (1 hour)**

```yaml
# deployment/inferenceservice.yaml

apiVersion: serving.kserve.io/v1beta1
kind: InferenceService
metadata:
  name: efficientnet-classifier
  namespace: kubeflow
spec:
  predictor:
    triton:
      storageUri: "pvc://data-pvc/models/efficientnet"
      runtimeVersion: "23.04-py3"
      resources:
        requests:
          cpu: "2"
          memory: "4Gi"
          nvidia.com/gpu: "1"
        limits:
          cpu: "4"
          memory: "8Gi"
          nvidia.com/gpu: "1"
```

**Deploy**:
```bash
kubectl apply -f deployment/inferenceservice.yaml -n kubeflow

# Wait for ready
kubectl wait --for=condition=Ready \
  inferenceservice/efficientnet-classifier \
  -n kubeflow \
  --timeout=300s
```

**Deliverable**: ✅ InferenceService deployed

---

**Task 4.6: Test Inference Endpoint (2 hours)**

```bash
# Get endpoint URL
ENDPOINT=$(kubectl get inferenceservice efficientnet-classifier \
  -n kubeflow \
  -o jsonpath='{.status.url}')

echo "Endpoint: $ENDPOINT"

# Prepare test image
python scripts/prepare_test_input.py \
  --image test_images/xray_001.png \
  --output test_input.json

# Test inference
curl -X POST \
  $ENDPOINT/v2/models/efficientnet/infer \
  -H "Content-Type: application/json" \
  -d @test_input.json

# Expected response
{
  "model_name": "efficientnet",
  "model_version": "1",
  "outputs": [
    {
      "name": "output",
      "datatype": "FP32",
      "shape": [1, 5],
      "data": [0.85, 0.10, 0.03, 0.01, 0.01]
    }
  ]
}
```

**Load Testing**:
```bash
# Test latency
for i in {1..100}; do
  curl -w "@curl-format.txt" -X POST $ENDPOINT/v2/models/efficientnet/infer \
    -H "Content-Type: application/json" \
    -d @test_input.json
done | awk '{print $1}' | sort -n | awk '{
  p50 = NR * 0.5;
  p95 = NR * 0.95;
  p99 = NR * 0.99;
}
END {
  print "p50:", p50;
  print "p95:", p95;
  print "p99:", p99;
}'

# Expected:
# p50: 45ms
# p95: 85ms
# p99: 120ms
```

**Deliverable**: ✅ Inference endpoint tested, latency < 100ms (p95)

---

### Day 4 Definition of Done

- [x] Complete Kubeflow pipeline created
- [x] Pipeline submitted successfully
- [x] All components completed (preprocess → train → evaluate)
- [x] Model evaluation passed thresholds
- [x] Triton model repository created
- [x] InferenceService deployed
- [x] Endpoint accessible and tested
- [x] Latency p95 < 100ms
- [x] No errors in inference

**Estimated Hours**: 8 hours

---

## Day 5: Canary Deployment & Rollback Testing

### Objectives
- Implement canary deployment
- Test gradual rollout (10% → 50% → 100%)
- Test rollback mechanism
- Setup monitoring and alerts
- Documentation

### Tasks

#### Morning (4 hours)

**Task 5.1: Create Canary Deployment Manifest (1 hour)**

```yaml
# deployment/canary/canary-10.yaml

apiVersion: serving.kserve.io/v1beta1
kind: InferenceService
metadata:
  name: efficientnet-classifier
  namespace: kubeflow
spec:
  predictor:
    triton:
      storageUri: "pvc://data-pvc/models/efficientnet"
      model_version: "1"  # Baseline
      # ... resources

  canaryTrafficPercent: 10  # 10% to canary

  canary:
    predictor:
      triton:
        storageUri: "pvc://data-pvc/models/efficientnet"
        model_version: "2"  # Canary
        # ... resources
```

**Deploy Canary**:
```bash
kubectl apply -f deployment/canary/canary-10.yaml -n kubeflow
```

**Deliverable**: ✅ Canary deployed with 10% traffic

---

**Task 5.2: Monitor Canary Metrics (1 hour)**

```bash
# Setup Prometheus queries

# Baseline latency
baseline_latency=$(curl -s 'http://prometheus:9090/api/v1/query' \
  --data-urlencode 'query=histogram_quantile(0.95,
    rate(istio_request_duration_milliseconds_bucket{
      destination_service="efficientnet-classifier-predictor"
    }[5m])
  )' | jq -r '.data.result[0].value[1]')

echo "Baseline p95: ${baseline_latency}ms"

# Canary latency
canary_latency=$(curl -s 'http://prometheus:9090/api/v1/query' \
  --data-urlencode 'query=histogram_quantile(0.95,
    rate(istio_request_duration_milliseconds_bucket{
      destination_service="efficientnet-classifier-canary"
    }[5m])
  )' | jq -r '.data.result[0].value[1]')

echo "Canary p95: ${canary_latency}ms"

# Error rate
error_rate=$(curl -s 'http://prometheus:9090/api/v1/query' \
  --data-urlencode 'query=rate(istio_requests_total{
      destination_service="efficientnet-classifier-canary",
      response_code=~"5.."
    }[5m])' | jq -r '.data.result[0].value[1]')

echo "Canary error rate: ${error_rate}"
```

**Decision**:
```python
# Should promote?
if canary_latency < baseline_latency * 1.2 and error_rate < 0.01:
    print("✅ Metrics look good, increase to 50%")
else:
    print("❌ Metrics failed, rollback")
```

**Deliverable**: ✅ Canary monitored for 30 minutes, metrics validated

---

**Task 5.3: Increase Canary to 50% (30 min)**

```bash
# Patch to 50%
kubectl patch inferenceservice efficientnet-classifier \
  -n kubeflow \
  --type='json' \
  -p='[{"op": "replace", "path": "/spec/canaryTrafficPercent", "value": 50}]'

# Monitor for 30 minutes
watch -n 60 'kubectl get inferenceservice efficientnet-classifier -n kubeflow'
```

**Deliverable**: ✅ Canary at 50%, metrics stable

---

**Task 5.4: Promote to 100% (30 min)**

```bash
# Promote canary to primary
kubectl patch inferenceservice efficientnet-classifier \
  -n kubeflow \
  --type='json' \
  -p='[
    {"op": "replace", "path": "/spec/predictor/triton/model_version", "value": "2"},
    {"op": "remove", "path": "/spec/canary"}
  ]'

# Verify
kubectl get inferenceservice efficientnet-classifier -n kubeflow
```

**Deliverable**: ✅ Canary promoted to 100%

---

**Task 5.5: Test Rollback (1 hour)**

```bash
# Simulate issue (manually trigger high latency or errors)

# Execute rollback
kubectl patch inferenceservice efficientnet-classifier \
  -n kubeflow \
  --type='json' \
  -p='[{"op": "replace", "path": "/spec/predictor/triton/model_version", "value": "1"}]'

# Time the rollback
time kubectl wait --for=condition=Ready \
  inferenceservice/efficientnet-classifier \
  -n kubeflow \
  --timeout=120s

# Expected: < 2 minutes

# Verify traffic back to v1
curl $ENDPOINT/v2/models/efficientnet/config | jq '.versions'
# Should show version "1"
```

**Deliverable**: ✅ Rollback tested, completed in < 2 minutes

---

#### Afternoon (4 hours)

**Task 5.6: Setup Grafana Dashboard (1 hour)**

```bash
# Import dashboard
kubectl apply -f deployment/monitoring/grafana-dashboard.yaml

# Open Grafana
open http://grafana.kubeflow.svc.cluster.local:3000

# Verify panels:
# - Latency (p50, p95, p99)
# - Error rate
# - Throughput (RPS)
# - GPU utilization
# - Canary vs Baseline comparison
```

**Deliverable**: ✅ Grafana dashboard configured

---

**Task 5.7: Setup Alerts (1 hour)**

```yaml
# deployment/monitoring/alerts.yaml

apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: efficientnet-alerts
spec:
  groups:
    - name: efficientnet
      rules:
        - alert: HighLatency
          expr: histogram_quantile(0.95, ...) > 100
          for: 5m
          labels:
            severity: warning

        - alert: HighErrorRate
          expr: rate(...) > 0.01
          for: 2m
          labels:
            severity: critical

        - alert: ModelDown
          expr: up{job="efficientnet-classifier"} == 0
          for: 1m
          labels:
            severity: critical
```

```bash
kubectl apply -f deployment/monitoring/alerts.yaml -n kubeflow
```

**Deliverable**: ✅ Prometheus alerts configured

---

**Task 5.8: Documentation (2 hours)**

```markdown
# Create deployment runbook

## Deployment Runbook

### Pre-deployment Checklist
- [ ] Model exported to ONNX
- [ ] Validation metrics passed
- [ ] Triton config created
- [ ] GPU node available

### Deployment Steps
1. Create Triton model repository
2. Deploy InferenceService
3. Test endpoint
4. Deploy canary (10%)
5. Monitor 30 min
6. Increase to 50%
7. Monitor 30 min
8. Promote to 100%

### Rollback Procedure
1. Identify issue
2. Execute: kubectl patch ... model_version=1
3. Verify traffic
4. Investigate root cause

### Troubleshooting
- High latency → Check dynamic batching, GPU util
- OOM errors → Increase memory limits
- Model not found → Verify storageUri

### Contacts
- On-call: [name]
- Slack: #ml-ops
```

**Create other docs**:
- `DEPLOYMENT_RUNBOOK.md`
- `TROUBLESHOOTING.md`
- `METRICS_GUIDE.md`

**Deliverable**: ✅ Documentation completed

---

### Day 5 Definition of Done

- [x] Canary deployment executed (10% → 50% → 100%)
- [x] Metrics monitored at each stage
- [x] Rollback tested and validated (< 2 min)
- [x] Grafana dashboard configured
- [x] Prometheus alerts setup
- [x] Documentation completed
- [x] Production deployment successful
- [x] No issues in production traffic
- [x] Team trained on rollback procedure

**Estimated Hours**: 8 hours

---

## Summary

### Total Timeline

| Day | Focus | Hours | Key Deliverables |
|-----|-------|-------|------------------|
| **Day 1** | Integration & Data Prep | 8 | Model wrapper, preprocessing component |
| **Day 2** | Training | 8 | Fine-tuned model, MLflow tracking |
| **Day 3** | Evaluation & Export | 8 | Metrics > thresholds, ONNX model |
| **Day 4** | Pipeline & Deployment | 8 | Kubeflow pipeline, InferenceService |
| **Day 5** | Canary & Monitoring | 8 | Canary rollout, documentation |
| **Total** | | **40 hours** | **Production ML system** |

### Critical Path

```
Day 1 (Model) → Day 2 (Training) → Day 3 (Export) → Day 4 (Deploy) → Day 5 (Canary)
    8h             8h                 8h              8h               8h
```

### Success Criteria

- [x] Model accuracy > 0.85
- [x] AUC > 0.90, F1 > 0.85, ECE < 0.10
- [x] Inference latency p95 < 100ms
- [x] Canary deployment successful
- [x] Rollback time < 2 minutes
- [x] Zero downtime deployment
- [x] Monitoring and alerts operational
- [x] Documentation complete

### Risks and Mitigations

| Risk | Mitigation |
|------|------------|
| Training takes longer (>4h) | Start training early Day 2, use smaller model if needed |
| ONNX export issues | Fallback to TorchScript, simplify model ops |
| Kubeflow issues | Test components locally first |
| GPU not available | Train on CPU (slower), deploy CPU inference |
| Canary fails | Have rollback tested and ready |

### Post-Deployment

**Week 2 Tasks**:
- Monitor production metrics (7 days)
- Collect production data for retraining
- Fine-tune based on production feedback
- A/B test with v2 model
- Scale inference pods based on traffic

**Long-term Roadmap**:
- Automated retraining pipeline
- Model drift detection
- Continuous evaluation on production data
- Multi-model ensemble
- Edge deployment optimization

---

## Appendix

### Quick Reference Commands

```bash
# Build all images
./scripts/build_images.sh

# Submit pipeline
kubectl apply -f pipeline/classification_pipeline.yaml

# Deploy InferenceService
kubectl apply -f deployment/inferenceservice.yaml

# Check status
kubectl get workflows,inferenceservices -n kubeflow

# Test inference
curl -X POST $ENDPOINT/v2/models/efficientnet/infer -d @input.json

# Rollback
kubectl patch inferenceservice efficientnet-classifier \
  --type='json' \
  -p='[{"op": "replace", "path": "/spec/predictor/triton/model_version", "value": "1"}]'
```

### Resource Requirements

- **Development Machine**: 16GB RAM, 8 cores
- **Kubernetes Cluster**: 3 nodes, 1 GPU node (V100/A100)
- **Storage**: 200Gi PVC
- **Network**: Ingress configured for external access

### Tools Required

- Docker
- kubectl
- Kubeflow Pipelines
- KServe
- Minikube (for local testing)
- Python 3.9+
- CUDA 11.8+ (for GPU)

---

**End of 5-Day Implementation Plan**
