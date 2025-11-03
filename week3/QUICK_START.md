# Quick Start Guide

**Goal**: Get started with EfficientNetV2-S integration in under 30 minutes.

---

## Prerequisites Check

```bash
# Verify installations
python --version        # Python 3.9+
docker --version        # Docker 20.10+
kubectl version         # Kubernetes 1.24+
minikube status         # Minikube running

# Verify GPU (optional but recommended)
nvidia-smi
```

---

## Step 1: Clone and Setup (5 min)

```bash
# Navigate to project
cd week3

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install torch torchvision \
            monai[all] \
            timm \
            mlflow \
            onnx \
            onnxruntime

# Verify timm installation
python -c "import timm; print(timm.list_models('efficientnetv2*'))"
# Should list: efficientnetv2_rw_s, efficientnetv2_rw_m, ...
```

---

## Step 2: Test Model Integration (10 min)

```bash
# Create test script
cat > test_model.py <<'EOF'
import torch
import timm

# Load EfficientNetV2-S
model = timm.create_model(
    'efficientnetv2_rw_s',
    pretrained=True,
    num_classes=5
)
model.eval()

# Test forward pass
dummy_input = torch.randn(1, 3, 224, 224)
output = model(dummy_input)

print(f"✅ Model loaded successfully")
print(f"   Input shape: {dummy_input.shape}")
print(f"   Output shape: {output.shape}")
print(f"   Output: {output.softmax(dim=1)}")
EOF

# Run test
python test_model.py

# Expected output:
# ✅ Model loaded successfully
#    Input shape: torch.Size([1, 3, 224, 224])
#    Output shape: torch.Size([1, 5])
#    Output: tensor([[0.2001, 0.2004, 0.1998, 0.1999, 0.1998]], grad_fn=<SoftmaxBackward>)
```

---

## Step 3: Prepare Sample Data (10 min)

```bash
# Create data directory
mkdir -p data/sample/{train,val,test}

# Create sample structure
for split in train val test; do
  for class in 0 1 2 3 4; do
    mkdir -p data/sample/$split/class_$class
  done
done

# Download sample medical images (or use your own)
# Place images in data/sample/train/class_X/

# Verify structure
tree data/sample/

# Expected:
# data/sample/
# ├── train/
# │   ├── class_0/
# │   │   └── *.png
# │   ├── class_1/
# │   └── ...
# ├── val/
# └── test/
```

---

## Step 4: Test MONAI Integration (5 min)

```bash
# Create MONAI test script
cat > test_monai.py <<'EOF'
from monai.data import Dataset, DataLoader
from monai.transforms import Compose, LoadImage, EnsureChannelFirst, Resize, ToTensor

# Define transforms
transforms = Compose([
    LoadImage(image_only=True),
    EnsureChannelFirst(),
    Resize((224, 224)),
    ToTensor(),
])

# Create simple dataset
data = [
    {"image": "data/sample/train/class_0/image1.png", "label": 0}
]

dataset = Dataset(data=data, transform=transforms)
loader = DataLoader(dataset, batch_size=1)

# Test loading
for batch in loader:
    print(f"✅ MONAI data loading successful")
    print(f"   Batch image shape: {batch['image'].shape}")
    print(f"   Batch label: {batch['label']}")
    break
EOF

python test_monai.py
```

---

## Step 5: Review Documentation (5 min)

```bash
# Read key documents in order:
# 1. ARCHITECTURE.md      - Understand design decisions
# 2. PIPELINE_DESIGN.md   - Component specifications
# 3. 5DAY_PLAN.md         - Implementation timeline

# Quick scan:
head -50 ARCHITECTURE.md
head -50 PIPELINE_DESIGN.md
head -50 5DAY_PLAN.md
```

---

## Step 6: Next Actions

### Option A: Start Day 1 Implementation

```bash
# Follow Day 1 plan
cat 5DAY_PLAN.md | grep -A 50 "## Day 1"

# Begin with:
# 1. Create models/efficientnet_wrapper.py
# 2. Implement EfficientNetV2Wrapper class
# 3. Test forward pass and freeze/unfreeze
```

### Option B: Build Docker Images

```bash
# Build preprocessing component
cd components/preprocess
docker build -t efficientnet-preprocess:v1 .

# Test locally
docker run --rm \
  -v $(pwd)/data:/data \
  efficientnet-preprocess:v1 \
  --raw-data-path /data/sample \
  --output-path /data/processed
```

### Option C: Test on Kubeflow

```bash
# Load image to minikube
minikube image load efficientnet-preprocess:v1

# Create test pipeline
kubectl apply -f pipeline/test_pipeline.yaml -n kubeflow

# Watch execution
kubectl get workflows -n kubeflow --watch
```

---

## Troubleshooting

### Issue: timm model download fails

```bash
# Manual download
mkdir -p ~/.cache/torch/hub/checkpoints
wget https://github.com/rwightman/pytorch-image-models/releases/download/v0.1-effv2-weights/efficientnetv2_rw_s_ra2-36bf1e4d.pth \
  -O ~/.cache/torch/hub/checkpoints/efficientnetv2_rw_s_ra2-36bf1e4d.pth
```

### Issue: CUDA not available

```bash
# Verify CUDA
python -c "import torch; print(torch.cuda.is_available())"

# If False, training will use CPU (slower but works)
```

### Issue: Docker build fails

```bash
# Check Docker daemon
docker ps

# Clear Docker cache
docker system prune -a

# Rebuild with no cache
docker build --no-cache -t efficientnet-preprocess:v1 .
```

---

## Summary of What You Achieved

- [x] Environment setup complete
- [x] Model integration tested
- [x] MONAI compatibility verified
- [x] Sample data structure created
- [x] Documentation reviewed

**Time Spent**: ~30 minutes

**Next**: Begin Day 1 implementation (see `5DAY_PLAN.md`)

---

## Quick Reference

### Important Files

```
week3/
├── README.md              ← Start here
├── ARCHITECTURE.md        ← Why EfficientNetV2-S?
├── PIPELINE_DESIGN.md     ← Component specs
├── DEPLOYMENT.md          ← KServe deployment
├── 5DAY_PLAN.md           ← Day-by-day tasks
└── SUMMARY.md             ← Executive overview
```

### Key Commands

```bash
# Test model
python -c "import timm; model = timm.create_model('efficientnetv2_rw_s', pretrained=True)"

# Build Docker image
docker build -t efficientnet-train:v1 components/train/

# Submit pipeline
kubectl apply -f pipeline/classification_pipeline.yaml

# Check status
kubectl get workflows,inferenceservices -n kubeflow

# Test inference
curl -X POST $ENDPOINT/v2/models/efficientnet/infer -d @input.json
```

### Help and Support

- **Slack**: `#ml-ops`, `#model-dev`
- **Documentation**: See `*.md` files in this directory
- **Issues**: Check `TROUBLESHOOTING.md` (to be created during implementation)

---

**Ready to start? → Open `5DAY_PLAN.md` and begin Day 1!**
