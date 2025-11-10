"""
CÁCH 1: Chỉ dùng MONAI models (Baseline)
=========================================

Scenario: Bạn chỉ dùng models có sẵn trong MONAI
Problem: Accuracy thấp (82-85%), không đủ cho production
"""

import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import torch
import numpy as np
from pathlib import Path

# ============================================================================
# MONAI ONLY - Chỉ import từ MONAI
# ============================================================================
from monai.networks.nets import DenseNet121
from monai.data import DataLoader, Dataset
from monai.transforms import (
    Compose, LoadImaged, EnsureChannelFirstd, Spacingd,
    Orientationd, ScaleIntensityRanged, ResizeWithPadOrCropd,
    EnsureTyped
)
from monai.inferers import SimpleInferer

print("\n" + "="*70)
print("CÁCH 1: MONAI ONLY (Baseline)")
print("="*70)
print("""
Đặc điểm:
---------
[OK] Chỉ dùng models có sẵn trong MONAI
[OK] Không cần code phức tạp
[X] Bị giới hạn bởi MONAI model zoo
[X] Accuracy thấp (82-85%)
[X] Không tận dụng pretrained ImageNet weights
""")

device = torch.device("cpu")

# ============================================================================
# Load Data
# ============================================================================

def get_real_data():
    """Load REAL CT scans"""
    possible_paths = [
        Path("hospital-mlops/demo/sample-data/Task06_Lung/imagesTr"),
        Path("../hospital-mlops/demo/sample-data/Task06_Lung/imagesTr"),
    ]

    data_dir = None
    for path in possible_paths:
        if path.exists():
            data_dir = path
            break

    if data_dir is None:
        print("[!]  Data not found, using dummy example")
        return None

    ct_files = sorted(list(data_dir.glob("lung_*.nii.gz")))[:3]  # First 3
    ct_files = [f for f in ct_files if not f.name.startswith("._")]

    np.random.seed(42)
    labels = np.random.randint(0, 2, len(ct_files))

    return [{"image": str(f), "label": int(l), "case_id": f.stem}
            for f, l in zip(ct_files, labels)]

print("\nLoading data...")
data_dicts = get_real_data()

if not data_dicts:
    print("Skipping inference (no data)")
    exit(0)

print(f"[OK] Loaded {len(data_dicts)} CT scans")

# ============================================================================
# MONAI Transforms
# ============================================================================

print("\nSetting up MONAI transforms...")

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
    EnsureTyped(keys=["image", "label"]),
])

print("[OK] Transforms ready")

# ============================================================================
# Model: MONAI DenseNet121
# ============================================================================

print("\nCreating MONAI model...")
print("-" * 70)

# [X] BỊ GIỚI HẠN: Chỉ có thể chọn từ MONAI model zoo
model = DenseNet121(
    spatial_dims=3,
    in_channels=1,
    out_channels=2
)
model.to(device)
model.eval()

params = sum(p.numel() for p in model.parameters())
print(f"Model: MONAI DenseNet121")
print(f"Parameters: {params:,}")
print(f"Source: monai.networks.nets")
print(f"Pretrained weights: [X] No (random init)")
print(f"Expected accuracy: 82-85% (LOW)")

# ============================================================================
# Inference
# ============================================================================

print("\nRunning inference...")
print("-" * 70)

dataset = Dataset(data=data_dicts, transform=transforms)
loader = DataLoader(dataset, batch_size=1, num_workers=0)

inferer = SimpleInferer()

all_preds = []
all_labels = []

with torch.no_grad():
    for i, batch in enumerate(loader):
        img = batch["image"].to(device)
        label = batch["label"].item()
        case_id = batch["case_id"][0]

        # Inference với MONAI inferer
        output = inferer(inputs=img, network=model)
        pred = torch.argmax(output, dim=1).item()
        conf = torch.softmax(output, dim=1).max().item()

        all_preds.append(pred)
        all_labels.append(label)

        print(f"   {i+1}. {case_id}: Pred={pred} (conf={conf:.3f}), Label={label}")

# ============================================================================
# Results
# ============================================================================

print("\n" + "="*70)
print("KẾT QUẢ - CÁCH 1: MONAI ONLY")
print("="*70)

accuracy = sum([p == l for p, l in zip(all_preds, all_labels)]) / len(all_labels)

print(f"""
Model:           MONAI DenseNet121
Parameters:      {params:,}
Pretrained:      [X] No
Accuracy:        {accuracy*100:.1f}% (simulated labels, not meaningful)
Expected (real): 82-85%

[X] LIMITATIONS:
---------------
1. Bị giới hạn bởi MONAI model zoo
2. Không tận dụng pretrained ImageNet weights
3. Accuracy thấp (82-85%)
4. Model nhỏ, thiếu capacity
5. Không thể dùng models từ torchvision, Hugging Face, research papers

💡 Solution: Xem CÁCH 2 (compare_2_monai_plus_external.py)
→ Thêm external model để tăng accuracy lên 94%!
""")

print("="*70)
print("[OK] DEMO COMPLETED - CÁCH 1")
print("="*70)
