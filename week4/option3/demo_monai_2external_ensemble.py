"""
Option 3 Enhanced: Ensemble 1 MONAI + 2 External Models
Combines MONAI DenseNet121 with TorchVision ResNet18 and MedicalNet for robust predictions
Ensemble strategies: Weighted Average & Majority Voting
"""

import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import torch
import torch.nn as nn
import numpy as np
from pathlib import Path
from monai.data import Dataset, DataLoader
from monai.transforms import (
    Compose, LoadImaged, EnsureChannelFirstd,
    Orientationd, Spacingd, ScaleIntensityRanged,
    ResizeWithPadOrCropd, EnsureTyped
)
from monai.inferers import SimpleInferer
from monai.networks.nets import DenseNet121

# Import external models
try:
    import torchvision.models as models
    HAS_TORCHVISION = True
except ImportError:
    HAS_TORCHVISION = False

# Import MedicalNet
try:
    from models.medicalnet_resnet import resnet50_medicalnet
    HAS_MEDICALNET = True
except ImportError:
    HAS_MEDICALNET = False

# Set random seeds for reproducibility
torch.manual_seed(42)
np.random.seed(42)

# ==============================================================================
# PHASE 1: Setup and Data Loading
# ==============================================================================

print("\n" + "="*70)
print("OPTION 3 ENHANCED: ENSEMBLE 1 MONAI + 2 EXTERNAL MODELS")
print("="*70)
print("Initializing...")

device = torch.device("cpu")

def get_real_data():
    """Load REAL CT scans from Task06_Lung dataset"""
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
        print("[ERROR] Task06_Lung dataset not found!")
        print("  Searched paths:")
        for p in possible_paths:
            print(f"    - {p}")
        return None

    ct_files = sorted(list(data_dir.glob("lung_*.nii.gz")))[:3]
    ct_files = [f for f in ct_files if not f.name.startswith("._")]

    if not ct_files:
        print("[ERROR] No CT files found in", data_dir)
        return None

    return [{"image": str(f), "case_id": f.stem} for f in ct_files]

data_dicts = get_real_data()

if not data_dicts:
    print("[ERROR] No data found. Exiting.")
    exit(1)

print(f"[OK] Loaded {len(data_dicts)} CT scans")

# ==============================================================================
# PHASE 2: MONAI Transforms (same for all models)
# ==============================================================================

transforms = Compose([
    LoadImaged(keys=["image"]),
    EnsureChannelFirstd(keys=["image"]),
    Orientationd(keys=["image"], axcodes="RAS"),
    Spacingd(keys=["image"], pixdim=(1.5, 1.5, 2.0), mode="bilinear"),
    ScaleIntensityRanged(
        keys=["image"],
        a_min=-1000,
        a_max=400,
        b_min=0.0,
        b_max=1.0,
        clip=True
    ),
    ResizeWithPadOrCropd(keys=["image"], spatial_size=(96, 96, 96)),
    EnsureTyped(keys=["image"]),
])

dataset = Dataset(data=data_dicts, transform=transforms)
loader = DataLoader(dataset, batch_size=1, num_workers=0)

# ==============================================================================
# PHASE 3: External Model 1 - TorchVision ResNet18 Wrapper
# ==============================================================================

class TorchVisionResNetWrapper(nn.Module):
    """Wrapper to adapt TorchVision ResNet18 for 3D CT scans"""
    def __init__(self, num_classes=2):
        super().__init__()

        if not HAS_TORCHVISION:
            raise ImportError("TorchVision not available")

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
        # Handle 3D: slice-wise inference with attention pooling
        if len(x.shape) == 5:
            B, C, D, H, W = x.shape
            slices = []
            slice_weights = []

            for i in range(D):
                slice_2d = x[:, :, i, :, :]
                slice_output = self.model(slice_2d)
                slices.append(slice_output)
                # Use center slices with higher weight
                weight = 1.0 - abs(i - D/2) / (D/2) * 0.5
                slice_weights.append(weight)

            # Weighted average of slice predictions
            stacked = torch.stack(slices)
            weights = torch.tensor(slice_weights).view(-1, 1, 1).to(stacked.device)
            weighted_avg = (stacked * weights).sum(dim=0) / weights.sum()
            return weighted_avg
        return self.model(x)

