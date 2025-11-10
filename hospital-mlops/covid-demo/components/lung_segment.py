"""
Lung Segmentation Component: Use LungMask to segment lungs
Input: /mnt/data/covid_inputs/week_current/{patient_id}/imaging.nii.gz
Output: /mnt/data/covid_inputs/week_current/{patient_id}/lung_mask.nii.gz
"""

import sys
import numpy as np
import SimpleITK as sitk
from pathlib import Path
from lungmask import LMInferer
import nibabel as nib
from nibabel.affines import voxel_sizes


def lung_segment(patient_id: str):
    """Segment lungs using LungMask R231 model"""
    print(f"\n{'='*60}")
    print(f"LUNG SEGMENTATION: {patient_id}")
    print(f"{'='*60}")

    try:
        # Paths
        input_file = Path(f"/mnt/data/covid_inputs/week_current/{patient_id}/imaging.nii.gz")
        output_file = Path(f"/mnt/data/covid_inputs/week_current/{patient_id}/lung_mask.nii.gz")
        ct_array_file = Path(f"/mnt/data/covid_inputs/week_current/{patient_id}/ct_array.npy")
        spacing_file = Path(f"/mnt/data/covid_inputs/week_current/{patient_id}/spacing.npy")

        print(f"Input: {input_file}")
        print(f"Output: {output_file}")

        if not input_file.exists():
            raise FileNotFoundError(f"Input file not found: {input_file}")

        # Load CT scan (robust: SimpleITK with NiBabel fallback)
        print("[Step 1/4] Loading CT scan...")
        try:
            ct_scan = sitk.ReadImage(str(input_file))
            ct_array = sitk.GetArrayFromImage(ct_scan)
            spacing = ct_scan.GetSpacing()
        except Exception as read_err:
            print(f"  [WARN] SimpleITK failed to read NIfTI: {read_err}")
            print("  [INFO] Falling back to NiBabel loader and constructing SimpleITK image...")
            ni = nib.load(str(input_file))
            data = ni.get_fdata(dtype=np.float32)
            # Convert to HU-like int16 if possible (assume input already in HU). Keep float32 for safety.
            arr = np.asarray(data)
            # Build SimpleITK image from array (note: SITK expects z,y,x ordering from numpy)
            ct_scan = sitk.GetImageFromArray(arr)
            try:
                vox = voxel_sizes(ni.affine)
                # NIfTI voxel sizes are (x, y, z); SimpleITK spacing is (x, y, z)
                # Our numpy array is indexed as [z, y, x], but SetSpacing still expects (x,y,z)
                ct_scan.SetSpacing(tuple(map(float, vox)))
                spacing = tuple(map(float, vox))
            except Exception as vs_err:
                print(f"  [WARN] Could not derive voxel sizes from affine: {vs_err}")
                spacing = (1.0, 1.0, 1.0)
            ct_array = sitk.GetArrayFromImage(ct_scan)

        print(f"  CT shape: {ct_array.shape}")
        print(f"  Spacing: {spacing}")
        print(f"  HU range: [{ct_array.min():.0f}, {ct_array.max():.0f}]")

        # Run LungMask segmentation
        print("[Step 2/4] Running LungMask segmentation...")
        print("  Model: R231")
        inferer = LMInferer(modelname='R231')
        lung_mask_array = inferer.apply(ct_scan)

        print(f"  Mask shape: {lung_mask_array.shape}")
        print(f"  Classes: {np.unique(lung_mask_array)}")

        right_lung = np.sum(lung_mask_array == 1)
        left_lung = np.sum(lung_mask_array == 2)
        total_lung = right_lung + left_lung

        print(f"  Right lung voxels: {right_lung:,}")
        print(f"  Left lung voxels: {left_lung:,}")
        print(f"  Total lung voxels: {total_lung:,}")

        # Save lung mask
        print("[Step 3/4] Saving lung mask...")
        lung_mask_image = sitk.GetImageFromArray(lung_mask_array)
        lung_mask_image.CopyInformation(ct_scan)
        sitk.WriteImage(lung_mask_image, str(output_file))
        print(f"  Saved: {output_file}")

        # Save CT array and spacing for COVID detection
        print("[Step 4/4] Saving CT array and spacing...")
        np.save(ct_array_file, ct_array)
        np.save(spacing_file, spacing)
        print(f"  Saved: {ct_array_file}")
        print(f"  Saved: {spacing_file}")

        print(f"[OK] Lung segmentation complete!")
        return 0

    except Exception as e:
        print(f"[ERROR] Lung segmentation failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python lung_segment.py <patient_id>")
        sys.exit(1)

    patient_id = sys.argv[1]
    sys.exit(lung_segment(patient_id))
