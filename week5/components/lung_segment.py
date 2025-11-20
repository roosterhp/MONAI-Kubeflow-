"""
Lung Segmentation Component: Use LungMask to segment lungs
Input: CT scan in NIfTI format
Output: Lung mask + processed CT data for COVID detection
"""

import sys
import numpy as np
import SimpleITK as sitk
from pathlib import Path
from lungmask import LMInferer
import nibabel as nib
from nibabel.affines import voxel_sizes


def lung_segment(input_path: str, output_dir: str):
    """Segment lungs using LungMask R231 model

    Args:
        input_path: Path to input NIfTI file
        output_dir: Directory to save outputs

    Returns:
        0 on success, 1 on failure
    """
    print(f"\n{'='*60}")
    print("LUNG SEGMENTATION")
    print(f"{'='*60}")
    print(f"Input: {input_path}")
    print(f"Output: {output_dir}")

    try:
        # Ensure output directory exists
        Path(output_dir).mkdir(parents=True, exist_ok=True)

        # Load CT scan (robust: SimpleITK with NiBabel fallback)
        print("[Step 1/4] Loading CT scan...")
        try:
            ct_scan = sitk.ReadImage(input_path)
            ct_array = sitk.GetArrayFromImage(ct_scan)
            spacing = ct_scan.GetSpacing()
        except Exception as read_err:
            print(f"  [WARN] SimpleITK failed to read NIfTI: {read_err}")
            print("  [INFO] Falling back to NiBabel loader...")
            ni = nib.load(input_path)
            data = ni.get_fdata(dtype=np.float32)
            arr = np.asarray(data)
            ct_scan = sitk.GetImageFromArray(arr)
            try:
                vox = voxel_sizes(ni.affine)
                ct_scan.SetSpacing(tuple(map(float, vox)))
                spacing = tuple(map(float, vox))
            except Exception as vs_err:
                print(f"  [WARN] Could not derive voxel sizes: {vs_err}")
                spacing = (1.0, 1.0, 1.0)
            ct_array = sitk.GetArrayFromImage(ct_scan)

        print(f"  CT shape: {ct_array.shape}")
        print(f"  Spacing: {spacing}")
        print(f"  HU range: [{ct_array.min():.0f}, {ct_array.max():.0f}]")

        # Run LungMask segmentation
        print("[Step 2/4] Running LungMask segmentation...")
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

        # Save outputs
        print("[Step 3/4] Saving lung mask...")
        lung_mask_path = Path(output_dir) / "lung_mask.nii.gz"
        lung_mask_image = sitk.GetImageFromArray(lung_mask_array)
        lung_mask_image.CopyInformation(ct_scan)
        sitk.WriteImage(lung_mask_image, str(lung_mask_path))
        print(f"  Saved: {lung_mask_path}")

        print("[Step 4/4] Saving CT array and spacing...")
        ct_array_path = Path(output_dir) / "ct_array.npy"
        spacing_path = Path(output_dir) / "spacing.npy"

        np.save(ct_array_path, ct_array)
        np.save(spacing_path, spacing)
        print(f"  Saved: {ct_array_path}")
        print(f"  Saved: {spacing_path}")

        print("[OK] Lung segmentation complete!")
        return 0

    except Exception as e:
        print(f"[ERROR] Lung segmentation failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python lung_segment.py <input_path> <output_dir>")
        sys.exit(1)

    input_path = sys.argv[1]
    output_dir = sys.argv[2]
    sys.exit(lung_segment(input_path, output_dir))