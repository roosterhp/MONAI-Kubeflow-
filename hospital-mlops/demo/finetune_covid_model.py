"""
Fine-tuning MONAI COVID-19 Model với dữ liệu riêng

Pipeline:
1. Load pretrained MONAI COVID model
2. Prepare custom dataset (CT scans + COVID labels)
3. Freeze early layers (transfer learning)
4. Train on custom data
5. Evaluate and save fine-tuned model

Requirements:
- Dữ liệu: CT scans (.nii.gz) + Labels/Masks
- Format:
  data/
    train/
      images/
        patient001.nii.gz
        patient002.nii.gz
      masks/
        patient001_mask.nii.gz  (Ground truth: 0=bg, 1=normal, 2=GGO, 3=consolidation)
    val/
      images/
      masks/
"""

import os
import torch
import numpy as np
from pathlib import Path
from typing import List, Dict, Tuple
import json
from datetime import datetime

from monai.transforms import (
    Compose, LoadImaged, EnsureChannelFirstd, Spacingd,
    ScaleIntensityRanged, RandCropByPosNegLabeld,
    RandFlipd, RandRotate90d, EnsureTyped, AsDiscreted,
    Activationsd
)
from monai.data import CacheDataset, DataLoader
from monai.networks.nets import UNet
from monai.losses import DiceCELoss
from monai.metrics import DiceMetric
from monai.inferers import sliding_window_inference
from monai.utils import set_determinism


