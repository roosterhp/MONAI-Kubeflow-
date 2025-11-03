# Week 3 Project Structure

Complete file and directory structure for EfficientNetV2-S integration project.

---

## Directory Tree

```
week3/
├── README.md                          # Project overview and quick navigation
├── ARCHITECTURE.md                    # Technical design decisions and rationale
├── PIPELINE_DESIGN.md                 # Kubeflow component specifications
├── DEPLOYMENT.md                      # KServe deployment strategy
├── 5DAY_PLAN.md                       # Day-by-day implementation plan
├── SUMMARY.md                         # Executive summary
├── QUICK_START.md                     # 30-minute getting started guide
├── CHECKLIST.md                       # Implementation checklist
├── PROJECT_STRUCTURE.md               # This file
│
├── components/                        # Kubeflow pipeline components
│   ├── preprocess/
│   │   ├── Dockerfile
│   │   ├── preprocess.py
│   │   ├── transforms.py
│   │   └── component.yaml
│   │
│   ├── train/
│   │   ├── Dockerfile
│   │   ├── train.py
│   │   ├── model_wrapper.py
│   │   ├── trainer.py
│   │   ├── mlflow_logger.py
│   │   └── component.yaml
│   │
│   ├── evaluate/
│   │   ├── Dockerfile
│   │   ├── evaluate.py
│   │   ├── medical_metrics.py
│   │   ├── visualization.py
│   │   └── component.yaml
│   │
│   ├── register/
│   │   ├── Dockerfile
│   │   ├── register.py
│   │   └── component.yaml
│   │
│   └── deploy/
│       ├── Dockerfile
│       ├── deploy.py
│       ├── export_onnx.py
│       └── component.yaml
│
├── models/                            # Model definitions and utilities
│   ├── efficientnet_wrapper.py        # Main model wrapper class
│   ├── export_onnx.py                 # ONNX export utility
│   ├── export_torchscript.py          # TorchScript export (fallback)
│   └── model_utils.py                 # Helper functions
│
├── pipeline/                          # Pipeline definitions
│   ├── classification_pipeline.yaml   # Main Kubeflow pipeline
│   ├── config.yaml                    # Pipeline configuration
│   ├── test_pipeline.yaml             # Testing pipeline
│   └── pipeline_utils.py              # Pipeline helper functions
│
├── deployment/                        # Deployment manifests
│   ├── inferenceservice.yaml          # Basic InferenceService
│   ├── predictor.yaml                 # Predictor configuration
│   │
│   ├── canary/
│   │   ├── canary-10.yaml             # 10% canary traffic
│   │   ├── canary-50.yaml             # 50% canary traffic
│   │   ├── canary-100.yaml            # Full promotion
│   │   └── rollback.yaml              # Rollback manifest
│   │
│   └── monitoring/
│       ├── grafana-dashboard.yaml     # Grafana dashboard config
│       ├── alerts.yaml                # Prometheus alerts
│       └── servicemonitor.yaml        # Service monitoring config
│
├── data/                              # Data-related files
│   ├── README.md                      # Data preparation guide
│   ├── data_structure.txt             # Expected data format
│   └── sample/                        # Sample data (not in repo)
│       ├── train/
│       ├── val/
│       └── test/
│
├── scripts/                           # Utility scripts
│   ├── README.md                      # Script documentation
│   ├── prepare_data.py                # Data preparation
│   ├── build_images.sh                # Build all Docker images
│   ├── deploy_pipeline.sh             # Deploy pipeline to Kubeflow
│   ├── test_inference.sh              # Test inference endpoint
│   └── monitor_metrics.sh             # Monitor production metrics
│
├── tests/                             # Testing
│   ├── test_model.py                  # Model wrapper tests
│   ├── test_transforms.py             # Data transform tests
│   ├── test_onnx_export.py            # ONNX validation tests
│   ├── test_inference.py              # Inference tests
│   └── test_deployment.py             # Deployment tests
│
└── docs/                              # Additional documentation (created during impl)
    ├── DEPLOYMENT_RUNBOOK.md
    ├── TROUBLESHOOTING.md
    ├── METRICS_GUIDE.md
    └── API_REFERENCE.md
```

---

## File Purposes

