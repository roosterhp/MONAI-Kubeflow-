# Deployment Strategy: KServe + Triton Inference Server

## 1. Overview

### 1.1 Deployment Architecture

```
┌────────────────────────────────────────────────────────────┐
│                   Kubernetes Cluster                       │
├────────────────────────────────────────────────────────────┤
│                                                            │
│  ┌──────────────────────────────────────────────────────┐ │
│  │              KServe InferenceService                 │ │
│  ├──────────────────────────────────────────────────────┤ │
│  │                                                      │ │
│  │  ┌────────────────┐         ┌────────────────┐     │ │
│  │  │   Predictor    │         │     Canary     │     │ │
│  │  │   (v1.0.0)     │         │   (v1.1.0)     │     │ │
│  │  │   100% traffic │         │   0% traffic   │     │ │
│  │  └────────┬───────┘         └────────┬───────┘     │ │
│  │           │                           │             │ │
│  │           ▼                           ▼             │ │
│  │  ┌──────────────────────────────────────────────┐  │ │
│  │  │         Triton Inference Server              │  │ │
│  │  ├──────────────────────────────────────────────┤  │ │
│  │  │  Model Repository                            │  │ │
│  │  │  ├── efficientnet/                           │  │ │
│  │  │  │   ├── 1/ (v1.0.0)                        │  │ │
│  │  │  │   │   └── model.onnx                     │  │ │
│  │  │  │   ├── 2/ (v1.1.0)                        │  │ │
│  │  │  │   │   └── model.onnx                     │  │ │
│  │  │  │   └── config.pbtxt                       │  │ │
│  │  └──────────────────────────────────────────────┘  │ │
│  │                                                      │ │
│  └──────────────────────────────────────────────────────┘ │
│                            │                              │
│                            ▼                              │
│                 ┌─────────────────────┐                   │
│                 │  Service / Ingress  │                   │
│                 │  External Endpoint  │                   │
│                 └─────────────────────┘                   │
│                                                            │
└────────────────────────────────────────────────────────────┘
```

### 1.2 Technology Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Serving Framework** | KServe | Model serving orchestration |
| **Inference Runtime** | Triton Inference Server | High-performance inference |
| **Model Format** | ONNX | Cross-platform compatibility |
| **Fallback Format** | TorchScript | PyTorch native |
| **Load Balancing** | Istio | Traffic management |
| **Monitoring** | Prometheus + Grafana | Metrics and alerts |
| **Model Registry** | MLflow | Version management |

---

## 2. Model Export

### 2.1 ONNX Export (Primary)

#### Process

```python
# Pseudo-code structure

import torch
import torch.onnx

def export_to_onnx(
    model: nn.Module,
    output_path: str,
    input_shape: tuple = (1, 3, 224, 224),
):
    """
    Export PyTorch model to ONNX format
    """
    # Set model to eval mode
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
        do_constant_folding=True,
        input_names=['input'],
        output_names=['output'],
        dynamic_axes={
            'input': {0: 'batch_size'},
            'output': {0: 'batch_size'}
        }
    )

    # Validate
    validate_onnx_model(output_path, dummy_input)

    print(f"✅ ONNX model exported: {output_path}")
```

#### Validation

```python
# Pseudo-code structure

import onnxruntime as ort
import numpy as np

def validate_onnx_model(onnx_path: str, test_input: torch.Tensor):
    """
    Validate ONNX model produces same output as PyTorch
    """
    # Load PyTorch model
    pytorch_output = model(test_input).detach().numpy()

    # Load ONNX model
    session = ort.InferenceSession(onnx_path)
    onnx_output = session.run(
        None,
        {'input': test_input.numpy()}
    )[0]

    # Compare outputs
    diff = np.abs(pytorch_output - onnx_output).max()
    assert diff < 1e-5, f"ONNX validation failed: max diff = {diff}"

    print(f"✅ ONNX validation passed: max diff = {diff:.2e}")
```

#### File Structure

```
models/efficientnet/
├── 1/                          # Version 1
│   └── model.onnx             # ONNX model (24MB)
├── config.pbtxt               # Triton config
└── metadata.json              # Model metadata
```

### 2.2 TorchScript Export (Fallback)

