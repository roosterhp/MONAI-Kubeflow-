"""
Script để chuẩn bị dữ liệu custom cho fine-tuning

Giả sử bạn có:
- CT scans (.nii.gz hoặc DICOM)
- Annotations (masks hoặc labels)

Script này sẽ:
1. Convert DICOM → NIfTI (nếu cần)
2. Organize data theo structure MONAI
3. Create train/val split
4. Validate data quality

Expected Output Structure:
data/covid_custom/
  train/
    images/
      patient001.nii.gz
      patient002.nii.gz
    masks/
      patient001_mask.nii.gz  (4 classes: 0=bg, 1=normal, 2=GGO, 3=consolidation)
      patient002_mask.nii.gz
  val/
    images/
    masks/
"""

import os
import shutil
import SimpleITK as sitk
import numpy as np
from pathlib import Path
from typing import List, Dict
import json


class DataPreparator:
    """
    Prepare custom data for MONAI fine-tuning
    """

    def __init__(self, raw_data_dir: str, output_dir: str):
        """
        Args:
            raw_data_dir: Directory containing raw data
            output_dir: Output directory for processed data
        """
        self.raw_data_dir = Path(raw_data_dir)
        self.output_dir = Path(output_dir)

        # Create output structure
        self.train_images_dir = self.output_dir / "train" / "images"
        self.train_masks_dir = self.output_dir / "train" / "masks"
        self.val_images_dir = self.output_dir / "val" / "images"
        self.val_masks_dir = self.output_dir / "val" / "masks"

        for d in [self.train_images_dir, self.train_masks_dir,
                  self.val_images_dir, self.val_masks_dir]:
            d.mkdir(parents=True, exist_ok=True)

        print(f"[INFO] Output directory created: {self.output_dir}")

    def convert_dicom_to_nifti(self, dicom_dir: Path, output_path: Path):
        """
        Convert DICOM series to NIfTI

        Args:
            dicom_dir: Directory containing DICOM files
            output_path: Output NIfTI file path
        """
        print(f"[INFO] Converting DICOM: {dicom_dir.name}")

        try:
            # Read DICOM series
            reader = sitk.ImageSeriesReader()
            dicom_names = reader.GetGDCMSeriesFileNames(str(dicom_dir))
            reader.SetFileNames(dicom_names)
            image = reader.Execute()

            # Save as NIfTI
            sitk.WriteImage(image, str(output_path))
            print(f"[OK] Saved: {output_path.name}")

        except Exception as e:
            print(f"[ERROR] Failed to convert {dicom_dir.name}: {e}")

    def create_dummy_mask(
        self,
        image_path: Path,
        output_path: Path,
        lesion_percentage: float = 0.2
    ):
        """
        Create dummy mask for testing (replace with your actual annotation pipeline)

        Args:
            image_path: Path to CT image
            output_path: Output mask path
            lesion_percentage: Percentage of lung to mark as lesion
        """
        print(f"[INFO] Creating dummy mask for: {image_path.name}")

        # Load image
        image = sitk.ReadImage(str(image_path))
        image_array = sitk.GetArrayFromImage(image)

        # Create mask (simplified)
        mask = np.ones_like(image_array, dtype=np.uint8)  # 1 = normal lung

        # Simulate some GGO (class 2)
        lung_voxels = (image_array > -800) & (image_array < -400)
        ggo_candidates = lung_voxels & ((image_array > -700) & (image_array < -500))

        # Random sample of GGO
        num_ggo = int(ggo_candidates.sum() * lesion_percentage)
        ggo_indices = np.where(ggo_candidates)
        if len(ggo_indices[0]) > 0:
            selected = np.random.choice(len(ggo_indices[0]), size=min(num_ggo, len(ggo_indices[0])), replace=False)
            mask[ggo_indices[0][selected], ggo_indices[1][selected], ggo_indices[2][selected]] = 2

        # Simulate some consolidation (class 3) - less common
        consolidation_candidates = lung_voxels & (image_array > -300)
        num_cons = int(consolidation_candidates.sum() * lesion_percentage * 0.3)
        cons_indices = np.where(consolidation_candidates)
        if len(cons_indices[0]) > 0:
            selected = np.random.choice(len(cons_indices[0]), size=min(num_cons, len(cons_indices[0])), replace=False)
            mask[cons_indices[0][selected], cons_indices[1][selected], cons_indices[2][selected]] = 3

        # Background
        mask[~lung_voxels] = 0

        # Save mask
        mask_image = sitk.GetImageFromArray(mask)
        mask_image.CopyInformation(image)
        sitk.WriteImage(mask_image, str(output_path))

        print(f"[OK] Mask saved: {output_path.name}")
        print(f"  Classes: BG={np.sum(mask==0)}, Normal={np.sum(mask==1)}, GGO={np.sum(mask==2)}, Cons={np.sum(mask==3)}")

    def process_nifti_files(
        self,
        image_files: List[Path],
        train_ratio: float = 0.8
    ):
        """
        Process NIfTI files and split into train/val

        Args:
            image_files: List of image file paths
            train_ratio: Train/val split ratio
        """
        print(f"\n[INFO] Processing {len(image_files)} files...")

        # Split train/val
        split_idx = int(len(image_files) * train_ratio)
        train_files = image_files[:split_idx]
        val_files = image_files[split_idx:]

        print(f"[INFO] Train: {len(train_files)}, Val: {len(val_files)}")

        # Process training files
        print("\n[TRAIN] Processing training files...")
        for img_file in train_files:
            # Copy image
            output_img = self.train_images_dir / img_file.name
            shutil.copy(img_file, output_img)

            # Create/copy mask
            mask_name = img_file.stem + "_mask.nii.gz"
            output_mask = self.train_masks_dir / mask_name

            # Check if mask exists
            mask_file = img_file.parent / mask_name
            if mask_file.exists():
                shutil.copy(mask_file, output_mask)
                print(f"[OK] Copied: {img_file.name} + mask")
            else:
                # Create dummy mask
                self.create_dummy_mask(img_file, output_mask)

        # Process validation files
        print("\n[VAL] Processing validation files...")
        for img_file in val_files:
            output_img = self.val_images_dir / img_file.name
            shutil.copy(img_file, output_img)

            mask_name = img_file.stem + "_mask.nii.gz"
            output_mask = self.val_masks_dir / mask_name

            mask_file = img_file.parent / mask_name
            if mask_file.exists():
                shutil.copy(mask_file, output_mask)
                print(f"[OK] Copied: {img_file.name} + mask")
            else:
                self.create_dummy_mask(img_file, output_mask)

        print("\n[OK] Data preparation complete!")

    def validate_data(self):
        """
        Validate prepared data
        """
        print("\n" + "="*60)
        print("DATA VALIDATION")
        print("="*60)

        # Check train data
        train_images = list(self.train_images_dir.glob("*.nii.gz"))
        train_masks = list(self.train_masks_dir.glob("*.nii.gz"))

        print(f"\n[TRAIN]")
        print(f"  Images: {len(train_images)}")
        print(f"  Masks:  {len(train_masks)}")

        if len(train_images) != len(train_masks):
            print(f"  [WARNING] Image/mask count mismatch!")

        # Check val data
        val_images = list(self.val_images_dir.glob("*.nii.gz"))
        val_masks = list(self.val_masks_dir.glob("*.nii.gz"))

        print(f"\n[VAL]")
        print(f"  Images: {len(val_images)}")
        print(f"  Masks:  {len(val_masks)}")

        if len(val_images) != len(val_masks):
            print(f"  [WARNING] Image/mask count mismatch!")

        # Sample validation
        print(f"\n[SAMPLE CHECK]")
        if len(train_images) > 0:
            sample_img = sitk.ReadImage(str(train_images[0]))
            sample_mask = sitk.ReadImage(str(train_masks[0]))

            print(f"  Image shape: {sitk.GetArrayFromImage(sample_img).shape}")
            print(f"  Mask shape:  {sitk.GetArrayFromImage(sample_mask).shape}")
            print(f"  Image spacing: {sample_img.GetSpacing()}")
            print(f"  Mask spacing:  {sample_mask.GetSpacing()}")

            mask_array = sitk.GetArrayFromImage(sample_mask)
            unique_classes = np.unique(mask_array)
            print(f"  Mask classes: {unique_classes}")

        print("\n" + "="*60)

        # Save dataset info
        dataset_info = {
            "train_samples": len(train_images),
            "val_samples": len(val_images),
            "total_samples": len(train_images) + len(val_images),
            "classes": {
                "0": "Background",
                "1": "Normal lung tissue",
                "2": "Ground-Glass Opacity (GGO)",
                "3": "Consolidation"
            },
            "data_structure": {
                "train_images": str(self.train_images_dir),
                "train_masks": str(self.train_masks_dir),
                "val_images": str(self.val_images_dir),
                "val_masks": str(self.val_masks_dir),
            }
        }

        info_path = self.output_dir / "dataset_info.json"
        with open(info_path, "w") as f:
            json.dump(dataset_info, f, indent=2)

        print(f"[OK] Dataset info saved: {info_path}")


