"""
Custom MONAI Transform để tích hợp LungMask model vào MONAI pipeline

Transform này:
1. Nhận input là MONAI MetaTensor (có metadata: spacing, affine, orientation)
2. Chuyển đổi sang SimpleITK Image (format LungMask yêu cầu)
3. Gọi LungMask inference
4. Chuyển output về MetaTensor và preserve metadata
5. Đảm bảo output mask có cùng spacing, orientation với ảnh gốc

Usage:
    from monai.transforms import Compose, LoadImaged
    from lungmask_transform import LungMaskTransformd

    transforms = Compose([
        LoadImaged(keys=["image"]),
        LungMaskTransformd(keys=["image"], model_name="R231", output_key="pred"),
    ])

    data = {"image": "patient.nii.gz"}
    result = transforms(data)
    # result["pred"] chứa lung segmentation mask
"""

import numpy as np
import SimpleITK as sitk
from typing import Dict, Hashable, Mapping, Optional, Union
import torch

from monai.config import KeysCollection
from monai.data import MetaTensor
from monai.transforms import MapTransform
from monai.utils import ensure_tuple_rep

# Import LungMask
try:
    from lungmask import LMInferer
    LUNGMASK_AVAILABLE = True
except ImportError:
    LUNGMASK_AVAILABLE = False
    print("[WARNING] lungmask not installed. Install: pip install git+https://github.com/JoHof/lungmask")