```python
# Pseudo-code structure

def export_to_torchscript(
    model: nn.Module,
    output_path: str,
    input_shape: tuple = (1, 3, 224, 224),
):
    """
    Export to TorchScript for TorchServe backend
    """
    model.eval()

    # Trace model
    example_input = torch.randn(*input_shape)
    traced_model = torch.jit.trace(model, example_input)

    # Optimize for inference
    traced_model = torch.jit.optimize_for_inference(traced_model)

    # Save
    traced_model.save(output_path)

    # Validate
    loaded = torch.jit.load(output_path)
    assert torch.allclose(
        loaded(example_input),
        model(example_input),
        atol=1e-5
    )

    print(f"✅ TorchScript model exported: {output_path}")
```

---

## 3. Triton Model Repository

### 3.1 Directory Structure

```
triton-models/
└── efficientnet/
    ├── config.pbtxt               # Model configuration
    ├── 1/                         # Version 1 (current production)
    │   └── model.onnx
    ├── 2/                         # Version 2 (candidate)
    │   └── model.onnx
    └── labels.txt                 # Class labels
```

### 3.2 Triton Config (config.pbtxt)

```protobuf
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
    dims: [ 5 ]  # num_classes
  }
]

instance_group [
  {
    count: 1
    kind: KIND_GPU
    gpus: [ 0 ]
  }
]

dynamic_batching {
  preferred_batch_size: [ 8, 16, 32 ]
  max_queue_delay_microseconds: 1000
}

optimization {
  cuda {
    graphs: true
  }
}

model_warmup {
  name: "warmup_batch_8"
  batch_size: 8
  inputs {
    key: "input"
    value: {
      data_type: TYPE_FP32
      dims: [ 3, 224, 224 ]
      random_data: true
    }
  }
}
```

### 3.3 Model Repository Setup

```bash
# Script structure

# 1. Create model repository
mkdir -p triton-models/efficientnet/{1,2}

# 2. Copy ONNX models
cp exported/model_v1.onnx triton-models/efficientnet/1/model.onnx
cp exported/model_v2.onnx triton-models/efficientnet/2/model.onnx

# 3. Create config
cat > triton-models/efficientnet/config.pbtxt <<EOF
# Config content here
EOF

# 4. Create labels
cat > triton-models/efficientnet/labels.txt <<EOF
Normal
Pneumonia
COVID-19
Tuberculosis
Other
EOF

# 5. Upload to storage (S3/GCS/PVC)
kubectl cp triton-models/ <pod>:/models/
```

---

## 4. KServe InferenceService

### 4.1 Basic InferenceService Manifest

```yaml
apiVersion: serving.kserve.io/v1beta1
kind: InferenceService
metadata:
  name: efficientnet-classifier
  namespace: kubeflow
  annotations:
    serving.kserve.io/enable-prometheus-scraping: "true"
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
      env:
        - name: ORT_TENSORRT_FP16_ENABLE
          value: "1"
      readinessProbe:
        initialDelaySeconds: 30
        periodSeconds: 10
        timeoutSeconds: 5
      livenessProbe:
        initialDelaySeconds: 90
        periodSeconds: 30
        timeoutSeconds: 10
```

### 4.2 Deploying InferenceService

```bash
# Deploy
kubectl apply -f deployment/inferenceservice.yaml -n kubeflow

# Wait for ready
kubectl wait --for=condition=Ready \
  inferenceservice/efficientnet-classifier \
  -n kubeflow \
  --timeout=300s

# Get endpoint URL
kubectl get inferenceservice efficientnet-classifier \
  -n kubeflow \
  -o jsonpath='{.status.url}'

# Example output: http://efficientnet-classifier.kubeflow.example.com
```

### 4.3 Testing Inference

```bash
# Test inference

# Prepare input
cat > input.json <<EOF
{
  "inputs": [
    {
      "name": "input",
      "shape": [1, 3, 224, 224],
      "datatype": "FP32",
      "data": [<flattened_image_array>]
    }
  ]
}
EOF

# Send request
curl -X POST \
  http://efficientnet-classifier.kubeflow.example.com/v2/models/efficientnet/infer \
  -H "Content-Type: application/json" \
  -d @input.json

# Expected response
{
  "model_name": "efficientnet",
  "model_version": "1",
  "outputs": [
    {
      "name": "output",
      "shape": [1, 5],
      "datatype": "FP32",
      "data": [0.85, 0.10, 0.03, 0.01, 0.01]
    }
  ]
}
```

---

## 5. Canary Deployment

### 5.1 Strategy