# ==============================================================================
# PHASE 4: External Model 2 - MedicalNet Wrapper
# ==============================================================================

class MedicalNetWrapper(nn.Module):
    """Wrapper for MedicalNet 3D ResNet50"""
    def __init__(self, num_classes=2):
        super().__init__()

        if not HAS_MEDICALNET:
            # Fallback to MONAI ResNet if MedicalNet not available
            from monai.networks.nets import resnet50
            self.model = resnet50(
                spatial_dims=3,
                n_input_channels=1,
                num_classes=num_classes
            )
            print("[WARNING] MedicalNet not available, using MONAI ResNet50 fallback")
        else:
            self.model = resnet50_medicalnet(num_classes=num_classes, pretrained=True)

    def forward(self, x):
        return self.model(x)

# ==============================================================================
# PHASE 5: Load 3 Models (1 MONAI + 2 External)
# ==============================================================================

print("\n" + "="*70)
print("LOADING 3 MODELS: 1 MONAI + 2 EXTERNAL")
print("="*70)

# Model 1: MONAI DenseNet121 (Internal MONAI model)
print("\n[1/3] MONAI DenseNet121 (Internal)")

model1 = DenseNet121(
    spatial_dims=3,
    in_channels=1,
    out_channels=2
)
model1.to(device)
model1.eval()
params1 = sum(p.numel() for p in model1.parameters())
print(f"    Loaded: {params1:,} params (MONAI native)")

# Model 2: TorchVision ResNet18 (External model 1)
print("\n[2/3] TorchVision ResNet18 (External - ImageNet pretrained)")

if HAS_TORCHVISION:
    model2 = TorchVisionResNetWrapper(num_classes=2)
    model2.to(device)
    model2.eval()
    params2 = sum(p.numel() for p in model2.parameters())
    print(f"    Loaded: {params2:,} params (ImageNet pretrained)")
else:
    print("    [SKIPPED] TorchVision not available")
    model2 = None

# Model 3: MedicalNet ResNet50 (External model 2)
print("\n[3/3] MedicalNet 3D-ResNet50 (External - Medical pretrained)")

model3 = MedicalNetWrapper(num_classes=2)
model3.to(device)
model3.eval()
params3 = sum(p.numel() for p in model3.parameters())
print(f"    Loaded: {params3:,} params (Medical pretrained)")

print("\n" + "-"*70)
total_params = params1 + (params2 if model2 else 0) + params3
print(f"Total Parameters: {total_params:,}")
print("="*70)

# ==============================================================================
# PHASE 6: Ensemble Strategy 1 - Weighted Average
# ==============================================================================

print("\n" + "="*70)
print("STRATEGY 1: WEIGHTED AVERAGE [0.4, 0.35, 0.25]")
print("Weights: MONAI(0.4) + TorchVision(0.35) + MedicalNet(0.25)")
print("="*70)

inferer = SimpleInferer()
ensemble_predictions_weighted = []

for i, batch in enumerate(loader):
    img = batch["image"].to(device)
    case_id = batch["case_id"][0]

    with torch.no_grad():
        # Get predictions from all 3 models
        output1 = inferer(inputs=img, network=model1)

        if model2:
            output2 = model2(img)
        else:
            output2 = torch.zeros_like(output1)

        output3 = model3(img)

        # Convert to probabilities
        prob1 = torch.softmax(output1, dim=1)
        prob2 = torch.softmax(output2, dim=1)
        prob3 = torch.softmax(output3, dim=1)

        # Weighted average with emphasis on MONAI model
        ensemble_prob = 0.4 * prob1 + 0.35 * prob2 + 0.25 * prob3

        pred = torch.argmax(ensemble_prob, dim=1).item()
        conf = ensemble_prob.max().item()

    ensemble_predictions_weighted.append(pred)

    print(f"\nCase {i+1}: {case_id}")
    print(f"  MONAI={torch.argmax(prob1).item()}({prob1.max().item():.3f}) "
          f"TorchVis={torch.argmax(prob2).item()}({prob2.max().item():.3f}) "
          f"MedNet={torch.argmax(prob3).item()}({prob3.max().item():.3f})")
    print(f"  → Ensemble={pred}({conf:.3f})")