class COVIDFineTuner:
    """
    Fine-tuning class for MONAI COVID-19 model
    """

    def __init__(
        self,
        data_root: str,
        pretrained_model_path: str = None,
        output_dir: str = "./finetuned_models",
        device: str = "cuda",
    ):
        """
        Initialize fine-tuner

        Args:
            data_root: Root directory containing train/val folders
            pretrained_model_path: Path to pretrained model weights (.pt or .pth)
            output_dir: Directory to save fine-tuned model
            device: "cuda" or "cpu"
        """
        self.data_root = Path(data_root)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.device = torch.device(device if torch.cuda.is_available() else "cpu")
        print(f"[INFO] Device: {self.device}")

        # Set random seed
        set_determinism(seed=42)

        # Model architecture (same as pretrained)
        self.num_classes = 4  # Background, Normal, GGO, Consolidation
        self.model = self._create_model()

        # Load pretrained weights if provided
        if pretrained_model_path:
            self._load_pretrained(pretrained_model_path)

    def _create_model(self) -> torch.nn.Module:
        """
        Create model architecture (UNet)

        Returns:
            model: UNet model
        """
        model = UNet(
            spatial_dims=3,
            in_channels=1,
            out_channels=self.num_classes,
            channels=(16, 32, 64, 128, 256),
            strides=(2, 2, 2, 2),
            num_res_units=2,
            norm="batch",
        )

        model = model.to(self.device)
        print(f"[INFO] Model created: UNet with {self.num_classes} output classes")

        return model

    def _load_pretrained(self, model_path: str):
        """
        Load pretrained weights

        Args:
            model_path: Path to pretrained model
        """
        print(f"[INFO] Loading pretrained weights: {model_path}")

        try:
            checkpoint = torch.load(model_path, map_location=self.device)

            # Handle different checkpoint formats
            if isinstance(checkpoint, dict):
                if "model" in checkpoint:
                    state_dict = checkpoint["model"]
                elif "state_dict" in checkpoint:
                    state_dict = checkpoint["state_dict"]
                else:
                    state_dict = checkpoint
            else:
                state_dict = checkpoint

            # Load weights
            self.model.load_state_dict(state_dict, strict=False)
            print("[OK] Pretrained weights loaded successfully")

        except Exception as e:
            print(f"[WARNING] Could not load pretrained weights: {e}")
            print("[INFO] Training from scratch")

    def freeze_encoder(self, freeze_ratio: float = 0.5):
        """
        Freeze encoder layers for transfer learning

        Args:
            freeze_ratio: Ratio of encoder layers to freeze (0.0 = none, 1.0 = all)
        """
        print(f"[INFO] Freezing {freeze_ratio*100:.0f}% of encoder layers")

        # Get all encoder parameters
        encoder_params = []
        for name, param in self.model.named_parameters():
            if "model" in name and "down" in name:  # UNet encoder
                encoder_params.append((name, param))

        # Freeze first N layers
        num_to_freeze = int(len(encoder_params) * freeze_ratio)
        for i, (name, param) in enumerate(encoder_params):
            if i < num_to_freeze:
                param.requires_grad = False
                print(f"  [FROZEN] {name}")

        # Count trainable parameters
        trainable = sum(p.numel() for p in self.model.parameters() if p.requires_grad)
        total = sum(p.numel() for p in self.model.parameters())
        print(f"[INFO] Trainable parameters: {trainable:,} / {total:,} ({trainable/total*100:.1f}%)")

    def prepare_data(
        self,
        train_split: float = 0.8,
        cache_rate: float = 1.0,
        batch_size: int = 2,
    ) -> Tuple[DataLoader, DataLoader]:
        """
        Prepare training and validation dataloaders

        Args:
            train_split: Ratio for train/val split
            cache_rate: Cache rate for dataset (1.0 = cache all)
            batch_size: Batch size

        Returns:
            train_loader, val_loader
        """
        print("\n[INFO] Preparing datasets...")

        # Find all images
        train_images = sorted(list((self.data_root / "train" / "images").glob("*.nii.gz")))
        train_masks = sorted(list((self.data_root / "train" / "masks").glob("*.nii.gz")))

        if len(train_images) == 0:
            raise FileNotFoundError(f"No training images found in {self.data_root / 'train' / 'images'}")

        print(f"[INFO] Found {len(train_images)} training samples")

        # Create data dictionaries
        train_files = [
            {"image": str(img), "label": str(mask)}
            for img, mask in zip(train_images, train_masks)
        ]

        # Check if val folder exists
        val_images_dir = self.data_root / "val" / "images"
        if val_images_dir.exists():
            val_images = sorted(list(val_images_dir.glob("*.nii.gz")))
            val_masks = sorted(list((self.data_root / "val" / "masks").glob("*.nii.gz")))
            val_files = [
                {"image": str(img), "label": str(mask)}
                for img, mask in zip(val_images, val_masks)
            ]
            print(f"[INFO] Found {len(val_files)} validation samples")
        else:
            # Split training data
            split_idx = int(len(train_files) * train_split)
            val_files = train_files[split_idx:]
            train_files = train_files[:split_idx]
            print(f"[INFO] Split: {len(train_files)} train, {len(val_files)} val")

        # Define transforms
        train_transforms = Compose([
            LoadImaged(keys=["image", "label"]),
            EnsureChannelFirstd(keys=["image", "label"]),
            Spacingd(keys=["image", "label"], pixdim=(1.5, 1.5, 2.0), mode=("bilinear", "nearest")),
            ScaleIntensityRanged(keys=["image"], a_min=-1000, a_max=500, b_min=0, b_max=1, clip=True),
            RandCropByPosNegLabeld(
                keys=["image", "label"],
                label_key="label",
                spatial_size=(96, 96, 96),
                pos=2,  # More positive samples (with lesions)
                neg=1,
                num_samples=2,
            ),
            RandFlipd(keys=["image", "label"], prob=0.5, spatial_axis=0),
            RandRotate90d(keys=["image", "label"], prob=0.5, spatial_axes=(0, 1)),
            EnsureTyped(keys=["image", "label"]),
        ])

        val_transforms = Compose([
            LoadImaged(keys=["image", "label"]),
            EnsureChannelFirstd(keys=["image", "label"]),
            Spacingd(keys=["image", "label"], pixdim=(1.5, 1.5, 2.0), mode=("bilinear", "nearest")),
            ScaleIntensityRanged(keys=["image"], a_min=-1000, a_max=500, b_min=0, b_max=1, clip=True),
            EnsureTyped(keys=["image", "label"]),
        ])

        # Create datasets
        train_ds = CacheDataset(
            data=train_files,
            transform=train_transforms,
            cache_rate=cache_rate,
            num_workers=4,
        )

        val_ds = CacheDataset(
            data=val_files,
            transform=val_transforms,
            cache_rate=cache_rate,
            num_workers=4,
        )

        # Create dataloaders
        train_loader = DataLoader(
            train_ds,
            batch_size=batch_size,
            shuffle=True,
            num_workers=4,
        )

        val_loader = DataLoader(
            val_ds,
            batch_size=1,
            shuffle=False,
            num_workers=4,
        )

        print(f"[OK] Dataloaders ready")
        return train_loader, val_loader

    def train(
        self,
        train_loader: DataLoader,
        val_loader: DataLoader,
        num_epochs: int = 50,
        learning_rate: float = 1e-4,
        val_interval: int = 2,
    ) -> Dict:
        """
        Training loop

        Args:
            train_loader: Training dataloader
            val_loader: Validation dataloader
            num_epochs: Number of epochs
            learning_rate: Learning rate
            val_interval: Validate every N epochs

        Returns:
            training_history: Dictionary with training metrics
        """
        print(f"\n[INFO] Starting fine-tuning for {num_epochs} epochs")

        # Loss and optimizer
        loss_function = DiceCELoss(
            include_background=False,
            to_onehot_y=True,
            softmax=True,
            squared_pred=True,
            lambda_dice=0.5,
            lambda_ce=0.5,
        )

        optimizer = torch.optim.Adam(
            [p for p in self.model.parameters() if p.requires_grad],
            lr=learning_rate,
        )

        # Learning rate scheduler
        scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=num_epochs)

        # Metrics
        dice_metric = DiceMetric(include_background=False, reduction="mean")

        # Training history
        history = {
            "train_loss": [],
            "val_dice": [],
            "best_val_dice": 0.0,
            "best_epoch": 0,
        }

        # Training loop
        for epoch in range(num_epochs):
            print(f"\n{'='*60}")
            print(f"Epoch {epoch + 1}/{num_epochs}")
            print(f"{'='*60}")

            # ===== TRAINING =====
            self.model.train()
            epoch_loss = 0
            step = 0

            for batch_data in train_loader:
                step += 1
                inputs = batch_data["image"].to(self.device)
                labels = batch_data["label"].to(self.device)

                optimizer.zero_grad()
                outputs = self.model(inputs)
                loss = loss_function(outputs, labels)
                loss.backward()
                optimizer.step()

                epoch_loss += loss.item()

                if step % 10 == 0:
                    print(f"  [{step}/{len(train_loader)}] Loss: {loss.item():.4f}")

            epoch_loss /= step
            history["train_loss"].append(epoch_loss)

            print(f"\n[TRAIN] Epoch Loss: {epoch_loss:.4f}")
            print(f"[INFO] Learning Rate: {optimizer.param_groups[0]['lr']:.6f}")

            # ===== VALIDATION =====
            if (epoch + 1) % val_interval == 0:
                print(f"\n[VALIDATION] Running validation...")
                self.model.eval()
                dice_metric.reset()

                with torch.no_grad():
                    for val_data in val_loader:
                        val_inputs = val_data["image"].to(self.device)
                        val_labels = val_data["label"].to(self.device)

                        # Sliding window inference
                        val_outputs = sliding_window_inference(
                            inputs=val_inputs,
                            roi_size=(96, 96, 96),
                            sw_batch_size=4,
                            predictor=self.model,
                            overlap=0.5,
                        )

                        # Post-processing
                        val_outputs = torch.argmax(val_outputs, dim=1, keepdim=True)
                        val_labels_onehot = torch.nn.functional.one_hot(
                            val_labels.squeeze(1).long(), num_classes=self.num_classes
                        ).permute(0, 4, 1, 2, 3).float()

                        val_outputs_onehot = torch.nn.functional.one_hot(
                            val_outputs.squeeze(1).long(), num_classes=self.num_classes
                        ).permute(0, 4, 1, 2, 3).float()

                        dice_metric(y_pred=val_outputs_onehot, y=val_labels_onehot)

                # Calculate mean dice
                mean_dice = dice_metric.aggregate().item()
                history["val_dice"].append(mean_dice)

                print(f"[VAL] Mean Dice: {mean_dice:.4f}")

                # Save best model
                if mean_dice > history["best_val_dice"]:
                    history["best_val_dice"] = mean_dice
                    history["best_epoch"] = epoch + 1

                    model_path = self.output_dir / "best_model.pth"
                    torch.save(self.model.state_dict(), model_path)
                    print(f"[OK] Best model saved: {model_path}")

            # Update learning rate
            scheduler.step()

        # Save final model
        final_path = self.output_dir / "final_model.pth"
        torch.save(self.model.state_dict(), final_path)
        print(f"\n[OK] Final model saved: {final_path}")

        # Save training history
        history_path = self.output_dir / "training_history.json"
        with open(history_path, "w") as f:
            json.dump(history, f, indent=2)
        print(f"[OK] Training history saved: {history_path}")

        print(f"\n{'='*60}")
        print("FINE-TUNING COMPLETE")
        print(f"{'='*60}")
        print(f"Best Validation Dice: {history['best_val_dice']:.4f} (Epoch {history['best_epoch']})")

        return history