class LungMaskTransform:
    """
    Transform để apply LungMask model trên single image

    Args:
        model_name: LungMask model name ('R231', 'LTRCLobes', etc.)
        output_dtype: Output data type (default: np.uint8)
        batch_size: Batch size for inference (default: 20)
    """

    def __init__(
        self,
        model_name: str = "R231",
        output_dtype: np.dtype = np.uint8,
        batch_size: int = 20,
    ):
        if not LUNGMASK_AVAILABLE:
            raise ImportError(
                "lungmask is required. Install: pip install git+https://github.com/JoHof/lungmask"
            )

        self.model_name = model_name
        self.output_dtype = output_dtype
        self.batch_size = batch_size

        # Lazy initialization - chỉ load model khi cần
        self._inferer = None

    @property
    def inferer(self):
        """Lazy load LungMask model"""
        if self._inferer is None:
            print(f"[INFO] Loading LungMask model: {self.model_name}")
            self._inferer = LMInferer(modelname=self.model_name)
            print("[INFO] Model loaded successfully")
        return self._inferer

    def _convert_to_sitk(self, image: Union[np.ndarray, torch.Tensor, MetaTensor]) -> sitk.Image:
        """
        Convert MONAI MetaTensor/Tensor/ndarray to SimpleITK Image

        Args:
            image: Input image (MetaTensor, Tensor, or ndarray)
                  Expected shape: (C, H, W, D) or (H, W, D)

        Returns:
            SimpleITK Image with metadata
        """
        # Extract metadata if available
        if isinstance(image, MetaTensor):
            # MetaTensor has metadata
            spacing = image.meta.get('pixdim', None)
            affine = image.meta.get('affine', None)

            # Convert to numpy
            if isinstance(image, torch.Tensor):
                image_np = image.cpu().numpy()
            else:
                image_np = np.array(image)
        else:
            # Plain tensor/array - no metadata
            spacing = None
            affine = None

            if isinstance(image, torch.Tensor):
                image_np = image.cpu().numpy()
            else:
                image_np = np.array(image)

        # Remove channel dimension if present
        if image_np.ndim == 4 and image_np.shape[0] == 1:
            image_np = image_np[0]  # (1, H, W, D) → (H, W, D)

        # SimpleITK expects (D, H, W) but numpy array is usually (H, W, D)
        # LungMask expects input in (D, H, W) order via SimpleITK
        # So we need to transpose: (H, W, D) → (D, H, W)
        if image_np.ndim == 3:
            image_np = np.transpose(image_np, (2, 1, 0))  # (H, W, D) → (D, W, H)

        # Create SimpleITK image
        sitk_image = sitk.GetImageFromArray(image_np)

        # Set metadata if available
        if spacing is not None:
            # spacing from MetaTensor: (X, Y, Z)
            # Convert to tuple and handle different formats
            if isinstance(spacing, torch.Tensor):
                spacing = spacing.cpu().numpy()

            # Take last 3 values (spatial dimensions)
            if len(spacing) > 3:
                spacing = spacing[-3:]

            sitk_image.SetSpacing([float(s) for s in spacing])

        if affine is not None:
            # Extract origin and direction from affine matrix
            if isinstance(affine, torch.Tensor):
                affine = affine.cpu().numpy()

            # Affine matrix: 4x4
            # Origin: last column (translation)
            origin = affine[:3, 3]
            sitk_image.SetOrigin([float(o) for o in origin])

            # Direction: 3x3 rotation matrix
            direction = affine[:3, :3]
            # Normalize direction vectors
            for i in range(3):
                norm = np.linalg.norm(direction[:, i])
                if norm > 0:
                    direction[:, i] /= norm

            sitk_image.SetDirection(direction.flatten().tolist())

        return sitk_image

    def _convert_from_sitk(
        self,
        sitk_image: sitk.Image,
        reference_meta: Optional[Dict] = None
    ) -> MetaTensor:
        """
        Convert SimpleITK Image back to MONAI MetaTensor

        Args:
            sitk_image: SimpleITK Image
            reference_meta: Reference metadata from input image

        Returns:
            MetaTensor with metadata
        """
        # Convert to numpy
        image_np = sitk.GetArrayFromImage(sitk_image)

        # Transpose back: (D, H, W) → (H, W, D)
        image_np = np.transpose(image_np, (2, 1, 0))

        # Add channel dimension: (H, W, D) → (1, H, W, D)
        image_np = image_np[np.newaxis, ...]

        # Convert to tensor
        image_tensor = torch.from_numpy(image_np.astype(self.output_dtype))

        # Create MetaTensor with metadata
        if reference_meta is not None:
            # Copy metadata from reference
            meta_tensor = MetaTensor(image_tensor, meta=reference_meta)
        else:
            # Extract metadata from SimpleITK image
            meta = {}

            # Spacing
            spacing = sitk_image.GetSpacing()
            meta['pixdim'] = torch.tensor([1.0] + list(spacing))

            # Origin and direction
            origin = sitk_image.GetOrigin()
            direction = np.array(sitk_image.GetDirection()).reshape(3, 3)

            # Create affine matrix
            affine = np.eye(4)
            affine[:3, :3] = direction * np.array(spacing)
            affine[:3, 3] = origin
            meta['affine'] = torch.from_numpy(affine)

            meta_tensor = MetaTensor(image_tensor, meta=meta)

        return meta_tensor

    def __call__(
        self,
        image: Union[np.ndarray, torch.Tensor, MetaTensor]
    ) -> MetaTensor:
        """
        Apply LungMask inference

        Args:
            image: Input CT scan (MetaTensor, Tensor, or ndarray)
                  Shape: (C, H, W, D) or (H, W, D)

        Returns:
            MetaTensor: Lung segmentation mask
                       Shape: (1, H, W, D)
                       Values: 0 (background), 1 (right lung), 2 (left lung)
        """
        # Save reference metadata
        reference_meta = None
        if isinstance(image, MetaTensor):
            reference_meta = dict(image.meta)

        # Convert to SimpleITK
        sitk_image = self._convert_to_sitk(image)

        # Apply LungMask
        # inferer.apply() returns numpy array in original input shape
        pred_array = self.inferer.apply(sitk_image, batch_size=self.batch_size)

        # Convert prediction to SimpleITK Image to preserve metadata
        # pred_array is in (D, H, W) format from LungMask
        pred_sitk = sitk.GetImageFromArray(pred_array)

        # Copy metadata from input
        pred_sitk.CopyInformation(sitk_image)

        # Convert back to MetaTensor
        pred_meta_tensor = self._convert_from_sitk(pred_sitk, reference_meta)

        return pred_meta_tensor