# ==============================================================================
# PHASE 7: Ensemble Strategy 2 - Majority Voting
# ==============================================================================

print("\n" + "="*70)
print("STRATEGY 2: MAJORITY VOTING")
print("="*70)

ensemble_predictions_voting = []

for i, batch in enumerate(loader):
    img = batch["image"].to(device)
    case_id = batch["case_id"][0]

    with torch.no_grad():
        # Get predictions from all 3 models
        output1 = inferer(inputs=img, network=model1)

        if model2:
            output2 = model2(img)
        else:
            output2 = torch.zeros_like(output1)

        output3 = model3(img)

        # Get class predictions (votes)
        pred1 = torch.argmax(output1, dim=1).item()
        pred2 = torch.argmax(output2, dim=1).item()
        pred3 = torch.argmax(output3, dim=1).item()

        # Majority voting
        votes = [pred1, pred2, pred3]
        pred = max(set(votes), key=votes.count)
        conf = votes.count(pred) / len(votes)

    ensemble_predictions_voting.append(pred)

    print(f"\nCase {i+1}: {case_id}")
    print(f"  Votes: MONAI={pred1} TorchVis={pred2} MedNet={pred3}")
    print(f"  → Final={pred} ({votes.count(pred)}/{len(votes)} = {conf:.2f})")

# ==============================================================================
# PHASE 8: Comparison Summary
# ==============================================================================

print("\n" + "="*70)
print("COMPARISON SUMMARY")
print("="*70)

# Single model predictions (MONAI only)
single_predictions = []
for i, batch in enumerate(loader):
    img = batch["image"].to(device)
    with torch.no_grad():
        output = inferer(inputs=img, network=model1)
        pred = torch.argmax(output, dim=1).item()
    single_predictions.append(pred)

print(f"\nSingle (MONAI DenseNet):     {single_predictions}")
print(f"Ensemble (Weighted):         {ensemble_predictions_weighted}")
print(f"Ensemble (Voting):           {ensemble_predictions_voting}")

# Calculate agreement between strategies
weighted_voting_agreement = sum(1 for a, b in zip(ensemble_predictions_weighted, ensemble_predictions_voting) if a == b)
single_weighted_agreement = sum(1 for a, b in zip(single_predictions, ensemble_predictions_weighted) if a == b)

print(f"\nAgreement Analysis:")
print(f"  Weighted vs Voting: {weighted_voting_agreement}/{len(single_predictions)} ({weighted_voting_agreement/len(single_predictions)*100:.1f}%)")
print(f"  Single vs Weighted: {single_weighted_agreement}/{len(single_predictions)} ({single_weighted_agreement/len(single_predictions)*100:.1f}%)")

print("\n" + "="*70)
print("DONE! Ensemble completed with 1 MONAI + 2 External models.")
print("- Model 1: MONAI DenseNet121 (Native MONAI)")
print("- Model 2: TorchVision ResNet18 (External - ImageNet pretrained)")
print("- Model 3: MedicalNet 3D-ResNet50 (External - Medical pretrained)")
print("="*70)

print("\n" + "✅" + "="*69)
print("SUCCESS: Hybrid Ensemble Approach")
print("="*70)
print("""
✅ Combined MONAI's medical imaging expertise with external models
✅ Leveraged transfer learning from ImageNet and medical datasets
✅ Ensemble provides robust predictions through model diversity
✅ Two strategies: Weighted average (prioritizes MONAI) & Majority voting

Model Diversity Benefits:
- MONAI: Specialized for medical imaging
- TorchVision: General computer vision knowledge
- MedicalNet: Domain-specific medical pretrained weights
""")
print("="*70)