"""
Create small sample dataset for testing

Randomly samples N images per class from full dataset
for quick testing without using full dataset.
"""

import argparse
import random
import shutil
from pathlib import Path
from tqdm import tqdm


def create_sample_dataset(
    input_dir: str,
    output_dir: str,
    num_per_class: int = 25,
    seed: int = 42
):
    """
    Create sample dataset by randomly sampling images from each class.

    Args:
        input_dir: Path to full organized dataset
        output_dir: Path to output sample dataset
        num_per_class: Number of images to sample per class
        seed: Random seed for reproducibility
    """
    random.seed(seed)

    input_path = Path(input_dir)
    output_path = Path(output_dir)

    print("="*60)
    print("Sample Dataset Creation")
    print("="*60)
    print(f"Input:  {input_path}")
    print(f"Output: {output_path}")
    print(f"Samples per class: {num_per_class}")
    print(f"Random seed: {seed}")
    print()

    total_sampled = 0

    # Process each class directory
    for class_dir in sorted(input_path.glob("class_*")):
        class_name = class_dir.name
        output_class = output_path / class_name
        output_class.mkdir(parents=True, exist_ok=True)

        # Get all images
        images = list(class_dir.glob("*.png")) + \
                list(class_dir.glob("*.jpg")) + \
                list(class_dir.glob("*.jpeg"))

        if not images:
            print(f"⚠️  {class_name}: No images found, skipping...")
            continue

        # Sample images
        num_to_sample = min(num_per_class, len(images))
        sampled = random.sample(images, num_to_sample)

        print(f"📂 {class_name}")
        print(f"   Available: {len(images)} images")
        print(f"   Sampling:  {num_to_sample} images")

        # Copy sampled images
        for img in tqdm(sampled, desc="   Copying", leave=False):
            try:
                shutil.copy2(img, output_class / img.name)
            except Exception as e:
                print(f"   ❌ Error copying {img.name}: {e}")

        total_sampled += num_to_sample
        print(f"   ✅ Copied to {class_name}/")
        print()

    print("="*60)
    print(f"✅ Sample dataset created!")
    print(f"   Total sampled: {total_sampled} images")
    print(f"   Output: {output_path}")
    print("="*60)

    # Verify
    verify_sample(output_dir)

    return total_sampled


def verify_sample(output_dir: str):
    """Verify sample dataset."""
    output_path = Path(output_dir)

    print("\n" + "="*60)
    print("Sample Dataset Verification")
    print("="*60)

    total = 0
    for class_dir in sorted(output_path.glob("class_*")):
        images = list(class_dir.glob("*.png")) + \
                list(class_dir.glob("*.jpg")) + \
                list(class_dir.glob("*.jpeg"))
        num_images = len(images)
        total += num_images
        print(f"{class_dir.name:30s}: {num_images:>4} images")

    print("-"*60)
    print(f"{'Total':30s}: {total:>4} images")
    print("="*60)


def main():
    parser = argparse.ArgumentParser(
        description="Create sample dataset for testing",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Create 25 images per class (default)
  python create_sample_dataset.py

  # Create 50 images per class
  python create_sample_dataset.py --num-per-class 50

  # Custom paths
  python create_sample_dataset.py \\
    --input-dir data/organized \\
    --output-dir data/sample_100 \\
    --num-per-class 25
        """
    )

    parser.add_argument(
        "--input-dir",
        type=str,
        default="data/organized",
        help="Path to full organized dataset"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="data/sample",
        help="Path to output sample dataset"
    )
    parser.add_argument(
        "--num-per-class",
        type=int,
        default=25,
        help="Number of images to sample per class"
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for reproducibility"
    )

    args = parser.parse_args()

    # Check input directory exists
    input_path = Path(args.input_dir)
    if not input_path.exists():
        print(f"❌ Error: Input directory not found: {input_path}")
        print()
        print("Please organize the dataset first:")
        print("  python scripts/organize_covid_data.py")
        return 1

    # Create sample dataset
    total_sampled = create_sample_dataset(
        input_dir=args.input_dir,
        output_dir=args.output_dir,
        num_per_class=args.num_per_class,
        seed=args.seed
    )

    print("\n✅ Done!")
    print()
    print("Next steps:")
    print("  1. Test preprocessing with sample data:")
    print(f"     python components/preprocess/preprocess.py \\")
    print(f"       --raw-data-path {args.output_dir} \\")
    print(f"       --output-path data/processed_sample")
    print()

    return 0


if __name__ == "__main__":
    exit(main())
