"""
MONAI Baseline - DenseNet121 (untrained)
"""

import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import torch
from pathlib import Path
from monai.networks.nets import DenseNet121
from monai.data import DataLoader, Dataset
from monai.transforms import (
    Compose, LoadImaged, EnsureChannelFirstd, Spacingd,
    Orientationd, ScaleIntensityRanged, ResizeWithPadOrCropd,
    EnsureTyped
)
from monai.inferers import SimpleInferer

# ============================================================================
# PHASE 1: Setup and Data Loading
# ============================================================================

print("\n" + "="*70)
print("MONAI BASELINE (DenseNet121 - Untrained)")
print("="*70)

device = torch.device("cpu")

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

# ============================================================================
# PHASE 2: MONAI Transforms (Medical image preprocessing)
# ============================================================================

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

# ============================================================================
# PHASE 3: Model Setup - MONAI DenseNet121 (untrained baseline)
# ============================================================================

model = DenseNet121(spatial_dims=3, in_channels=1, out_channels=2)
model.to(device)
model.eval()

params = sum(p.numel() for p in model.parameters())
print(f"\nModel: MONAI DenseNet121")
print(f"Parameters: {params:,}")
print(f"Pretrained: No (random init)")

# ============================================================================
# PHASE 4: Inference with MONAI SimpleInferer
# ============================================================================

dataset = Dataset(data=data_dicts, transform=transforms)
loader = DataLoader(dataset, batch_size=1, num_workers=0)

inferer = SimpleInferer()

all_preds = []
all_confs = []

with torch.no_grad():
    for i, batch in enumerate(loader):
        img = batch["image"].to(device)
        case_id = batch["case_id"][0]

        output = inferer(inputs=img, network=model)
        pred = torch.argmax(output, dim=1).item()
        conf = torch.softmax(output, dim=1).max().item()

        all_preds.append(pred)
        all_confs.append(conf)

        print(f"  {i+1}. {case_id}: Pred={pred} (conf={conf:.3f})")

avg_confidence = sum(all_confs) / len(all_confs)

print("\n" + "="*70)
print(f"RESULTS - Avg Confidence: {avg_confidence:.3f} (random, untrained)")
print("="*70)
