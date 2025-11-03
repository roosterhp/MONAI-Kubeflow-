# Week 3: External Model Integration - EfficientNetV2-S for Medical Image Classification

**Task**: Integrate timm.EfficientNetV2-S into MONAI pipeline for 2D medical image classification (X-ray/Ultrasound)

**Pipeline**: Integration → Fine-tuning → Evaluation → Kubeflow/KServe Deployment

---

## Project Structure

```
week3/
├── README.md                          # This file
├── ARCHITECTURE.md                    # Technical architecture & rationale
├── PIPELINE_DESIGN.md                 # Kubeflow pipeline components
├── DEPLOYMENT.md                      # KServe deployment strategy
├── 5DAY_PLAN.md                       # Implementation timeline
├── components/                        # Kubeflow pipeline components
│   ├── preprocess/
│   │   ├── Dockerfile
│   │   ├── preprocess.py
│   │   └── component.yaml
│   ├── train/
│   │   ├── Dockerfile
│   │   ├── train.py
│   │   ├── model_wrapper.py
│   │   └── component.yaml
│   ├── evaluate/
│   │   ├── Dockerfile
│   │   ├── evaluate.py
│   │   ├── medical_metrics.py
│   │   └── component.yaml
│   ├── register/
│   │   ├── Dockerfile
│   │   ├── register.py
│   │   └── component.yaml
│   └── deploy/
│       ├── Dockerfile
│       ├── deploy.py
│       └── component.yaml
├── models/                            # Model definitions
│   ├── efficientnet_wrapper.py
│   ├── export_onnx.py
│   └── export_torchscript.py
├── pipeline/                          # Pipeline definitions
│   ├── classification_pipeline.yaml
│   └── config.yaml
├── deployment/                        # KServe manifests
│   ├── inferenceservice.yaml
│   ├── predictor.yaml
│   └── canary/
│       ├── canary.yaml
│       └── rollback.yaml
├── data/                              # Data preparation
│   ├── README.md
│   └── data_structure.txt
├── scripts/                           # Utility scripts
│   ├── prepare_data.py
│   ├── build_images.sh
│   └── deploy_pipeline.sh
└── tests/                             # Testing
    ├── test_model.py
    ├── test_inference.py
    └── test_deployment.py
```

---

## Quick Start

### Prerequisites
- Minikube/Kubernetes cluster
- Kubeflow Pipelines installed
- KServe installed
- GPU node (optional but recommended)

### Setup
```bash
cd week3

# 1. Build component images
./scripts/build_images.sh

# 2. Prepare data
python scripts/prepare_data.py --data-dir /path/to/data

# 3. Submit pipeline
kubectl apply -f pipeline/classification_pipeline.yaml

# 4. Deploy model
kubectl apply -f deployment/inferenceservice.yaml
```

---

## Key Documents

1. **ARCHITECTURE.md**: Why EfficientNetV2-S? How to integrate with MONAI?
2. **PIPELINE_DESIGN.md**: Kubeflow component specifications
3. **DEPLOYMENT.md**: KServe deployment patterns (canary, rollback)
4. **5DAY_PLAN.md**: Implementation timeline and deliverables

---

## Objectives

### Phase 1: Integration (Day 1-2)
- Wrap timm.EfficientNetV2-S for MONAI compatibility
- Create data preprocessing pipeline
- Build training component

### Phase 2: Training & Evaluation (Day 2-3)
- Fine-tune on custom medical dataset
- Implement medical metrics (AUC, F1, Accuracy, ECE)
- Validate model performance

### Phase 3: Model Export (Day 3-4)
- Export to TorchScript
- Export to ONNX
- Validate exported models

### Phase 4: Deployment (Day 4-5)
- Create KServe InferenceService
- Configure Triton/TorchServe backend
- Implement canary deployment
- Test rollback mechanism

---

## Success Metrics

- Model AUC > 0.90 on validation set
- Inference latency < 100ms (p95)
- Deployment uptime > 99.9%
- Successful canary rollout (10% → 50% → 100%)
- Rollback time < 2 minutes

---

## Next Steps

1. Read `ARCHITECTURE.md` to understand design decisions
2. Review `PIPELINE_DESIGN.md` for implementation details
3. Follow `5DAY_PLAN.md` for day-by-day execution