**Canary Release Pattern**:
```
v1.0.0 (100%) → v1.1.0 (10%) → v1.1.0 (50%) → v1.1.0 (100%)
              ↓ monitor      ↓ monitor      ↓ monitor
           rollback?      rollback?      promote?
```

**Metrics to Monitor**:
- Latency (p50, p95, p99)
- Error rate
- Request rate
- Model metrics (AUC, accuracy if available)

**Decision Criteria**:
```python
# Pseudo-code

def should_promote_canary(metrics):
    """
    Decide whether to promote canary to production
    """
    # Latency check: p95 < 100ms
    if metrics['latency_p95'] > 100:
        return False, "Latency too high"

    # Error rate check: < 1%
    if metrics['error_rate'] > 0.01:
        return False, "Error rate too high"

    # Traffic comparison: canary vs baseline
    baseline_latency = metrics['baseline_latency_p95']
    canary_latency = metrics['canary_latency_p95']

    # Canary must be within 20% of baseline
    if canary_latency > baseline_latency * 1.2:
        return False, "Canary slower than baseline"

    return True, "Metrics passed"
```

### 5.2 Canary Manifest (10% Traffic)

```yaml
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
      # Version 1 (baseline)
      model_version: "1"
      resources:
        requests:
          cpu: "2"
          memory: "4Gi"
          nvidia.com/gpu: "1"

  # Canary configuration
  canaryTrafficPercent: 10  # 10% of traffic to canary

  canary:
    predictor:
      triton:
        storageUri: "pvc://data-pvc/models/efficientnet"
        runtimeVersion: "23.04-py3"
        # Version 2 (canary)
        model_version: "2"
        resources:
          requests:
            cpu: "2"
            memory: "4Gi"
            nvidia.com/gpu: "1"
```

### 5.3 Gradual Rollout Process

#### Step 1: Deploy Canary (10%)

```bash
# Deploy with 10% traffic to canary
kubectl apply -f deployment/canary/canary-10.yaml

# Monitor for 30 minutes
kubectl logs -f -n kubeflow \
  -l serving.kserve.io/inferenceservice=efficientnet-classifier
```

#### Step 2: Monitor Metrics

```bash
# Check Prometheus metrics

# Canary latency
rate(istio_request_duration_milliseconds_sum{
  destination_service="efficientnet-classifier-canary"
}[5m])

# Canary error rate
rate(istio_requests_total{
  destination_service="efficientnet-classifier-canary",
  response_code=~"5.."
}[5m])
```

#### Step 3: Increase to 50%

```bash
# If metrics look good, increase to 50%
kubectl patch inferenceservice efficientnet-classifier \
  -n kubeflow \
  --type='json' \
  -p='[{"op": "replace", "path": "/spec/canaryTrafficPercent", "value": 50}]'

# Monitor for 30 minutes
```

#### Step 4: Promote to 100%

```bash
# Promote canary to primary predictor
kubectl patch inferenceservice efficientnet-classifier \
  -n kubeflow \
  --type='json' \
  -p='[
    {"op": "replace", "path": "/spec/predictor/triton/model_version", "value": "2"},
    {"op": "remove", "path": "/spec/canary"}
  ]'
```

### 5.4 Automated Canary with Flagger

```yaml
apiVersion: flagger.app/v1beta1
kind: Canary
metadata:
  name: efficientnet-classifier
  namespace: kubeflow
spec:
  targetRef:
    apiVersion: serving.kserve.io/v1beta1
    kind: InferenceService
    name: efficientnet-classifier

  service:
    port: 80

  analysis:
    interval: 1m
    threshold: 5
    maxWeight: 50
    stepWeight: 10

    metrics:
      - name: request-success-rate
        thresholdRange:
          min: 99
        interval: 1m

      - name: request-duration
        thresholdRange:
          max: 100
        interval: 1m

  webhooks:
    - name: smoke-test
      url: http://flagger-loadtester/
      timeout: 5s
      metadata:
        type: bash
        cmd: |
          curl -X POST \
            http://efficientnet-classifier-canary/v2/models/efficientnet/infer \
            -H "Content-Type: application/json" \
            -d @test_input.json
```

**Flagger Workflow**:
```
1. Deploy canary
2. Wait 1 minute
3. Check metrics (success rate > 99%, latency < 100ms)
4. If pass: increase traffic by 10%
5. Repeat until 50% or failure
6. If fail: rollback immediately
7. If all pass: promote to 100%
```

---

## 6. Rollback Strategy

### 6.1 Immediate Rollback