class LungMaskTransformd(MapTransform):
    """
    Dictionary-based transform để apply LungMask trên multiple keys

    Tương thích với MONAI pipeline (LoadImaged, Spacingd, etc.)

    Args:
        keys: Keys to apply transform
        model_name: LungMask model name ('R231', 'LTRCLobes', etc.)
        output_key: Key to store output (default: "pred")
        output_dtype: Output data type (default: np.uint8)
        batch_size: Batch size for inference (default: 20)
        allow_missing_keys: Ignore missing keys

    Example:
        transforms = Compose([
            LoadImaged(keys=["image"]),
            LungMaskTransformd(keys=["image"], output_key="pred"),
        ])
    """

    def __init__(
        self,
        keys: KeysCollection,
        model_name: str = "R231",
        output_key: str = "pred",
        output_dtype: np.dtype = np.uint8,
        batch_size: int = 20,
        allow_missing_keys: bool = False,
    ):
        super().__init__(keys, allow_missing_keys)

        self.model_name = model_name
        self.output_key = output_key
        self.output_dtype = output_dtype
        self.batch_size = batch_size

        # Create transform instance (shared across all keys)
        self.transform = LungMaskTransform(
            model_name=model_name,
            output_dtype=output_dtype,
            batch_size=batch_size,
        )

    def __call__(
        self,
        data: Mapping[Hashable, Union[np.ndarray, torch.Tensor, MetaTensor]]
    ) -> Dict[Hashable, Union[np.ndarray, torch.Tensor, MetaTensor]]:
        """
        Apply transform to data dictionary

        Args:
            data: Dictionary with image data
                  Example: {"image": MetaTensor(...)}

        Returns:
            Dictionary with added prediction
            Example: {"image": MetaTensor(...), "pred": MetaTensor(...)}
        """
        d = dict(data)

        for key in self.key_iterator(d):
            # Apply transform
            pred = self.transform(d[key])

            # Store output
            d[self.output_key] = pred

        return d


# Example usage
if __name__ == "__main__":
    """
    Test LungMaskTransformd
    """
    print("\n" + "="*60)
    print("Testing LungMaskTransformd")
    print("="*60)

    from monai.transforms import Compose, LoadImaged, EnsureChannelFirstd
    from pathlib import Path

    # Check if sample data exists
    sample_data = Path("./sample-data/Task06_Lung/imagesTr")
    if not sample_data.exists():
        print("\n[ERROR] Sample data not found!")
        print("Please download data first (see QUICKSTART.md)")
        exit(1)

    # Find first patient
    image_files = list(sample_data.glob("*.nii.gz"))
    if len(image_files) == 0:
        print("\n[ERROR] No .nii.gz files found!")
        exit(1)

    test_image = image_files[0]
    print(f"\n[INFO] Testing with: {test_image.name}")

    # Create pipeline
    transforms = Compose([
        LoadImaged(keys=["image"]),
        EnsureChannelFirstd(keys=["image"]),
        LungMaskTransformd(keys=["image"], model_name="R231", output_key="pred"),
    ])

    # Apply transform
    print("\n[INFO] Running pipeline...")
    data = {"image": str(test_image)}
    result = transforms(data)

    # Check results
    image = result["image"]
    pred = result["pred"]

    print(f"\n[OK] Transform completed!")
    print(f"  Image shape: {image.shape}")
    print(f"  Prediction shape: {pred.shape}")

    # Check metadata
    if isinstance(pred, MetaTensor):
        print(f"  Prediction has metadata: ✓")
        print(f"  Spacing: {pred.meta.get('pixdim', 'N/A')}")
    else:
        print(f"  Prediction has metadata: ✗")

    # Check alignment
    if isinstance(image, MetaTensor) and isinstance(pred, MetaTensor):
        image_spacing = image.meta.get('pixdim')
        pred_spacing = pred.meta.get('pixdim')

        if image_spacing is not None and pred_spacing is not None:
            if torch.allclose(image_spacing, pred_spacing):
                print(f"  Spacing alignment: ✓ PASS")
            else:
                print(f"  Spacing alignment: ✗ FAIL")
                print(f"    Image: {image_spacing}")
                print(f"    Pred:  {pred_spacing}")

    print("\n" + "="*60)
    print("[OK] Test completed!")
    print("="*60)
