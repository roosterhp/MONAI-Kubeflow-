"""
Fine-tuning Component: Fine-tune COVID model based on detected cases
Input: Collected patient data and annotations
Output: Fine-tuned model checkpoint
"""

import sys
import json
import torch
import numpy as np
import SimpleITK as sitk
from pathlib import Path
from monai.networks.nets import UNet
from monai.losses import DiceCELoss
from monai.transforms import Compose, LoadImaged, EnsureChannelFirstd, ScaleIntensityRanged, EnsureTyped
from monai.data import DataLoader, Dataset
from path_utils import get_data_path


def create_synthetic_labels(ct_array, lung_mask):
    """
    Create synthetic COVID labels for fine-tuning
    Uses HU thresholds to generate 4-class labels
    """
    label = np.ones_like(ct_array, dtype=np.uint8)

    # Background
    label[lung_mask == 0] = 0

    # GGO: HU -700 to -500
    ggo_mask = ((ct_array > -700) & (ct_array <= -500)) & (lung_mask > 0)
    label[ggo_mask] = 2

    # Consolidation: HU > -300
    cons_mask = (ct_array > -300) & (lung_mask > 0)
    label[cons_mask] = 3

    return label


def collect_training_data(patient_ids):
    """Collect data from processed patients for fine-tuning"""
    training_data = []
    base_path = get_data_path()

    for patient_id in patient_ids:
        ct_path = base_path / f"covid_inputs/week_current/{patient_id}/ct_array.npy"
        mask_path = base_path / f"covid_inputs/week_current/{patient_id}/lung_mask.nii.gz"
        results_path = base_path / f"covid_outputs/week_current/{patient_id}/covid_results.json"

        # Only use high likelihood cases for fine-tuning
        if results_path.exists():
            with open(results_path, 'r') as f:
                results = json.load(f)

            likelihood = results['diagnosis']['covid_likelihood']

            # Use HIGH or MODERATE cases
            if likelihood in ['HIGH', 'MODERATE']:
                if ct_path.exists() and mask_path.exists():
                    training_data.append({
                        'patient_id': patient_id,
                        'ct_path': ct_path,
                        'mask_path': mask_path,
                        'likelihood': likelihood
                    })

    return training_data


def finetune_model(batch_id: str, patient_ids: list):
    """
    Fine-tune COVID detection model

    Args:
        batch_id: Identifier for this fine-tuning batch
        patient_ids: List of patient IDs to use for fine-tuning
    """
    print(f"\n{'='*60}")
    print(f"FINE-TUNING: Batch {batch_id}")
    print(f"{'='*60}")

    try:
        base_path = get_data_path()
        output_dir = base_path / "covid_outputs/finetuned_models"
        output_dir.mkdir(parents=True, exist_ok=True)

        model_path = output_dir / f"finetuned_model_{batch_id}.pth"
        log_path = output_dir / f"training_log_{batch_id}.json"

        # Collect training data
        print(f"[Step 1/5] Collecting training data from {len(patient_ids)} patients...")
        training_data = collect_training_data(patient_ids)

        print(f"  Found {len(training_data)} cases suitable for fine-tuning:")
        for data in training_data:
            print(f"    - {data['patient_id']}: {data['likelihood']}")

        if len(training_data) < 2:
            print(f"\n[WARNING] Not enough data for fine-tuning (need at least 2 cases)")
            print(f"[INFO] Skipping fine-tuning for this batch")
            return 0

        # Prepare dataset
        print(f"\n[Step 2/5] Preparing training dataset...")

        dataset_files = []
        for data in training_data:
            # Load CT and lung mask
            ct_array = np.load(data['ct_path'])
            lung_mask = sitk.GetArrayFromImage(sitk.ReadImage(str(data['mask_path'])))

            # Create synthetic labels
            label_array = create_synthetic_labels(ct_array, lung_mask)

            # Save temporarily
            temp_dir = base_path / f"covid_inputs/temp_finetune/{data['patient_id']}"
            temp_dir.mkdir(parents=True, exist_ok=True)

            ct_file = temp_dir / "ct.npy"
            label_file = temp_dir / "label.npy"

            np.save(ct_file, ct_array)
            np.save(label_file, label_array)

            dataset_files.append({
                'image': str(ct_file),
                'label': str(label_file)
            })

        print(f"  Prepared {len(dataset_files)} training samples")

        # Create model
        print(f"\n[Step 3/5] Creating model...")
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        print(f"  Device: {device}")

        model = UNet(
            spatial_dims=3,
            in_channels=1,
            out_channels=4,  # 4 classes: Background, Normal, GGO, Consolidation
            channels=(16, 32, 64, 128),
            strides=(2, 2, 2),
            num_res_units=2,
            norm="batch",
        ).to(device)

        params = sum(p.numel() for p in model.parameters())
        print(f"  Parameters: {params:,}")

        # Training setup
        print(f"\n[Step 4/5] Training model...")

        loss_function = DiceCELoss(
            include_background=False,
            to_onehot_y=True,
            softmax=True,
        )

        optimizer = torch.optim.Adam(model.parameters(), lr=1e-4)

        # Simple training loop (mini fine-tuning)
        num_epochs = 3  # Quick fine-tuning
        training_log = []

        for epoch in range(num_epochs):
            model.train()
            epoch_loss = 0

            for idx, data in enumerate(dataset_files):
                # Load data
                ct = np.load(data['image'])
                label = np.load(data['label'])

                # Convert to tensors
                ct_tensor = torch.from_numpy(ct).unsqueeze(0).unsqueeze(0).float()
                label_tensor = torch.from_numpy(label).unsqueeze(0).unsqueeze(0).long()

                # Crop to manageable size
                ct_crop = ct_tensor[:, :, 32:96, 32:96, 32:96]  # 64x64x64 crop
                label_crop = label_tensor[:, :, 32:96, 32:96, 32:96]

                ct_crop = ct_crop.to(device)
                label_crop = label_crop.to(device)

                # Forward pass
                optimizer.zero_grad()
                outputs = model(ct_crop)
                loss = loss_function(outputs, label_crop)

                # Backward pass
                loss.backward()
                optimizer.step()

                epoch_loss += loss.item()

                print(f"  Epoch {epoch+1}/{num_epochs}, Sample {idx+1}/{len(dataset_files)}: Loss = {loss.item():.4f}")

            avg_loss = epoch_loss / len(dataset_files)
            training_log.append({
                'epoch': epoch + 1,
                'loss': avg_loss
            })

            print(f"  Epoch {epoch+1} Average Loss: {avg_loss:.4f}")

        # Save model
        print(f"\n[Step 5/5] Saving fine-tuned model...")
        torch.save(model.state_dict(), model_path)
        print(f"  Saved: {model_path}")

        # Save training log
        log_data = {
            'batch_id': batch_id,
            'num_patients': len(training_data),
            'patient_ids': [d['patient_id'] for d in training_data],
            'num_epochs': num_epochs,
            'training_log': training_log,
            'final_loss': training_log[-1]['loss']
        }

        with open(log_path, 'w') as f:
            json.dump(log_data, f, indent=2)

        print(f"  Saved log: {log_path}")

        print(f"\n[OK] Fine-tuning complete!")
        print(f"  Model: {model_path}")
        print(f"  Final loss: {training_log[-1]['loss']:.4f}")

        return 0

    except Exception as e:
        print(f"[ERROR] Fine-tuning failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python finetune.py <batch_id> <patient1> <patient2> ...")
        sys.exit(1)

    batch_id = sys.argv[1]
    patient_ids = sys.argv[2:]

    sys.exit(finetune_model(batch_id, patient_ids))