```bash
# Rollback to previous version immediately

# Option 1: Remove canary
kubectl patch inferenceservice efficientnet-classifier \
  -n kubeflow \
  --type='json' \
  -p='[{"op": "remove", "path": "/spec/canary"}]'

# Option 2: Set traffic to 0%
kubectl patch inferenceservice efficientnet-classifier \
  -n kubeflow \
  --type='json' \
  -p='[{"op": "replace", "path": "/spec/canaryTrafficPercent", "value": 0}]'

# Option 3: Rollback to previous model version
kubectl patch inferenceservice efficientnet-classifier \
  -n kubeflow \
  --type='json' \
  -p='[{"op": "replace", "path": "/spec/predictor/triton/model_version", "value": "1"}]'
```

**Rollback Time**: < 2 minutes

### 6.2 Automated Rollback (Flagger)

```yaml
# Flagger automatically rolls back if:

analysis:
  metrics:
    - name: request-success-rate
      thresholdRange:
        min: 99  # If success rate < 99%, rollback

    - name: request-duration
      thresholdRange:
        max: 100  # If p95 latency > 100ms, rollback

  threshold: 5  # Allow 5 failed checks before rollback
```

### 6.3 Manual Rollback Checklist

```markdown
## Rollback Procedure

1. [ ] Identify issue (high latency / errors / low accuracy)
2. [ ] Stop canary rollout
   ```bash
   kubectl patch inferenceservice ... --type='json' -p='[{"op": "remove", "path": "/spec/canary"}]'
   ```
3. [ ] Verify baseline is serving 100% traffic
4. [ ] Check metrics return to normal
5. [ ] Investigate canary issues
6. [ ] Document root cause
7. [ ] Fix and redeploy canary

**Target Rollback Time**: < 2 minutes
```

---

## 7. Monitoring and Observability

### 7.1 Key Metrics

#### Latency

```promql
# p95 latency
histogram_quantile(0.95,
  rate(istio_request_duration_milliseconds_bucket{
    destination_service="efficientnet-classifier"
  }[5m])
)
```

#### Error Rate

```promql
# Error rate (5xx responses)
rate(istio_requests_total{
  destination_service="efficientnet-classifier",
  response_code=~"5.."
}[5m])
```

#### Throughput

```promql
# Requests per second
rate(istio_requests_total{
  destination_service="efficientnet-classifier"
}[1m])
```

#### GPU Utilization

```promql
# GPU utilization
DCGM_FI_DEV_GPU_UTIL{
  pod=~"efficientnet-classifier.*"
}
```

### 7.2 Grafana Dashboard

```json
{
  "dashboard": {
    "title": "EfficientNet Classifier",
    "panels": [
      {
        "title": "Latency (p50, p95, p99)",
        "targets": [
          {
            "expr": "histogram_quantile(0.50, ...)"
          },
          {
            "expr": "histogram_quantile(0.95, ...)"
          },
          {
            "expr": "histogram_quantile(0.99, ...)"
          }
        ]
      },
      {
        "title": "Error Rate",
        "targets": [
          {
            "expr": "rate(istio_requests_total{response_code=~\"5..\"}[5m])"
          }
        ]
      },
      {
        "title": "Throughput (RPS)",
        "targets": [
          {
            "expr": "rate(istio_requests_total[1m])"
          }
        ]
      },
      {
        "title": "GPU Utilization",
        "targets": [
          {
            "expr": "DCGM_FI_DEV_GPU_UTIL"
          }
        ]
      }
    ]
  }
}
```

### 7.3 Alerts

```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: efficientnet-alerts
  namespace: kubeflow
spec:
  groups:
    - name: efficientnet
      interval: 30s
      rules:
        - alert: HighLatency
          expr: |
            histogram_quantile(0.95,
              rate(istio_request_duration_milliseconds_bucket{
                destination_service="efficientnet-classifier"
              }[5m])
            ) > 100
          for: 5m
          labels:
            severity: warning
          annotations:
            summary: "High latency detected"
            description: "p95 latency is {{ $value }}ms"

        - alert: HighErrorRate
          expr: |
            rate(istio_requests_total{
              destination_service="efficientnet-classifier",
              response_code=~"5.."
            }[5m]) > 0.01
          for: 2m
          labels:
            severity: critical
          annotations:
            summary: "High error rate detected"
            description: "Error rate is {{ $value }}"

        - alert: ModelDown
          expr: |
            up{job="efficientnet-classifier"} == 0
          for: 1m
          labels:
            severity: critical
          annotations:
            summary: "Model endpoint is down"
```

