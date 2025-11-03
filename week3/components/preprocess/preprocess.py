"""
Data Preprocessing Component for Medical Image Classification

This component:
- Loads raw medical images (DICOM, PNG, JPG)
- Applies MONAI transforms
- Splits into train/val/test sets
- Computes dataset statistics
- Caches preprocessed data
"""

import argparse
import json
import os
from pathlib import Path
from typing import Dict, List, Tuple
import numpy as np

from monai.data import CacheDataset, Dataset
from monai.transforms import (
    Compose,
    LoadImaged,
    EnsureChannelFirstd,
    Resized,
    ScaleIntensityd,
    NormalizeIntensityd,
    RandRotated,
    RandFlipd,
    RandZoomd,
    EnsureTyped,
)


class DataPreprocessor:
    """
    Preprocessor for 2D medical images.

    Handles loading, transforming, and splitting medical image datasets
    for EfficientNetV2 classification.
    """

    def __init__(
        self,
        raw_data_path: str,
        output_path: str,
        image_size: Tuple[int, int] = (224, 224),
        train_split: float = 0.7,
        val_split: float = 0.2,
        test_split: float = 0.1,
        cache_rate: float = 1.0,
    ):
        self.raw_data_path = Path(raw_data_path)
        self.output_path = Path(output_path)
        self.image_size = image_size
        self.train_split = train_split
        self.val_split = val_split
        self.test_split = test_split
        self.cache_rate = cache_rate

        # Create output directories
        self.output_path.mkdir(parents=True, exist_ok=True)
        (self.output_path / "train").mkdir(exist_ok=True)
        (self.output_path / "val").mkdir(exist_ok=True)
        (self.output_path / "test").mkdir(exist_ok=True)

    def scan_data(self) -> Dict[str, List[Dict]]:
        """
        Scan raw data directory and create data dictionaries.

        Expected structure:
            raw_data/
            ├── class_0/
            │   ├── img1.png
            │   └── img2.png
            ├── class_1/
            └── ...

        Returns:
            Dictionary with 'train', 'val', 'test' splits
        """
        print(f"📂 Scanning data directory: {self.raw_data_path}")

        # Find all class directories
        class_dirs = [d for d in self.raw_data_path.iterdir() if d.is_dir()]
        print(f"   Found {len(class_dirs)} classes")

        # Collect all images
        all_data = []
        class_counts = {}

        for class_idx, class_dir in enumerate(sorted(class_dirs)):
            class_name = class_dir.name
            image_files = list(class_dir.glob("*.png")) + \
                         list(class_dir.glob("*.jpg")) + \
                         list(class_dir.glob("*.jpeg"))

            class_counts[class_name] = len(image_files)

            for img_path in image_files:
                all_data.append({
                    "image": str(img_path),
                    "label": class_idx,
                    "class_name": class_name,
                })

        print(f"   Total images: {len(all_data)}")
        print(f"   Class distribution: {class_counts}")

        # Shuffle and split
        np.random.seed(42)
        np.random.shuffle(all_data)

        n_total = len(all_data)
        n_train = int(n_total * self.train_split)
        n_val = int(n_total * self.val_split)

        splits = {
            "train": all_data[:n_train],
            "val": all_data[n_train:n_train + n_val],
            "test": all_data[n_train + n_val:],
        }

        print(f"   Train: {len(splits['train'])} samples")
        print(f"   Val: {len(splits['val'])} samples")
        print(f"   Test: {len(splits['test'])} samples")

        return splits

    def get_train_transforms(self) -> Compose:
        """Get training transforms with augmentation."""
        return Compose([
            LoadImaged(keys=["image"]),
            EnsureChannelFirstd(keys=["image"]),
            Resized(keys=["image"], spatial_size=self.image_size),
            ScaleIntensityd(keys=["image"], minv=0.0, maxv=1.0),
            # ImageNet normalization
            NormalizeIntensityd(
                keys=["image"],
                subtrahend=[0.485, 0.456, 0.406],
                divisor=[0.229, 0.224, 0.225],
            ),
            # Augmentation
            RandRotated(keys=["image"], prob=0.5, range_x=0.2, range_y=0.2),
            RandFlipd(keys=["image"], prob=0.5, spatial_axis=0),
            RandFlipd(keys=["image"], prob=0.5, spatial_axis=1),
            RandZoomd(keys=["image"], prob=0.3, min_zoom=0.9, max_zoom=1.1),
            EnsureTyped(keys=["image"], dtype="float32"),
        ])

    def get_val_transforms(self) -> Compose:
        """Get validation/test transforms (no augmentation)."""
        return Compose([
            LoadImaged(keys=["image"]),
            EnsureChannelFirstd(keys=["image"]),
            Resized(keys=["image"], spatial_size=self.image_size),
            ScaleIntensityd(keys=["image"], minv=0.0, maxv=1.0),
            # ImageNet normalization
            NormalizeIntensityd(
                keys=["image"],
                subtrahend=[0.485, 0.456, 0.406],
                divisor=[0.229, 0.224, 0.225],
            ),
            EnsureTyped(keys=["image"], dtype="float32"),
        ])

    def compute_statistics(self, data_list: List[Dict]) -> Dict:
        """
        Compute dataset statistics.

        Args:
            data_list: List of data dictionaries

        Returns:
            Statistics dictionary
        """
        labels = [d["label"] for d in data_list]
        classes = list(set([d["class_name"] for d in data_list]))

        stats = {
            "num_samples": len(data_list),
            "num_classes": len(classes),
            "classes": sorted(classes),
            "class_distribution": {},
        }

        # Class distribution
        for label in set(labels):
            count = labels.count(label)
            stats["class_distribution"][label] = count

        return stats

    def process(self) -> Dict:
        """
        Main preprocessing pipeline.

        Returns:
            Dataset statistics
        """
        print("🚀 Starting data preprocessing...")

        # 1. Scan and split data
        splits = self.scan_data()

        # 2. Create datasets with transforms
        print("\n📦 Creating datasets...")
        train_ds = CacheDataset(
            data=splits["train"],
            transform=self.get_train_transforms(),
            cache_rate=self.cache_rate,
            num_workers=4,
        )
        print(f"   ✅ Train dataset cached: {len(train_ds)} samples")

        val_ds = CacheDataset(
            data=splits["val"],
            transform=self.get_val_transforms(),
            cache_rate=self.cache_rate,
            num_workers=4,
        )
        print(f"   ✅ Val dataset cached: {len(val_ds)} samples")

        test_ds = CacheDataset(
            data=splits["test"],
            transform=self.get_val_transforms(),
            cache_rate=self.cache_rate,
            num_workers=4,
        )
        print(f"   ✅ Test dataset cached: {len(test_ds)} samples")

        # 3. Compute statistics
        print("\n📊 Computing statistics...")
        train_stats = self.compute_statistics(splits["train"])
        val_stats = self.compute_statistics(splits["val"])
        test_stats = self.compute_statistics(splits["test"])

        all_stats = {
            "train": train_stats,
            "val": val_stats,
            "test": test_stats,
            "image_size": self.image_size,
            "normalization": {
                "mean": [0.485, 0.456, 0.406],
                "std": [0.229, 0.224, 0.225],
            },
        }

        # 4. Save metadata
        metadata_path = self.output_path / "metadata.json"
        with open(metadata_path, "w") as f:
            json.dump(all_stats, f, indent=2)
        print(f"   ✅ Metadata saved: {metadata_path}")

        # Save data splits
        splits_path = self.output_path / "data_splits.json"
        with open(splits_path, "w") as f:
            json.dump(splits, f, indent=2)
        print(f"   ✅ Data splits saved: {splits_path}")

        print("\n✅ Preprocessing complete!")
        return all_stats


