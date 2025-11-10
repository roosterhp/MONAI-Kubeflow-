"""
Option 1: Direct Replacement
=============================

Thay thế trực tiếp MONAI model bằng external model mà KHÔNG CẦN wrapper.

Khi nào dùng:
- Model external đã là torch.nn.Module
- Input/output shape tương thích sẵn
- Model đã được train trên medical data

Ưu điểm:
- Đơn giản nhất (5-10 dòng code)
- Không cần viết wrapper
- Giữ nguyên toàn bộ MONAI pipeline

Nhược điểm:
- Yêu cầu model phải compatible sẵn
- Input shape phải khớp (1 channel cho CT)
"""

import torch
import torch.nn as nn
from pathlib import Path
import numpy as np

from monai.data import Dataset, DataLoader
from monai.transforms import (
    Compose,
    LoadImaged,
    EnsureChannelFirstd,
    Orientationd,
    Spacingd,
    ScaleIntensityRanged,
    ResizeWithPadOrCropd,
)
from monai.inferers import SimpleInferer
from monai.networks.nets import DenseNet121

print("\n" + "="*70)
print("OPTION 1: DIRECT REPLACEMENT")
print("="*70)

# ============================================================================
# Data Loading
# ============================================================================

def get_real_data():
    """Load real CT scans from Task06_Lung dataset"""
    possible_paths = [
        Path("../hospital-mlops/demo/sample-data/Task06_Lung/imagesTr"),
        Path("../../hospital-mlops/demo/sample-data/Task06_Lung/imagesTr"),
    ]

    data_dir = None
    for path in possible_paths:
        if path.exists():
            data_dir = path
            break

    if data_dir is None:
        print("[!] Data not found")
        return None

    ct_files = sorted(list(data_dir.glob("lung_*.nii.gz")))[:3]
    ct_files = [f for f in ct_files if not f.name.startswith("._")]

    np.random.seed(42)
    labels = np.random.randint(0, 2, len(ct_files))

    return [{"image": str(f), "label": int(l), "case_id": f.stem}
            for f, l in zip(ct_files, labels)]

print("\nLoading data...")
data_dicts = get_real_data()

if not data_dicts:
    print("Skipping - no data")
    exit(0)

print(f"[OK] Loaded {len(data_dicts)} CT scans")

# ============================================================================
# MONAI Transforms (Giữ nguyên cho cả 2 cases)
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
# BEFORE: MONAI Model (Baseline)
# ============================================================================

print("\n" + "="*70)
print("BEFORE: MONAI DenseNet121 (Baseline)")
print("="*70)

monai_model = DenseNet121(
    spatial_dims=3,
    in_channels=1,  # CT grayscale
    out_channels=2  # Binary classification
)
monai_model.eval()

print(f"Model: MONAI DenseNet121")
print(f"Parameters: {sum(p.numel() for p in monai_model.parameters()):,}")
print(f"Source: monai.networks.nets")
print(f"Expected accuracy: 82-85%")

# Inference
inferer = SimpleInferer()
monai_predictions = []

print("\nRunning inference...")
for i, batch in enumerate(loader):
    img = batch["image"]
    label = batch["label"].item()

    with torch.no_grad():
        output = inferer(inputs=img, network=monai_model)
        pred = torch.argmax(output, dim=1).item()
        conf = torch.softmax(output, dim=1).max().item()

    monai_predictions.append(pred)
    print(f"   {i+1}. {batch['case_id'][0]}: Pred={pred} (conf={conf:.3f}), Label={label}")

# ============================================================================
# AFTER: External Model (Direct Replacement)
# ============================================================================

print("\n" + "="*70)
print("AFTER: External Model (Direct Replacement)")
print("="*70)

# Custom external model that is ALREADY COMPATIBLE
# (trong thực tế: load từ research paper, GitHub, Hugging Face)
class ExternalCompatibleModel(nn.Module):
    """
    External model đã được train trên medical CT data
    Input: (B, 1, D, H, W) - 3D CT grayscale
    Output: (B, num_classes) - Classification logits

    Trong thực tế, model này từ:
    - Research paper weights
    - Pre-trained từ medical dataset khác
    - GitHub repository
    - Hugging Face model hub
    """
    def __init__(self, in_channels=1, out_channels=2):
        super().__init__()

        # Architecture tương tự medical models
        self.features = nn.Sequential(
            nn.Conv3d(in_channels, 32, kernel_size=3, padding=1),
            nn.BatchNorm3d(32),
            nn.ReLU(inplace=True),
            nn.MaxPool3d(2),

            nn.Conv3d(32, 64, kernel_size=3, padding=1),
            nn.BatchNorm3d(64),
            nn.ReLU(inplace=True),
            nn.MaxPool3d(2),

            nn.Conv3d(64, 128, kernel_size=3, padding=1),
            nn.BatchNorm3d(128),
            nn.ReLU(inplace=True),
            nn.AdaptiveAvgPool3d(1),
        )

        self.classifier = nn.Sequential(
            nn.Flatten(),
            nn.Linear(128, 64),
            nn.ReLU(inplace=True),
            nn.Dropout(0.5),
            nn.Linear(64, out_channels)
        )

    def forward(self, x):
        x = self.features(x)
        x = self.classifier(x)
        return x

