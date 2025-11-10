"""
Load Data Component: Copy patient CT scan to pipeline input
Source: /mnt/data/test_data/Task06_Lung/imagesTr/lung_XXX.nii.gz
Target: /mnt/data/covid_inputs/week_current/{patient_id}/imaging.nii.gz
"""

import sys
import shutil
from pathlib import Path
import SimpleITK as sitk
import nibabel as nib


def load_data(patient_id: str):
    """Copy CT scan from test dataset to pipeline input directory"""
    print(f"\n{'='*60}")
    print(f"LOAD DATA: {patient_id}")
    print(f"{'='*60}")

    try:
        # Locate source: support multiple common input locations on the PVC
        source_candidates = [
            Path(f"/mnt/data/test_data/Task06_Lung/imagesTr/{patient_id}.nii.gz"),
            Path(f"/mnt/data/input/{patient_id}.nii.gz"),
            Path(f"/mnt/data/input/{patient_id}/imaging.nii.gz"),
            Path(f"/mnt/data/input/{patient_id}/{patient_id}.nii.gz"),
        ]
        source_file = None
        for cand in source_candidates:
            if cand.exists():
                source_file = cand
                break

        # Target: COVID pipeline input directory
        target_dir = Path(f"/mnt/data/covid_inputs/week_current/{patient_id}")
        target_file = target_dir / "imaging.nii.gz"

        print("Source candidates:")
        for c in source_candidates:
            print(f"  - {c} {'[FOUND]' if c.exists() else ''}")

        if source_file is None:
            raise FileNotFoundError(
                "No input found for {}. Place one of:".format(patient_id)
                + f"\n  - /mnt/data/test_data/Task06_Lung/imagesTr/{patient_id}.nii.gz"
                + f"\n  - /mnt/data/input/{patient_id}.nii.gz"
                + f"\n  - /mnt/data/input/{patient_id}/imaging.nii.gz"
                + f"\n  - /mnt/data/input/{patient_id}/{patient_id}.nii.gz"
            )

        print(f"Selected source: {source_file}")
        print(f"Target: {target_file}")

        # Check source exists
        if not source_file.exists():
            raise FileNotFoundError(f"Source file not found: {source_file}")

        # Create target directory
        print(f"[Step 1/2] Creating target directory...")
        target_dir.mkdir(parents=True, exist_ok=True)
        print(f"  Created: {target_dir}")

        # Copy file
        print(f"[Step 2/2] Copying CT scan...")
        def _is_valid_nifti(p: Path) -> bool:
            try:
                # Try SimpleITK first
                _ = sitk.ReadImage(str(p))
                return True
            except Exception:
                try:
                    # Fallback to NiBabel header read
                    _ = nib.load(str(p))
                    return True
                except Exception:
                    return False

        do_copy = True
        if target_file.exists():
            size = target_file.stat().st_size
            if size > 0 and _is_valid_nifti(target_file):
                print(f"  File already exists and is valid ({size/1024/1024:.2f} MB), skipping copy")
                do_copy = False
            else:
                print(f"  Existing file is invalid or empty, re-copying...")

        if do_copy:
            shutil.copy2(source_file, target_file)
            print(f"  Copied successfully")

        # Final integrity check
        if not _is_valid_nifti(target_file):
            raise RuntimeError(f"Target file appears corrupted or unreadable: {target_file}")

        # Verify
        file_size = target_file.stat().st_size / (1024 * 1024)  # MB
        print(f"  Size: {file_size:.2f} MB")
        print(f"  Location: {target_file}")

        print(f"[OK] Data loading complete!")
        return 0

    except Exception as e:
        print(f"[ERROR] Data loading failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python load_data.py <patient_id>")
        sys.exit(1)

    patient_id = sys.argv[1]
    sys.exit(load_data(patient_id))
