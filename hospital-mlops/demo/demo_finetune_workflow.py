"""
DEMO Fine-tuning Workflow - Không cần dữ liệu riêng

Script này sẽ:
1. Sử dụng sample data có sẵn (Task06_Lung)
2. Tạo synthetic labels để simulate fine-tuning
3. Chạy mini fine-tuning loop (5 epochs)
4. Demonstrate complete workflow

Mục đích: Hiểu workflow trước khi có dữ liệu thật
"""

import torch
import numpy as np
from pathlib import Path
from lungmask import LMInferer

from monai.transforms import (
    Compose, LoadImaged, EnsureChannelFirstd,
    ScaleIntensityRanged, RandCropByPosNegLabeld,
    EnsureTyped
)
from monai.data import CacheDataset, DataLoader
from monai.networks.nets import UNet
from monai.losses import DiceCELoss
from monai.utils import set_determinism


def create_synthetic_covid_labels(ct_array, lung_mask_array):
    """
    Tạo synthetic COVID labels từ CT + lung mask
    (Simulate what annotators would do)

    Args:
        ct_array: CT scan (D, H, W)
        lung_mask_array: Lung mask (D, H, W)

    Returns:
        synthetic_label: 4-class mask (D, H, W)
            0 = Background
            1 = Normal lung
            2 = GGO (Ground-Glass Opacity)
            3 = Consolidation
    """
    # Initialize: all normal lung tissue
    label = np.ones_like(ct_array, dtype=np.uint8)

    # Background (outside lungs)
    label[lung_mask_array == 0] = 0

    # GGO: HU between -700 and -500
    ggo_mask = ((ct_array > -700) & (ct_array <= -500)) & (lung_mask_array > 0)
    label[ggo_mask] = 2

    # Consolidation: HU > -300
    cons_mask = (ct_array > -300) & (lung_mask_array > 0)
    label[cons_mask] = 3

    return label