### Documentation (Root Level)

| File | Purpose | Audience |
|------|---------|----------|
| **README.md** | Project entry point | All |
| **ARCHITECTURE.md** | Why EfficientNetV2-S? Technical decisions | Engineers |
| **PIPELINE_DESIGN.md** | Component specs, DAG structure | ML Engineers |
| **DEPLOYMENT.md** | KServe, Triton, canary strategy | DevOps, SRE |
| **5DAY_PLAN.md** | Implementation timeline | Project Manager |
| **SUMMARY.md** | Executive overview | Leadership |
| **QUICK_START.md** | 30-min getting started | New developers |
| **CHECKLIST.md** | Task tracking | All implementers |
| **PROJECT_STRUCTURE.md** | This file | All |

### Components Directory

Each component follows this structure:

```
component_name/
├── Dockerfile           # Container definition
├── main_script.py       # Primary logic
├── component.yaml       # Kubeflow component spec
└── utils.py            # Helper functions (optional)
```

**Preprocess Component**:
- Loads raw medical images
- Applies MONAI transforms
- Splits train/val/test
- Caches processed data

**Train Component**:
- Two-stage fine-tuning
- MLflow tracking
- Model checkpointing
- GPU-optimized

**Evaluate Component**:
- Medical metrics (AUC, F1, ECE)
- Confusion matrix
- Calibration analysis
- Validation thresholds

**Register Component**:
- MLflow Model Registry
- Version tagging
- Metadata storage

**Deploy Component**:
- ONNX export
- Triton model repository
- InferenceService deployment
- Health checks

### Models Directory

**efficientnet_wrapper.py**:
```python
class EfficientNetV2Wrapper(nn.Module):
    """
    Wraps timm.EfficientNetV2-S for MONAI
    """
    - __init__: Load pretrained model
    - forward: Standard forward pass
    - freeze_backbone: Freeze encoder for stage 1
    - unfreeze_all: Unfreeze for stage 2
```

**export_onnx.py**:
- Export PyTorch → ONNX
- Validate exported model
- Optimize for inference

### Pipeline Directory

**classification_pipeline.yaml**:
- Argo Workflow definition
- DAG structure
- Component dependencies
- Resource specifications

**config.yaml**:
- Hyperparameters
- Data paths
- Model configuration
- Training settings

### Deployment Directory

**inferenceservice.yaml**:
- KServe InferenceService manifest
- Triton backend configuration
- Resource requests/limits
- Autoscaling rules

**Canary Deployment**:
- `canary-10.yaml`: Initial 10% traffic
- `canary-50.yaml`: Increase to 50%
- `canary-100.yaml`: Full promotion
- `rollback.yaml`: Emergency rollback

**Monitoring**:
- Grafana dashboards
- Prometheus alerts
- ServiceMonitor for scraping

### Scripts Directory

Utility scripts for common operations:

| Script | Purpose |
|--------|---------|
| **prepare_data.py** | Organize and validate dataset |
| **build_images.sh** | Build all Docker images |
| **deploy_pipeline.sh** | Submit pipeline to Kubeflow |
| **test_inference.sh** | Test deployed endpoint |
| **monitor_metrics.sh** | Query Prometheus metrics |

### Tests Directory

Test files for CI/CD:

| Test File | Coverage |
|-----------|----------|
| **test_model.py** | Model wrapper, forward pass |
| **test_transforms.py** | MONAI transforms |
| **test_onnx_export.py** | ONNX validation |
| **test_inference.py** | End-to-end inference |
| **test_deployment.py** | K8s deployment |

---

## Implementation Order

Follow this order when creating files:

### Day 1: Foundation
1. `models/efficientnet_wrapper.py`
2. `components/preprocess/preprocess.py`
3. `components/preprocess/Dockerfile`
4. `components/preprocess/component.yaml`
5. `tests/test_model.py`

### Day 2: Training
1. `components/train/model_wrapper.py` (copy from models/)
2. `components/train/trainer.py`
3. `components/train/train.py`
4. `components/train/mlflow_logger.py`
5. `components/train/Dockerfile`
6. `components/train/component.yaml`

