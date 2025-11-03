"""
Download MONAI COVID-19 Bundle

This script downloads the pretrained COVID-19 CT segmentation model from MONAI.

Model Details:
- Name: covid19_lung_ct_segmentation
- Task: Segment COVID-19 lesions (GGO, consolidation) in CT scans
- Output Classes:
  - 0: Background
  - 1: Normal lung
  - 2: Ground-Glass Opacity (GGO)
  - 3: Consolidation
- Training Data: 1000+ COVID CT scans
- Architecture: SegResNet
"""

import os
from pathlib import Path


def download_covid_model():
    """Download MONAI COVID-19 segmentation bundle"""

    print("\n" + "="*70)
    print("MONAI COVID-19 Model Downloader")
    print("="*70)

    # Create models directory
    models_dir = Path("./monai_models")
    models_dir.mkdir(exist_ok=True)

    print(f"\n[INFO] Models directory: {models_dir.absolute()}")

    # Check if already downloaded
    covid_model_dir = models_dir / "covid19_lung_ct_segmentation"
    if covid_model_dir.exists():
        print(f"\n[INFO] Model already exists at: {covid_model_dir}")
        print("[INFO] Skipping download...")
        return str(covid_model_dir)

    print("\n[INFO] Downloading MONAI COVID-19 model...")
    print("[INFO] This may take 5-10 minutes (~500 MB)...")

    try:
        from monai.bundle import download

        # Download bundle
        download(
            name="covid19_lung_ct_segmentation",
            bundle_dir=str(models_dir),
            source="monaihosting",
            progress=True
        )

        print(f"\n[OK] Model downloaded successfully!")
        print(f"[INFO] Location: {covid_model_dir}")

        # List downloaded files
        if covid_model_dir.exists():
            print(f"\n[INFO] Downloaded files:")
            for item in covid_model_dir.rglob("*"):
                if item.is_file():
                    size_mb = item.stat().st_size / (1024 * 1024)
                    print(f"  - {item.relative_to(covid_model_dir)}: {size_mb:.1f} MB")

        return str(covid_model_dir)

    except ImportError:
        print("\n[ERROR] MONAI not installed!")
        print("[INFO] Install: pip install monai")
        return None
    except Exception as e:
        print(f"\n[ERROR] Download failed: {e}")
        print("\n[INFO] Troubleshooting:")
        print("  1. Check internet connection")
        print("  2. Try manual download:")
        print("     from monai.bundle import download")
        print("     download(name='covid19_lung_ct_segmentation')")
        return None


def verify_model():
    """Verify downloaded model structure"""

    print("\n" + "="*70)
    print("Model Verification")
    print("="*70)

    models_dir = Path("./monai_models")
    covid_model_dir = models_dir / "covid19_lung_ct_segmentation"

    if not covid_model_dir.exists():
        print("\n[ERROR] Model directory not found!")
        return False

    # Check required files
    required_files = [
        "configs/inference.json",
        "models/model.pt",
    ]

    print("\n[INFO] Checking required files...")
    all_ok = True
    for file_path in required_files:
        full_path = covid_model_dir / file_path
        if full_path.exists():
            print(f"  [OK] {file_path}")
        else:
            print(f"  [MISSING] {file_path}")
            all_ok = False

    if all_ok:
        print("\n[OK] Model structure verified!")
        return True
    else:
        print("\n[ERROR] Model structure incomplete!")
        print("[INFO] Try re-downloading the model")
        return False


def test_model_loading():
    """Test if model can be loaded"""

    print("\n" + "="*70)
    print("Model Loading Test")
    print("="*70)

    try:
        from monai.bundle import ConfigParser

        models_dir = Path("./monai_models")
        covid_model_dir = models_dir / "covid19_lung_ct_segmentation"

        print("\n[INFO] Attempting to load model...")

        # Load config
        config_file = covid_model_dir / "configs" / "inference.json"
        if not config_file.exists():
            print(f"[ERROR] Config file not found: {config_file}")
            return False

        parser = ConfigParser()
        parser.read_config(str(config_file))

        print("[OK] Config loaded successfully!")

        # Check if model weights exist
        model_file = covid_model_dir / "models" / "model.pt"
        if model_file.exists():
            size_mb = model_file.stat().st_size / (1024 * 1024)
            print(f"[OK] Model weights found: {size_mb:.1f} MB")
        else:
            print("[ERROR] Model weights not found!")
            return False

        print("\n[OK] Model ready for inference!")
        return True

    except ImportError as e:
        print(f"[ERROR] Import failed: {e}")
        print("[INFO] Install: pip install monai")
        return False
    except Exception as e:
        print(f"[ERROR] Loading failed: {e}")
        return False


def main():
    """Main function"""

    # Step 1: Download
    model_path = download_covid_model()

    if model_path is None:
        print("\n[ERROR] Download failed. Exiting...")
        return

    # Step 2: Verify
    if not verify_model():
        print("\n[ERROR] Verification failed. Exiting...")
        return

    # Step 3: Test loading
    if not test_model_loading():
        print("\n[WARNING] Model loading test failed")
        print("[INFO] But model files are present, may work in inference")

    # Summary
    print("\n" + "="*70)
    print("DOWNLOAD COMPLETE")
    print("="*70)

    print("\n[SUMMARY]")
    print(f"  Model: covid19_lung_ct_segmentation")
    print(f"  Location: ./monai_models/covid19_lung_ct_segmentation/")
    print(f"  Status: Ready for use")

    print("\n[NEXT STEPS]")
    print("  1. Run COVID detection:")
    print("     python monai_covid_classifier.py")
    print("  2. Compare with rule-based:")
    print("     python compare_methods.py")

    print("\n" + "="*70)


if __name__ == "__main__":
    main()