def main():
    """
    Example usage
    """
    print("\n" + "="*70)
    print("MONAI COVID-19 MODEL FINE-TUNING")
    print("="*70)

    # Configuration
    config = {
        "data_root": "./data/covid_custom",  # Your custom data folder
        "pretrained_model_path": "./monai_models/covid19_lung_ct_segmentation/models/model.pt",
        "output_dir": "./finetuned_covid_model",
        "device": "cuda",

        # Training hyperparameters
        "freeze_ratio": 0.5,  # Freeze 50% of encoder
        "num_epochs": 50,
        "batch_size": 2,
        "learning_rate": 1e-4,
        "val_interval": 2,
    }

    # Initialize fine-tuner
    finetuner = COVIDFineTuner(
        data_root=config["data_root"],
        pretrained_model_path=config.get("pretrained_model_path"),
        output_dir=config["output_dir"],
        device=config["device"],
    )

    # Freeze encoder layers (transfer learning)
    finetuner.freeze_encoder(freeze_ratio=config["freeze_ratio"])

    # Prepare data
    train_loader, val_loader = finetuner.prepare_data(
        batch_size=config["batch_size"],
    )

    # Train
    history = finetuner.train(
        train_loader=train_loader,
        val_loader=val_loader,
        num_epochs=config["num_epochs"],
        learning_rate=config["learning_rate"],
        val_interval=config["val_interval"],
    )

    print("\n[OK] Fine-tuning pipeline completed!")


if __name__ == "__main__":
    main()