---

## 8. Performance Optimization

### 8.1 TensorRT Conversion

```bash
# Convert ONNX to TensorRT for faster inference

# Install TensorRT
pip install tensorrt

# Convert
trtexec \
  --onnx=model.onnx \
  --saveEngine=model.plan \
  --fp16 \
  --workspace=4096

# Expected speedup: 2-3x faster inference
```

### 8.2 Triton Optimizations

```protobuf
# config.pbtxt optimizations

# 1. Dynamic batching (batch requests together)
dynamic_batching {
  preferred_batch_size: [ 8, 16, 32 ]
  max_queue_delay_microseconds: 1000  # 1ms max wait
}

# 2. Instance groups (multiple model instances)
instance_group [
  {
    count: 2  # Run 2 model copies
    kind: KIND_GPU
    gpus: [ 0 ]
  }
]

# 3. CUDA graphs (optimize GPU kernel launches)
optimization {
  cuda {
    graphs: true
  }
}
```

---

## 9. Deployment Checklist

### 9.1 Pre-Deployment

- [ ] Model exported to ONNX successfully
- [ ] ONNX model validated (outputs match PyTorch)
- [ ] Triton model repository created
- [ ] config.pbtxt configured correctly
- [ ] Model tested locally with Triton
- [ ] Inference latency < 100ms (p95)
- [ ] GPU node available in cluster
- [ ] KServe installed and configured
- [ ] Monitoring (Prometheus/Grafana) setup

### 9.2 Initial Deployment

- [ ] InferenceService manifest created
- [ ] Applied to cluster: `kubectl apply -f inferenceservice.yaml`
- [ ] Service becomes Ready: `kubectl wait --for=condition=Ready`
- [ ] Endpoint accessible
- [ ] Smoke test passed
- [ ] Latency within SLA
- [ ] No errors in logs

### 9.3 Canary Deployment

- [ ] Canary manifest created (10% traffic)
- [ ] Applied to cluster
- [ ] Monitor metrics for 30 minutes
- [ ] Latency within 20% of baseline
- [ ] Error rate < 1%
- [ ] Increase to 50% traffic
- [ ] Monitor for 30 minutes
- [ ] Promote to 100% or rollback

### 9.4 Post-Deployment

- [ ] Production traffic serving successfully
- [ ] Monitoring dashboard updated
- [ ] Alerts configured
- [ ] Rollback procedure tested
- [ ] Documentation updated
- [ ] Team trained on rollback procedure

---

## 10. Troubleshooting

### 10.1 Common Issues

| Issue | Symptom | Solution |
|-------|---------|----------|
| **High Latency** | p95 > 100ms | Enable dynamic batching, use TensorRT |
| **OOM Errors** | Pod crashes | Increase memory limits, reduce batch size |
| **Model Not Found** | 404 errors | Check storageUri, verify PVC mount |
| **GPU Not Used** | Low GPU util | Verify GPU resources requested |
| **Cold Start** | First request slow | Enable model warmup in config |

### 10.2 Debug Commands

```bash
# Check InferenceService status
kubectl describe inferenceservice efficientnet-classifier -n kubeflow

# Check pod logs
kubectl logs -n kubeflow \
  -l serving.kserve.io/inferenceservice=efficientnet-classifier

# Check Triton logs
kubectl exec -n kubeflow <pod> -- cat /tmp/triton.log

# Test model directly (bypass Istio)
kubectl port-forward -n kubeflow <pod> 8000:8000
curl localhost:8000/v2/models/efficientnet

# Check GPU availability
kubectl exec -n kubeflow <pod> -- nvidia-smi
```

---

## Summary

### Deployment Flow

```
1. Export model (ONNX) → 2. Create Triton repository
     ↓                           ↓
3. Deploy InferenceService → 4. Test endpoint
     ↓                           ↓
5. Deploy canary (10%) → 6. Monitor metrics
     ↓                           ↓
7. Increase to 50% → 8. Promote to 100% OR Rollback
```

### Key Metrics

- **Latency Target**: p95 < 100ms
- **Error Rate Target**: < 1%
- **Availability Target**: > 99.9%
- **Rollback Time Target**: < 2 minutes

### Next Steps

Review `5DAY_PLAN.md` for day-by-day implementation timeline.