def main():
    parser = argparse.ArgumentParser(description="Preprocess medical images")
    parser.add_argument(
        "--raw-data-path",
        type=str,
        required=True,
        help="Path to raw data directory",
    )
    parser.add_argument(
        "--output-path",
        type=str,
        required=True,
        help="Path to output processed data",
    )
    parser.add_argument(
        "--image-size",
        type=int,
        nargs=2,
        default=[224, 224],
        help="Image size (height width)",
    )
    parser.add_argument(
        "--train-split",
        type=float,
        default=0.7,
        help="Train split ratio",
    )
    parser.add_argument(
        "--val-split",
        type=float,
        default=0.2,
        help="Validation split ratio",
    )
    parser.add_argument(
        "--test-split",
        type=float,
        default=0.1,
        help="Test split ratio",
    )
    parser.add_argument(
        "--cache-rate",
        type=float,
        default=1.0,
        help="Cache rate (0.0-1.0)",
    )

    args = parser.parse_args()

    # Validate splits
    total_split = args.train_split + args.val_split + args.test_split
    assert abs(total_split - 1.0) < 0.01, "Splits must sum to 1.0"

    # Run preprocessing
    preprocessor = DataPreprocessor(
        raw_data_path=args.raw_data_path,
        output_path=args.output_path,
        image_size=tuple(args.image_size),
        train_split=args.train_split,
        val_split=args.val_split,
        test_split=args.test_split,
        cache_rate=args.cache_rate,
    )

    stats = preprocessor.process()

    # Print summary
    print("\n" + "="*60)
    print("PREPROCESSING SUMMARY")
    print("="*60)
    print(f"Train samples: {stats['train']['num_samples']}")
    print(f"Val samples: {stats['val']['num_samples']}")
    print(f"Test samples: {stats['test']['num_samples']}")
    print(f"Number of classes: {stats['train']['num_classes']}")
    print(f"Classes: {stats['train']['classes']}")
    print(f"Image size: {stats['image_size']}")
    print("="*60)


if __name__ == "__main__":
    main()
