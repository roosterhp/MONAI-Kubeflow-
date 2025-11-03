"""
Organize COVID-19 Radiography Dataset into standard format

Input structure (from Kaggle):
    COVID-19_Radiography_Dataset/
    ├── COVID/
    │   └── images/*.png
    ├── Normal/
    │   └── images/*.png
    ├── Lung_Opacity/
    │   └── images/*.png
    └── Viral Pneumonia/
        └── images/*.png

Output structure (for training):
    organized/
    ├── class_0_normal/*.png
    ├── class_1_covid/*.png
    ├── class_2_opacity/*.png
    └── class_3_pneumonia/*.png
"""

import argparse
import shutil
from pathlib import Path
from tqdm import tqdm


def organize_covid_dataset(raw_dir: str, output_dir: str, verbose: bool = True):
    """
    Organize COVID-19 Radiography Dataset into standard format.

    Args:
        raw_dir: Path to raw COVID-19_Radiography_Dataset directory
        output_dir: Path to output organized directory
        verbose: Print progress
    """
    raw_path = Path(raw_dir)
    output_path = Path(output_dir)

    # Class mapping
    class_map = {
        "Normal": "class_0_normal",
        "COVID": "class_1_covid",
        "Lung_Opacity": "class_2_opacity",
        "Viral Pneumonia": "class_3_pneumonia",
    }

    if verbose:
        print("="*60)
        print("COVID-19 Dataset Organization")
        print("="*60)
        print(f"Input:  {raw_path}")
        print(f"Output: {output_path}")
        print()

    # Create output directories
    for class_name in class_map.values():
        (output_path / class_name).mkdir(parents=True, exist_ok=True)

    total_copied = 0

    # Copy images for each class
    for source_name, target_name in class_map.items():
        source_dir = raw_path / source_name / "images"
        target_dir = output_path / target_name

        if not source_dir.exists():
            print(f"⚠️  Warning: {source_dir} not found, skipping...")
            continue

        # Get all PNG images
        images = list(source_dir.glob("*.png"))

        if verbose:
            print(f"📂 {source_name}")
            print(f"   Found: {len(images)} images")
            print(f"   Copying to: {target_name}/")

        # Copy with progress bar
        if verbose:
            images_iter = tqdm(images, desc=f"   Copying", leave=False)
        else:
            images_iter = images

        copied = 0
        for img in images_iter:
            try:
                shutil.copy2(img, target_dir / img.name)
                copied += 1
            except Exception as e:
                print(f"   ❌ Error copying {img.name}: {e}")

        total_copied += copied

        if verbose:
            print(f"   ✅ Copied: {copied}/{len(images)} images")
            print()

    if verbose:
        print("="*60)
        print(f"✅ Organization complete!")
        print(f"   Total images copied: {total_copied}")
        print(f"   Output directory: {output_path}")
        print("="*60)

    return total_copied


def verify_organization(output_dir: str):
    """Verify organized dataset structure and count images."""
    output_path = Path(output_dir)

    print("\n" + "="*60)
    print("Dataset Verification")
    print("="*60)

    total = 0
    for class_dir in sorted(output_path.glob("class_*")):
        images = list(class_dir.glob("*.png"))
        num_images = len(images)
        total += num_images
        print(f"{class_dir.name:30s}: {num_images:>6,} images")

    print("-"*60)
    print(f"{'Total':30s}: {total:>6,} images")
    print("="*60)

    return total


def main():
    parser = argparse.ArgumentParser(
        description="Organize COVID-19 Radiography Dataset",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic usage
  python organize_covid_data.py

  # Custom paths
  python organize_covid_data.py \\
    --raw-dir data/raw/COVID-19_Radiography_Dataset \\
    --output-dir data/organized

  # Verify only (no copying)
  python organize_covid_data.py --verify-only
        """
    )

    parser.add_argument(
        "--raw-dir",
        type=str,
        default="data/raw/COVID-19_Radiography_Dataset",
        help="Path to raw COVID-19_Radiography_Dataset directory"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="data/organized",
        help="Path to output organized directory"
    )
    parser.add_argument(
        "--verify-only",
        action="store_true",
        help="Only verify existing organization (no copying)"
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress progress output"
    )

    args = parser.parse_args()

    # Check raw directory exists
    if not args.verify_only:
        raw_path = Path(args.raw_dir)
        if not raw_path.exists():
            print(f"❌ Error: Raw directory not found: {raw_path}")
            print()
            print("Please download the dataset first:")
            print("  kaggle datasets download -d tawsifurrahman/covid19-radiography-database")
            print("  unzip covid19-radiography-database.zip -d data/raw")
            return 1

        # Organize dataset
        total_copied = organize_covid_dataset(
            raw_dir=args.raw_dir,
            output_dir=args.output_dir,
            verbose=not args.quiet
        )

    # Verify organization
    output_path = Path(args.output_dir)
    if output_path.exists():
        verify_organization(args.output_dir)
    else:
        print(f"❌ Error: Output directory not found: {output_path}")
        return 1

    print("\n✅ Done!")
    print()
    print("Next steps:")
    print("  1. Verify class distribution above")
    print("  2. Run preprocessing:")
    print(f"     python components/preprocess/preprocess.py \\")
    print(f"       --raw-data-path {args.output_dir} \\")
    print(f"       --output-path data/processed")
    print()

    return 0


if __name__ == "__main__":
    exit(main())
