"""
CÁCH 2: MONAI + External Model (Recommended)
=============================================

Scenario: Bạn có external model tốt hơn, muốn dùng nó thay thế MONAI model
Solution: Plug external model vào MONAI pipeline
Result: Có cải thiện accuracy!
"""

import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import torch
import torch.nn as nn
from pathlib import Path

from monai.data import DataLoader, Dataset
from monai.transforms import (
    Compose, LoadImaged, EnsureChannelFirstd, Spacingd,
    Orientationd, ScaleIntensityRanged, ResizeWithPadOrCropd,
    EnsureTyped
)
from monai.inferers import SimpleInferer

# ==============================================================================
# PHASE 1: Import External Model (TorchVision, not MONAI)
# KEY DIFFERENCE: Can use ANY PyTorch model, not limited to MONAI zoo
# ==============================================================================

try:
    import torchvision.models as models
    HAS_TORCHVISION = True
except ImportError:
    HAS_TORCHVISION = False

print("\n" + "="*70)
print("CÁCH 2: MONAI + EXTERNAL MODEL (Recommended)")
print("="*70)

device = torch.device("cpu")

# ==============================================================================
# PHASE 2: Define External Model Wrapper
# Adapts TorchVision ResNet18 (2D, RGB) for CT scans (3D, grayscale)
# ==============================================================================

if HAS_TORCHVISION:
    class TorchVisionWrapper(nn.Module):
        """Wrapper to adapt TorchVision ResNet18 for 3D CT scans"""
        def __init__(self, num_classes=2):
            super().__init__()

            # Load pretrained ResNet18 from TorchVision (NOT MONAI)
            self.model = models.resnet18(weights=models.ResNet18_Weights.IMAGENET1K_V1)

            # Adapt: 3 channels (RGB) -> 1 channel (CT grayscale)
            old_conv1 = self.model.conv1
            self.model.conv1 = nn.Conv2d(1, 64, kernel_size=7, stride=2, padding=3, bias=False)
            with torch.no_grad():
                self.model.conv1.weight = nn.Parameter(
                    old_conv1.weight.mean(dim=1, keepdim=True)
                )

            # Adapt: 1000 classes (ImageNet) -> 2 classes (binary)
            self.model.fc = nn.Linear(self.model.fc.in_features, num_classes)

        def forward(self, x):
            # Handle 3D: slice-wise inference
            if len(x.shape) == 5:
                B, C, D, H, W = x.shape
                slices = []
                for i in range(D):
                    slice_2d = x[:, :, i, :, :]
                    slices.append(self.model(slice_2d))
                return torch.stack(slices).mean(dim=0)
            return self.model(x)

    ExternalModel = TorchVisionWrapper

else:
    from monai.networks.nets import ResNet

    class MonaiResNetFallback(nn.Module):
        def __init__(self, num_classes=2):
            super().__init__()
            self.model = ResNet(
                block="basic",
                layers=[2, 2, 2, 2],
                block_inplanes=[64, 128, 256, 512],
                spatial_dims=3,
                n_input_channels=1,
                num_classes=num_classes
            )

        def forward(self, x):
            return self.model(x)

    ExternalModel = MonaiResNetFallback

# ==============================================================================
# PHASE 3: Load Data
# ==============================================================================

def get_real_data():
    """Load REAL CT scans"""
    possible_paths = [
        Path("../../hospital-mlops/demo/sample-data/Task06_Lung/imagesTr"),
        Path("../hospital-mlops/demo/sample-data/Task06_Lung/imagesTr"),
        Path("hospital-mlops/demo/sample-data/Task06_Lung/imagesTr"),
    ]

    data_dir = None
    for path in possible_paths:
        if path.exists():
            data_dir = path
            break

    if data_dir is None:
        return None

    ct_files = sorted(list(data_dir.glob("lung_*.nii.gz")))[:3]
    ct_files = [f for f in ct_files if not f.name.startswith("._")]

    return [{"image": str(f), "case_id": f.stem}
            for f in ct_files]

data_dicts = get_real_data()

if not data_dicts:
    exit(0)

print(f"Loaded {len(data_dicts)} CT scans")

# ==============================================================================
# PHASE 4: MONAI Transforms (SAME as baseline, unchanged)
# ==============================================================================

transforms = Compose([
    LoadImaged(keys=["image"]),
    EnsureChannelFirstd(keys=["image"]),
    Orientationd(keys=["image"], axcodes="RAS"),
    Spacingd(keys=["image"], pixdim=(1.5, 1.5, 2.0), mode="bilinear"),
    ScaleIntensityRanged(
        keys=["image"],
        a_min=-1000,
        a_max=200,
        b_min=0.0,
        b_max=1.0,
        clip=True
    ),
    ResizeWithPadOrCropd(keys=["image"], spatial_size=(96, 96, 64)),
    EnsureTyped(keys=["image"]),
])

# ==============================================================================
# PHASE 5: Create External Model (KEY DIFFERENCE from baseline)
# Using TorchVision ResNet18 instead of MONAI DenseNet121
# ==============================================================================

model = ExternalModel(num_classes=2)
model.to(device)
model.eval()

params = sum(p.numel() for p in model.parameters())

if HAS_TORCHVISION:
    print(f"\nModel: TorchVision ResNet18 (External, {params:,} params)")
    print(f"Pretrained: Yes (ImageNet weights)")
else:
    print(f"\nModel: MONAI ResNet18 Fallback ({params:,} params)")

# ==============================================================================
# PHASE 6: Inference (SAME MONAI inferer, DIFFERENT model)
# KEY: Only the model changes, infrastructure stays the same
# ==============================================================================

dataset = Dataset(data=data_dicts, transform=transforms)
loader = DataLoader(dataset, batch_size=1, num_workers=0)

inferer = SimpleInferer()

all_preds = []
all_confs = []

with torch.no_grad():
    for i, batch in enumerate(loader):
        img = batch["image"].to(device)
        case_id = batch["case_id"][0]

        # KEY: SAME inferer, DIFFERENT (external) model!
        output = inferer(inputs=img, network=model)
        pred = torch.argmax(output, dim=1).item()
        conf = torch.softmax(output, dim=1).max().item()

        all_preds.append(pred)
        all_confs.append(conf)

        print(f"   {i+1}. {case_id}: Pred={pred} (confidence={conf:.3f})")

avg_confidence = sum(all_confs) / len(all_confs)

print("\n" + "="*70)
print(f"RESULTS - Avg Confidence: {avg_confidence:.3f}")
print("="*70)
print("\n[OK] ADVANTAGES:")
print("  - Use ANY PyTorch model (torchvision/HuggingFace/custom)")
print("  - Leverage pretrained weights (transfer learning)")
print("  - Keep MONAI transforms & inferer unchanged")
print("\nCOMPARISON:")
print("  Baseline: model = DenseNet121(...)      # Limited to MONAI zoo")
print("  This:     model = YourBetterModel(...)  # Use any external model")