### Day 3: Evaluation
1. `components/evaluate/medical_metrics.py`
2. `components/evaluate/evaluate.py`
3. `components/evaluate/visualization.py`
4. `components/evaluate/Dockerfile`
5. `models/export_onnx.py`
6. `tests/test_onnx_export.py`

### Day 4: Pipeline
1. `pipeline/config.yaml`
2. `pipeline/classification_pipeline.yaml`
3. `deployment/inferenceservice.yaml`
4. `scripts/deploy_pipeline.sh`

### Day 5: Canary
1. `deployment/canary/canary-10.yaml`
2. `deployment/canary/canary-50.yaml`
3. `deployment/canary/rollback.yaml`
4. `deployment/monitoring/grafana-dashboard.yaml`
5. `deployment/monitoring/alerts.yaml`
6. `docs/DEPLOYMENT_RUNBOOK.md`

---

## File Size Estimates

| File/Directory | Size | Notes |
|----------------|------|-------|
| **Documentation (*.md)** | ~500KB | Text files |
| **Python scripts** | ~50KB | Code files |
| **Docker images** | ~5GB total | All components |
| **- preprocess** | ~500MB | Python + MONAI |
| **- train** | ~3GB | PyTorch + MONAI + timm |
| **- evaluate** | ~1GB | PyTorch + sklearn |
| **- deploy** | ~500MB | Lightweight |
| **Model artifacts** | ~24MB | ONNX model |
| **Trained checkpoint** | ~100MB | PyTorch .pth |
| **Total (excl. data)** | ~5.5GB | |

---

## Git Structure

### .gitignore

```
# Python
__pycache__/
*.pyc
*.pyo
venv/
*.egg-info/

# Data
data/sample/
data/processed/
*.nii.gz
*.dcm
*.png
*.jpg

# Models
models/*.pth
models/*.onnx
models/*.pt

# MLflow
mlruns/

# Kubernetes
*.log
.kube/

# Docker
.dockerignore

# IDE
.vscode/
.idea/
```

### Branches

- `main`: Stable, production-ready
- `develop`: Active development
- `feature/day1-integration`: Day 1 implementation
- `feature/day2-training`: Day 2 implementation
- `feature/day3-evaluation`: Day 3 implementation
- `feature/day4-pipeline`: Day 4 implementation
- `feature/day5-canary`: Day 5 implementation

### Commits

Use conventional commits:
```
feat: add EfficientNetV2Wrapper class
fix: resolve ONNX export precision issue
docs: update ARCHITECTURE.md with rationale
test: add model forward pass tests
chore: build Docker images for all components
```

---

## Resources Requirements

### Development Environment

- **CPU**: 8 cores
- **RAM**: 16GB
- **Storage**: 100GB
- **GPU**: Optional (NVIDIA, CUDA 11.8+)

### Kubernetes Cluster

- **Nodes**: 3 (1 control, 2 workers)
- **Worker CPU**: 8 cores each
- **Worker RAM**: 32GB each
- **GPU Node**: 1 (V100 or A100)
- **Storage**: 200Gi PVC

### Network

- **Ingress**: Configured for external access
- **DNS**: For inference endpoint
- **Bandwidth**: 1Gbps

---

## Quick Navigation

**Start here**: `README.md` → `QUICK_START.md` → `5DAY_PLAN.md`

**Technical deep dive**: `ARCHITECTURE.md` → `PIPELINE_DESIGN.md` → `DEPLOYMENT.md`

**Implementation**: Follow `CHECKLIST.md` and `5DAY_PLAN.md` day by day

**Troubleshooting**: `docs/TROUBLESHOOTING.md` (created during implementation)

---

## Version Control

- **Project Version**: 1.0.0 (initial documentation)
- **Documentation Date**: 2025-10-31
- **Last Updated**: 2025-10-31

### Changelog

- **1.0.0** (2025-10-31): Initial project structure and documentation
- **1.1.0** (TBD): Post-Day 1 implementation updates
- **1.2.0** (TBD): Post-Day 2 implementation updates
- **2.0.0** (TBD): Production deployment and learnings

---

**This structure is designed for clarity, scalability, and maintainability.**

**All files follow consistent naming conventions and organization patterns.**

**Refer to this document when adding new files or restructuring the project.**