def demo_fine_tuning():
    """
    Demo fine-tuning workflow với sample data
    """
    print("\n" + "="*70)
    print("DEMO: FINE-TUNING WORKFLOW")
    print("Using sample data - No custom data required")
    print("="*70)

    # Set seed
    set_determinism(seed=42)

    # Device
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"\n[INFO] Device: {device}")

    # ========== STEP 1: Prepare Demo Data ==========
    print("\n[STEP 1] Preparing demo data...")

    sample_data = Path("./sample-data/Task06_Lung/imagesTr")
    if not sample_data.exists():
        print("[ERROR] Sample data not found!")
        print("Please download sample data first (see README.md)")
        return

    # Get first 6 files (3 train, 3 val)
    image_files = sorted([f for f in sample_data.glob("*.nii.gz") if not f.name.startswith("._")])[:6]
    print(f"[INFO] Found {len(image_files)} sample files")

    # Create synthetic labels using LungMask
    print("\n[INFO] Creating synthetic COVID labels...")
    print("(In real scenario, these would be manual annotations)")

    output_dir = Path("./demo_data")
    output_dir.mkdir(exist_ok=True)

    train_images_dir = output_dir / "train" / "images"
    train_labels_dir = output_dir / "train" / "labels"
    val_images_dir = output_dir / "val" / "images"
    val_labels_dir = output_dir / "val" / "labels"

    for d in [train_images_dir, train_labels_dir, val_images_dir, val_labels_dir]:
        d.mkdir(parents=True, exist_ok=True)

    # Load LungMask for creating labels
    print("[INFO] Loading LungMask...")
    inferer = LMInferer(modelname='R231')

    import SimpleITK as sitk

    for idx, image_file in enumerate(image_files):
        print(f"\n[{idx+1}/{len(image_files)}] Processing {image_file.name}...")

        # Load CT
        ct_scan = sitk.ReadImage(str(image_file))
        ct_array = sitk.GetArrayFromImage(ct_scan)

        # Get lung mask
        lung_mask_array = inferer.apply(ct_scan)

        # Create synthetic label
        synthetic_label = create_synthetic_covid_labels(ct_array, lung_mask_array)

        # Save label
        label_image = sitk.GetImageFromArray(synthetic_label)
        label_image.CopyInformation(ct_scan)

        # Split train/val
        if idx < 3:
            # Train
            output_img = train_images_dir / image_file.name
            output_label = train_labels_dir / image_file.name.replace('.nii.gz', '_label.nii.gz')
        else:
            # Val
            output_img = val_images_dir / image_file.name
            output_label = val_labels_dir / image_file.name.replace('.nii.gz', '_label.nii.gz')

        # Copy image and save label
        import shutil
        shutil.copy(image_file, output_img)
        sitk.WriteImage(label_image, str(output_label))

        # Stats
        unique, counts = np.unique(synthetic_label, return_counts=True)
        print(f"  Label classes: {dict(zip(unique, counts))}")

    print("\n[OK] Demo data prepared!")
    print(f"  Train: {len(list(train_images_dir.glob('*.nii.gz')))} samples")
    print(f"  Val: {len(list(val_images_dir.glob('*.nii.gz')))} samples")

    # ========== STEP 2: Create Model ==========
    print("\n[STEP 2] Creating model...")

    model = UNet(
        spatial_dims=3,
        in_channels=1,
        out_channels=4,  # 4 classes
        channels=(16, 32, 64, 128),  # Smaller for demo
        strides=(2, 2, 2),
        num_res_units=2,
        norm="batch",
    ).to(device)

    print(f"[OK] Model created")
    trainable = sum(p.numel() for p in model.parameters())
    print(f"  Parameters: {trainable:,}")

    # ========== STEP 3: Prepare Dataloaders ==========
    print("\n[STEP 3] Preparing dataloaders...")

    # Train files
    train_images = sorted(list(train_images_dir.glob("*.nii.gz")))
    train_labels = sorted(list(train_labels_dir.glob("*.nii.gz")))
    train_files = [
        {"image": str(img), "label": str(lbl)}
        for img, lbl in zip(train_images, train_labels)
    ]

    # Val files
    val_images = sorted(list(val_images_dir.glob("*.nii.gz")))
    val_labels = sorted(list(val_labels_dir.glob("*.nii.gz")))
    val_files = [
        {"image": str(img), "label": str(lbl)}
        for img, lbl in zip(val_images, val_labels)
    ]

    # Transforms
    train_transforms = Compose([
        LoadImaged(keys=["image", "label"]),
        EnsureChannelFirstd(keys=["image", "label"]),
        ScaleIntensityRanged(keys=["image"], a_min=-1000, a_max=500, b_min=0, b_max=1, clip=True),
        RandCropByPosNegLabeld(
            keys=["image", "label"],
            label_key="label",
            spatial_size=(64, 64, 64),  # Small for demo
            pos=1,
            neg=1,
            num_samples=2,
        ),
        EnsureTyped(keys=["image", "label"]),
    ])

    # Datasets
    train_ds = CacheDataset(
        data=train_files,
        transform=train_transforms,
        cache_rate=1.0,
        num_workers=2,
    )

    train_loader = DataLoader(
        train_ds,
        batch_size=1,  # Small batch for demo
        shuffle=True,
        num_workers=0,  # Windows compatible
    )

    print(f"[OK] Dataloaders ready")
    print(f"  Train batches: {len(train_loader)}")

    # ========== STEP 4: Training Loop (Mini) ==========
    print("\n[STEP 4] Running mini training loop (5 epochs)...")
    print("(This is just a demo - real fine-tuning would be 50-100 epochs)")

    loss_function = DiceCELoss(
        include_background=False,
        to_onehot_y=True,
        softmax=True,
    )

    optimizer = torch.optim.Adam(model.parameters(), lr=1e-4)

    num_epochs = 5
    for epoch in range(num_epochs):
        model.train()
        epoch_loss = 0
        step = 0

        print(f"\n--- Epoch {epoch + 1}/{num_epochs} ---")

        for batch_data in train_loader:
            step += 1
            inputs = batch_data["image"].to(device)
            labels = batch_data["label"].to(device)

            optimizer.zero_grad()
            outputs = model(inputs)
            loss = loss_function(outputs, labels)
            loss.backward()
            optimizer.step()

            epoch_loss += loss.item()

            if step % 2 == 0:
                print(f"  Batch {step}: Loss = {loss.item():.4f}")

        epoch_loss /= step
        print(f"Epoch {epoch + 1} Average Loss: {epoch_loss:.4f}")

    # ========== STEP 5: Save Model ==========
    print("\n[STEP 5] Saving demo model...")

    output_model = output_dir / "demo_finetuned_model.pth"
    torch.save(model.state_dict(), output_model)
    print(f"[OK] Model saved: {output_model}")

    # ========== Summary ==========
    print("\n" + "="*70)
    print("DEMO COMPLETE!")
    print("="*70)
    print("\n✅ You have successfully run a fine-tuning demo!")
    print("\n📚 What you learned:")
    print("  1. How to prepare data (images + labels)")
    print("  2. How to create MONAI transforms")
    print("  3. How to setup training loop")
    print("  4. How to save fine-tuned model")
    print("\n🚀 Next steps:")
    print("  1. Collect your custom data (CT scans)")
    print("  2. Annotate your data (create ground truth masks)")
    print("  3. Use prepare_custom_data.py to organize data")
    print("  4. Run finetune_covid_model.py with your data")
    print("\n" + "="*70)


if __name__ == "__main__":
    demo_fine_tuning()
