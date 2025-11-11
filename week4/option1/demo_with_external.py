"""
MedicalNet 3D-ResNet50 (Tencent)
NOTE: Without pretrained weights, accuracy will be SAME or WORSE than baseline!
"""

import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import torch
from pathlib import Path
from monai.data import Dataset, DataLoader
from monai.transforms import (
    Compose, LoadImaged, EnsureChannelFirstd, Orientationd,
    Spacingd, ScaleIntensityRanged, ResizeWithPadOrCropd,
)
from monai.inferers import SimpleInferer

# ============================================================================
# PHASE 1: Setup and Data Loading
# ============================================================================

print("\n" + "="*70)
print("MEDICALNET 3D-RESNET50 (Untrained - No Improvement Expected!)")
print("="*70)

def get_real_data():
    """Load real CT scans from Task06_Lung dataset"""
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

# ============================================================================
# PHASE 2: MONAI Transforms (same as baseline)
# ============================================================================

transforms = Compose([
    LoadImaged(keys=["image"]),
    EnsureChannelFirstd(keys=["image"]),
    Orientationd(keys=["image"], axcodes="RAS"),
    Spacingd(keys=["image"], pixdim=(1.5, 1.5, 2.0), mode="bilinear"),
    ScaleIntensityRanged(keys=["image"], a_min=-1000, a_max=500, b_min=0, b_max=1, clip=True),
    ResizeWithPadOrCropd(keys=["image"], spatial_size=(96, 96, 96)),
])

dataset = Dataset(data=data_dicts, transform=transforms)
loader = DataLoader(dataset, batch_size=1, num_workers=0)

# ============================================================================
# PHASE 3: External Model (MedicalNet 3D-ResNet50) - KEY DIFFERENCE
# NOTE: Using external model instead of MONAI built-in
# ============================================================================

from models.medicalnet_resnet import resnet50_medicalnet

model = resnet50_medicalnet(num_classes=2, pretrained=True)
model.eval()

params = sum(p.numel() for p in model.parameters())
print(f"\nModel: MedicalNet 3D-ResNet50")
print(f"Parameters: {params:,}")
print(f"Pretrained: No weights (random init)")
print(f"WARNING: Without pretrained weights, performance = baseline or worse!")

# ============================================================================
# PHASE 4: Inference - Using SAME MONAI inferer with DIFFERENT model
# ============================================================================

inferer = SimpleInferer()
predictions = []
confidences = []
for i, batch in enumerate(loader):
    img = batch["image"]
    case_id = batch["case_id"][0]

    with torch.no_grad():
        // KEY: Same MONAI inferer, different (external) model!
        output = inferer(inputs=img, network=model)
        pred = torch.argmax(output, dim=1).item()
        conf = torch.softmax(output, dim=1).max().item()

    predictions.append(pred)
    confidences.append(conf)
    print(f"  {i+1}. {case_id}: Pred={pred} (conf={conf:.3f})")

avg_confidence = sum(confidences) / len(confidences)

print("\n" + "="*70)
print(f"RESULTS - Avg Confidence: {avg_confidence:.3f} (random, untrained)")
print("="*70)
print("\nNOTE: To see improvement, download pretrained weights:")
print("  1. Visit: https://github.com/Tencent/MedicalNet")
print("  2. Download: resnet_50_23dataset.pth")
print("  3. Place at: pretrained_weights/medicalnet/resnet_50_23dataset.pth")
print("  4. Expected: 87-93% accuracy (vs 50-60% random)")
print("="*70)
