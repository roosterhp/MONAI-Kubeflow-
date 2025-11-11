"""
Download MedicalNet pretrained weights

MedicalNet 3D-ResNet50 pretrained on 23 medical datasets
Source: https://github.com/Tencent/MedicalNet
"""

import os
from pathlib import Path

def download_medicalnet_weights():
    """Download MedicalNet ResNet-50 pretrained weights"""

    weights_dir = Path(__file__).parent / "pretrained_weights/medicalnet"
    weights_dir.mkdir(parents=True, exist_ok=True)

    weights_file = weights_dir / "resnet_50_23dataset.pth"

    if weights_file.exists():
        print(f"[OK] Weights already exist: {weights_file}")
        return str(weights_file)

    print("\n" + "="*70)
    print("DOWNLOADING MEDICALNET PRETRAINED WEIGHTS")
    print("="*70)
    print("\nModel: MedicalNet 3D-ResNet50")
    print("Source: Tencent/MedicalNet (GitHub)")
    print("Pretrained on: 23 medical imaging datasets")
    print("Size: ~185MB")
    print()

    # Try gdown (Google Drive downloader)
    try:
        import gdown
        print("[OK] gdown is installed")
    except ImportError:
        print("[!] Installing gdown...")
        import subprocess
        subprocess.check_call(["pip", "install", "gdown", "-q"])
        import gdown
        print("[OK] gdown installed")

    # MedicalNet weights on Google Drive
    # File ID from: https://github.com/Tencent/MedicalNet
    # Using the full dataset link from README
    file_id = "13tnSvXY7oDIEloNFiGTsjUIYfS3g3BfG"
    url = f"https://drive.google.com/uc?id={file_id}"

    print(f"[Downloading] From Google Drive...")
    print(f"[Target] {weights_file}")

    try:
        gdown.download(url, str(weights_file), quiet=False)
        print(f"\n[OK] Downloaded: {weights_file}")
        print(f"[OK] Size: {weights_file.stat().st_size / (1024*1024):.1f} MB")
        return str(weights_file)
    except Exception as e:
        print(f"\n[ERROR] Download failed: {e}")
        print("\n" + "="*70)
        print("MANUAL DOWNLOAD INSTRUCTIONS")
        print("="*70)
        print("1. Visit: https://github.com/Tencent/MedicalNet")
        print("2. Go to 'Pretrained Models' section")
        print("3. Download: resnet_50_23dataset.pth")
        print(f"4. Place at: {weights_file}")
        print("="*70)
        return None

if __name__ == "__main__":
    weights_path = download_medicalnet_weights()

    if weights_path:
        print("\n✅ Ready to use MedicalNet!")
        print(f"   Weights: {weights_path}")
    else:
        print("\n❌ Please download weights manually")