# Load external model
external_model = ExternalCompatibleModel(in_channels=1, out_channels=2)

# Trong thực tế: load pretrained weights
# external_model.load_state_dict(torch.load("external_weights_95acc.pth"))

external_model.eval()

print(f"Model: External Compatible Model")
print(f"Parameters: {sum(p.numel() for p in external_model.parameters()):,}")
print(f"Source: External (research paper/GitHub/Hugging Face)")
print(f"Input: (B, 1, D, H, W) - SameĐÃ compatible!")
print(f"Expected accuracy: 90-95% (after loading real weights)")

# KEY POINT: Dùng SAME inferer, SAME transforms, SAME DataLoader
# CHỈ THAY MODEL!
print("\n[OK] Using SAME MONAI inferer (SimpleInferer)")
print("[OK] Using SAME MONAI transforms")
print("[OK] Using SAME MONAI DataLoader")
print("\n[!] ONLY CHANGE: The model!")

external_predictions = []

print("\nRunning inference with external model...")
for i, batch in enumerate(loader):
    img = batch["image"]
    label = batch["label"].item()

    with torch.no_grad():
        # Same inferer, different model!
        output = inferer(inputs=img, network=external_model)
        pred = torch.argmax(output, dim=1).item()
        conf = torch.softmax(output, dim=1).max().item()

    external_predictions.append(pred)
    print(f"   {i+1}. {batch['case_id'][0]}: Pred={pred} (conf={conf:.3f}), Label={label}")

# ============================================================================
# Comparison
# ============================================================================

print("\n" + "="*70)
print("COMPARISON: BEFORE vs AFTER")
print("="*70)

print(f"\n{'Aspect':<30} {'BEFORE (MONAI)':<25} {'AFTER (External)':<25}")
print("-" * 80)
print(f"{'Model Source':<30} {'monai.networks.nets':<25} {'External (compatible)':<25}")
print(f"{'Parameters':<30} {sum(p.numel() for p in monai_model.parameters()):<25,} {sum(p.numel() for p in external_model.parameters()):<25,}")
print(f"{'Input compatible':<30} {'[OK] 3D CT':<25} {'[OK] 3D CT (same!)':<25}")
print(f"{'MONAI Transforms':<30} {'[OK] Used':<25} {'[OK] Same transforms':<25}")
print(f"{'MONAI Inferer':<30} {'[OK] SimpleInferer':<25} {'[OK] Same inferer':<25}")
print(f"{'Code changes':<30} {'-':<25} {'~5 dòng (chỉ thay model)':<25}")
print(f"{'Expected Accuracy':<30} {'82-85%':<25} {'90-95% (+10%)':<25}")

# ============================================================================
# Key Takeaways
# ============================================================================

print("\n" + "="*70)
print("KEY TAKEAWAYS - OPTION 1: DIRECT REPLACEMENT")
print("="*70)

print("""
Option 1 là phương pháp ĐƠN GIẢN NHẤT khi:
-----------------------------------------

[OK] Điều kiện cần:
   1. External model đã là torch.nn.Module
   2. Input shape đã compatible (1 channel cho CT)
   3. Output shape khớp (num_classes)
   4. Model đã train trên medical data tương tự

[OK] Ưu điểm:
   1. Đơn giản nhất - chỉ 5 dòng code thay đổi
   2. Không cần wrapper hoặc adapter
   3. Giữ nguyên 100% MONAI infrastructure
   4. Nhanh - không có overhead

[X] Nhược điểm:
   1. Model phải compatible sẵn (khó tìm)
   2. Input shape phải khớp (1 channel, 3D)
   3. Không tận dụng pretrained ImageNet weights

Code thay đổi:
--------------
BEFORE:
    from monai.networks.nets import DenseNet121
    model = DenseNet121(spatial_dims=3, in_channels=1, out_channels=2)

AFTER:
    from your_model import BetterModel  # External model
    model = BetterModel()
    model.load_state_dict(torch.load("weights.pth"))

    # That's it! GIỮ NGUYÊN transforms, DataLoader, inferer

Khi nào dùng Option 1:
----------------------
- Bạn có external model ĐÃ train trên medical CT data
- Model đã có input/output shape phù hợp
- Muốn giải pháp đơn giản nhất

Khi nào KHÔNG dùng Option 1:
----------------------------
- Model pretrained trên ImageNet (3 channels RGB) → Dùng Option 2
- Model output shape khác → Cần modify hoặc dùng Option 2
- Muốn ensemble nhiều models → Dùng Option 3
""")

print("="*70)
print("[OK] DEMO COMPLETED - OPTION 1")
print("="*70)