def main():
    """
    Example usage
    """
    print("\n" + "="*70)
    print("CUSTOM DATA PREPARATION FOR FINE-TUNING")
    print("="*70)

    # ===== OPTION 1: Process existing NIfTI files =====
    # Uncomment if you already have .nii.gz files
    """
    preparator = DataPreparator(
        raw_data_dir="./raw_data/ct_scans",
        output_dir="./data/covid_custom"
    )

    # Find all NIfTI files
    nifti_files = list(Path("./raw_data/ct_scans").glob("*.nii.gz"))
    print(f"[INFO] Found {len(nifti_files)} NIfTI files")

    # Process and split
    preparator.process_nifti_files(nifti_files, train_ratio=0.8)

    # Validate
    preparator.validate_data()
    """

    # ===== OPTION 2: Convert DICOM to NIfTI first =====
    # Uncomment if you have DICOM files
    """
    preparator = DataPreparator(
        raw_data_dir="./raw_data/dicom",
        output_dir="./data/covid_custom"
    )

    # Find DICOM series folders
    dicom_series = [d for d in Path("./raw_data/dicom").iterdir() if d.is_dir()]
    print(f"[INFO] Found {len(dicom_series)} DICOM series")

    # Convert each series
    converted_files = []
    for dicom_dir in dicom_series:
        output_path = Path("./raw_data/converted") / f"{dicom_dir.name}.nii.gz"
        output_path.parent.mkdir(parents=True, exist_ok=True)

        preparator.convert_dicom_to_nifti(dicom_dir, output_path)
        converted_files.append(output_path)

    # Process converted files
    preparator.process_nifti_files(converted_files, train_ratio=0.8)
    preparator.validate_data()
    """

    # ===== DEMO: Create synthetic data for testing =====
    print("\n[DEMO] Creating synthetic demo data...")
    print("(Replace this with your actual data preparation)")

    # Use existing sample data as demo
    sample_data = Path("./sample-data/Task06_Lung/imagesTr")
    if sample_data.exists():
        preparator = DataPreparator(
            raw_data_dir=str(sample_data),
            output_dir="./data/covid_custom_demo"
        )

        # Take first 10 files
        nifti_files = sorted(list(sample_data.glob("*.nii.gz")))[:10]
        print(f"[INFO] Using {len(nifti_files)} sample files for demo")

        # Process
        preparator.process_nifti_files(nifti_files, train_ratio=0.8)
        preparator.validate_data()

        print("\n[OK] Demo data prepared!")
        print(f"[NEXT] Run fine-tuning: python finetune_covid_model.py")
    else:
        print("[INFO] No sample data found. Please specify your data directory.")


if __name__ == "__main__":
    main()
