"""
Setup script for COVID-19 Detection Pipeline
Prepares test data and environment
"""

import os
import shutil
from pathlib import Path


def setup_data_directories():
    """Create required data directories"""
    print("\n[1/3] Creating data directories...")

    dirs = [
        "/mnt/data/covid_inputs/week_current",
        "/mnt/data/covid_outputs/week_current",
        "/mnt/data/test_data/Task06_Lung/imagesTr"
    ]

    for dir_path in dirs:
        Path(dir_path).mkdir(parents=True, exist_ok=True)
        print(f"  ✓ {dir_path}")


def check_test_data():
    """Check if test data exists"""
    print("\n[2/3] Checking test data...")

    test_data = Path("/mnt/data/test_data/Task06_Lung/imagesTr")

    if not test_data.exists():
        print("  ⚠ Test data not found at /mnt/data/test_data/Task06_Lung/imagesTr")
        print("  Please copy lung CT scans to this directory.")
        print("  Expected files: lung_001.nii.gz, lung_002.nii.gz, etc.")
        return False

    files = list(test_data.glob("*.nii.gz"))
    print(f"  ✓ Found {len(files)} CT scans")

    for f in files[:5]:  # Show first 5
        print(f"    - {f.name}")

    if len(files) > 5:
        print(f"    ... and {len(files) - 5} more")

    return True


def verify_environment():
    """Verify Python environment"""
    print("\n[3/3] Verifying environment...")

    try:
        import torch
        print(f"  ✓ PyTorch {torch.__version__}")
    except ImportError:
        print("  ✗ PyTorch not found")
        return False

    try:
        import monai
        print(f"  ✓ MONAI {monai.__version__}")
    except ImportError:
        print("  ✗ MONAI not found")
        return False

    try:
        import lungmask
        print(f"  ✓ LungMask installed")
    except ImportError:
        print("  ✗ LungMask not found")
        return False

    try:
        import SimpleITK as sitk
        print(f"  ✓ SimpleITK {sitk.__version__}")
    except ImportError:
        print("  ✗ SimpleITK not found")
        return False

    return True


def main():
    print("=" * 60)
    print("COVID-19 Detection Pipeline - Setup")
    print("=" * 60)

    setup_data_directories()
    data_ok = check_test_data()
    env_ok = verify_environment()

    print("\n" + "=" * 60)
    if data_ok and env_ok:
        print("✓ Setup complete!")
        print("=" * 60)
        print("\nNext steps:")
        print("1. Build Docker image: ./build.sh (or build.ps1 on Windows)")
        print("2. Deploy Kubernetes resources: kubectl apply -f kubernetes/")
        print("3. Upload covid_pipeline.yaml to Kubeflow UI")
    else:
        print("⚠ Setup incomplete - please fix the issues above")
        print("=" * 60)


if __name__ == "__main__":
    main()
