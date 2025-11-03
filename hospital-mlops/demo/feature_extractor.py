"""
Feature Extractor cho Disease Detection

Extract clinical features từ CT scan và lung mask để phát hiện bệnh lý

Features:
- Lung volume
- HU statistics (mean, std, distribution)
- Tissue distribution (emphysema, GGO, consolidation)
- Texture features (variance, entropy)
- Spatial features (center of mass)

Usage:
    from feature_extractor import LungFeatureExtractor

    extractor = LungFeatureExtractor()
    features = extractor.extract(ct_array, lung_mask_array, spacing)
"""

import numpy as np
from scipy import ndimage
from scipy.stats import entropy as scipy_entropy
from typing import Dict, Tuple, Optional


class LungFeatureExtractor:
    """
    Extract clinical features từ CT scan và lung mask
    """

    def __init__(self):
        """Initialize feature extractor"""
        pass

    def extract(
        self,
        ct_array: np.ndarray,
        lung_mask_array: np.ndarray,
        spacing: Tuple[float, float, float] = (1.0, 1.0, 1.0)
    ) -> Dict:
        """
        Extract all features

        Args:
            ct_array: CT scan in HU values, shape (D, H, W)
            lung_mask_array: Lung segmentation mask, shape (D, H, W)
                            Values: 0 (background), 1 (right lung), 2 (left lung)
            spacing: Voxel spacing (X, Y, Z) in mm

        Returns:
            dict: All extracted features
        """
        features = {}

        # Extract lung ROI
        lung_roi = ct_array[lung_mask_array > 0]

        if lung_roi.size == 0:
            # No lung detected - return default features
            return self._default_features()

        # ==== Volumetric Features ====
        features.update(self._extract_volume_features(lung_mask_array, spacing))

        # ==== HU Statistics ==== (must be first - needed by texture features)
        features.update(self._extract_hu_statistics(lung_roi))

        # ==== Tissue Distribution ====
        features.update(self._extract_tissue_distribution(lung_roi))

        # ==== Texture Features ==== (depends on hu_mean and hu_std)
        features.update(self._extract_texture_features(lung_roi, features))

        # ==== Spatial Features ====
        features.update(self._extract_spatial_features(lung_mask_array, spacing))

        # ==== Separate left/right lung features ====
        features.update(self._extract_lung_specific_features(
            ct_array, lung_mask_array, spacing
        ))

        return features

    def _extract_volume_features(
        self,
        lung_mask_array: np.ndarray,
        spacing: Tuple[float, float, float]
    ) -> Dict:
        """Extract lung volume features"""
        features = {}

        # Voxel volume in mm^3
        voxel_volume = np.prod(spacing)

        # Total lung volume
        total_lung_voxels = (lung_mask_array > 0).sum()
        features['lung_volume_ml'] = (total_lung_voxels * voxel_volume) / 1000

        # Right lung (label = 1)
        right_lung_voxels = (lung_mask_array == 1).sum()
        features['right_lung_volume_ml'] = (right_lung_voxels * voxel_volume) / 1000

        # Left lung (label = 2)
        left_lung_voxels = (lung_mask_array == 2).sum()
        features['left_lung_volume_ml'] = (left_lung_voxels * voxel_volume) / 1000

        # Volume ratio (should be close to 1.0 for normal)
        if features['left_lung_volume_ml'] > 0:
            features['lung_volume_ratio'] = (
                features['right_lung_volume_ml'] / features['left_lung_volume_ml']
            )
        else:
            features['lung_volume_ratio'] = 0.0

        return features

    def _extract_hu_statistics(self, lung_roi: np.ndarray) -> Dict:
        """Extract HU statistics"""
        features = {}

        features['hu_mean'] = float(lung_roi.mean())
        features['hu_std'] = float(lung_roi.std())
        features['hu_min'] = float(lung_roi.min())
        features['hu_max'] = float(lung_roi.max())
        features['hu_median'] = float(np.median(lung_roi))

        # Percentiles
        features['hu_p5'] = float(np.percentile(lung_roi, 5))
        features['hu_p25'] = float(np.percentile(lung_roi, 25))
        features['hu_p75'] = float(np.percentile(lung_roi, 75))
        features['hu_p95'] = float(np.percentile(lung_roi, 95))

        return features

    def _extract_tissue_distribution(self, lung_roi: np.ndarray) -> Dict:
        """
        Extract tissue distribution based on HU values

        HU Ranges (typical):
        - Emphysema: < -950 HU (air trapping)
        - Normal lung: -950 to -700 HU
        - Ground-glass: -700 to -500 HU
        - Soft tissue: -500 to -100 HU
        - Consolidation: > -300 HU (fluid/pus)
        """
        features = {}
        total_voxels = lung_roi.size

        # Emphysema (air trapping)
        emphysema_voxels = (lung_roi < -950).sum()
        features['emphysema_ratio'] = float(emphysema_voxels / total_voxels)
        features['emphysema_percentage'] = features['emphysema_ratio'] * 100

        # Normal lung parenchyma
        normal_voxels = ((lung_roi >= -950) & (lung_roi <= -700)).sum()
        features['normal_lung_ratio'] = float(normal_voxels / total_voxels)
        features['normal_lung_percentage'] = features['normal_lung_ratio'] * 100

        # Ground-glass opacity (GGO)
        ggo_voxels = ((lung_roi > -700) & (lung_roi <= -500)).sum()
        features['ggo_ratio'] = float(ggo_voxels / total_voxels)
        features['ggo_percentage'] = features['ggo_ratio'] * 100

        # Soft tissue attenuation
        soft_tissue_voxels = ((lung_roi > -500) & (lung_roi <= -100)).sum()
        features['soft_tissue_ratio'] = float(soft_tissue_voxels / total_voxels)
        features['soft_tissue_percentage'] = features['soft_tissue_ratio'] * 100

        # Consolidation (high attenuation - pneumonia, edema)
        consolidation_voxels = (lung_roi > -300).sum()
        features['consolidation_ratio'] = float(consolidation_voxels / total_voxels)
        features['consolidation_percentage'] = features['consolidation_ratio'] * 100

        return features

    def _extract_texture_features(self, lung_roi: np.ndarray, base_features: Dict) -> Dict:
        """Extract texture features from HU distribution"""
        features = {}

        hu_mean = base_features['hu_mean']
        hu_std = base_features['hu_std']

        # Variance
        features['hu_variance'] = float(np.var(lung_roi))

        # Entropy (measure of randomness/heterogeneity)
        hist, _ = np.histogram(lung_roi, bins=100, range=(-1000, 500))
        hist = hist / hist.sum()  # Normalize
        hist = hist[hist > 0]  # Remove zeros to avoid log(0)
        features['hu_entropy'] = float(-np.sum(hist * np.log2(hist)))

        # Coefficient of variation
        if hu_mean != 0:
            features['hu_cv'] = hu_std / abs(hu_mean)
        else:
            features['hu_cv'] = 0.0

        # Skewness (asymmetry of distribution)
        if hu_std > 0:
            features['hu_skewness'] = float(
                ((lung_roi - hu_mean) ** 3).mean() / (hu_std ** 3)
            )
        else:
            features['hu_skewness'] = 0.0

        # Kurtosis (tailedness of distribution)
        if hu_std > 0:
            features['hu_kurtosis'] = float(
                ((lung_roi - hu_mean) ** 4).mean() / (hu_std ** 4)
            )
        else:
            features['hu_kurtosis'] = 0.0

        return features

    def _extract_spatial_features(
        self,
        lung_mask_array: np.ndarray,
        spacing: Tuple[float, float, float]
    ) -> Dict:
        """Extract spatial features"""
        features = {}

        # Center of mass (in physical coordinates)
        com = ndimage.center_of_mass(lung_mask_array > 0)
        features['center_of_mass_z'] = float(com[0] * spacing[2])
        features['center_of_mass_y'] = float(com[1] * spacing[1])
        features['center_of_mass_x'] = float(com[2] * spacing[0])

        # Bounding box size
        lung_coords = np.where(lung_mask_array > 0)
        if len(lung_coords[0]) > 0:
            z_min, z_max = lung_coords[0].min(), lung_coords[0].max()
            y_min, y_max = lung_coords[1].min(), lung_coords[1].max()
            x_min, x_max = lung_coords[2].min(), lung_coords[2].max()

            features['bbox_z_mm'] = float((z_max - z_min) * spacing[2])
            features['bbox_y_mm'] = float((y_max - y_min) * spacing[1])
            features['bbox_x_mm'] = float((x_max - x_min) * spacing[0])
        else:
            features['bbox_z_mm'] = 0.0
            features['bbox_y_mm'] = 0.0
            features['bbox_x_mm'] = 0.0

        return features

    def _extract_lung_specific_features(
        self,
        ct_array: np.ndarray,
        lung_mask_array: np.ndarray,
        spacing: Tuple[float, float, float]
    ) -> Dict:
        """Extract separate features for left and right lungs"""
        features = {}

        # Right lung (label = 1)
        right_lung_roi = ct_array[lung_mask_array == 1]
        if right_lung_roi.size > 0:
            features['right_lung_hu_mean'] = float(right_lung_roi.mean())
            features['right_lung_hu_std'] = float(right_lung_roi.std())
            features['right_lung_ggo_ratio'] = float(
                ((right_lung_roi > -700) & (right_lung_roi <= -500)).sum() / right_lung_roi.size
            )
            features['right_lung_consolidation_ratio'] = float(
                (right_lung_roi > -300).sum() / right_lung_roi.size
            )
        else:
            features['right_lung_hu_mean'] = 0.0
            features['right_lung_hu_std'] = 0.0
            features['right_lung_ggo_ratio'] = 0.0
            features['right_lung_consolidation_ratio'] = 0.0

        # Left lung (label = 2)
        left_lung_roi = ct_array[lung_mask_array == 2]
        if left_lung_roi.size > 0:
            features['left_lung_hu_mean'] = float(left_lung_roi.mean())
            features['left_lung_hu_std'] = float(left_lung_roi.std())
            features['left_lung_ggo_ratio'] = float(
                ((left_lung_roi > -700) & (left_lung_roi <= -500)).sum() / left_lung_roi.size
            )
            features['left_lung_consolidation_ratio'] = float(
                (left_lung_roi > -300).sum() / left_lung_roi.size
            )
        else:
            features['left_lung_hu_mean'] = 0.0
            features['left_lung_hu_std'] = 0.0
            features['left_lung_ggo_ratio'] = 0.0
            features['left_lung_consolidation_ratio'] = 0.0

        # Asymmetry features
        features['lung_hu_asymmetry'] = abs(
            features['right_lung_hu_mean'] - features['left_lung_hu_mean']
        )

        # Bilateral involvement (both lungs affected)
        # Check if both lungs have abnormalities (GGO or consolidation)
        right_abnormal = (features['right_lung_ggo_ratio'] > 0.05 or
                          features['right_lung_consolidation_ratio'] > 0.03)
        left_abnormal = (features['left_lung_ggo_ratio'] > 0.05 or
                         features['left_lung_consolidation_ratio'] > 0.03)
        features['bilateral_involvement'] = right_abnormal and left_abnormal

        return features

    def _default_features(self) -> Dict:
        """Return default features when no lung detected"""
        return {
            'lung_volume_ml': 0.0,
            'right_lung_volume_ml': 0.0,
            'left_lung_volume_ml': 0.0,
            'hu_mean': 0.0,
            'hu_std': 0.0,
            'emphysema_ratio': 0.0,
            'ggo_ratio': 0.0,
            'consolidation_ratio': 0.0,
        }

    def get_feature_names(self) -> list:
        """Get list of all feature names"""
        # Create dummy data to extract feature names
        dummy_ct = np.random.randn(10, 10, 10) * 100 - 800
        dummy_mask = np.ones((10, 10, 10))
        features = self.extract(dummy_ct, dummy_mask)
        return list(features.keys())


# Example usage
if __name__ == "__main__":
    """
    Test feature extractor
    """
    print("\n" + "="*60)
    print("Testing LungFeatureExtractor")
    print("="*60)

    # Create synthetic CT and mask
    print("\n[INFO] Creating synthetic test data...")

    ct_array = np.random.randn(100, 256, 256) * 100 - 850  # Mean ~-850 HU
    lung_mask = np.zeros((100, 256, 256))

    # Create synthetic lung regions
    # Right lung
    lung_mask[30:70, 80:150, 50:120] = 1

    # Left lung
    lung_mask[30:70, 80:150, 140:210] = 2

    spacing = (0.7, 0.7, 1.0)  # mm

    # Extract features
    print("\n[INFO] Extracting features...")
    extractor = LungFeatureExtractor()
    features = extractor.extract(ct_array, lung_mask, spacing)

    # Print features
    print("\n[OK] Features extracted successfully!")
    print(f"\n[INFO] Total features: {len(features)}")

    print("\n--- Volumetric Features ---")
    print(f"  Total lung volume: {features['lung_volume_ml']:.1f} ml")
    print(f"  Right lung volume: {features['right_lung_volume_ml']:.1f} ml")
    print(f"  Left lung volume: {features['left_lung_volume_ml']:.1f} ml")
    print(f"  L/R ratio: {features['lung_volume_ratio']:.2f}")

    print("\n--- HU Statistics ---")
    print(f"  Mean HU: {features['hu_mean']:.1f}")
    print(f"  Std HU: {features['hu_std']:.1f}")
    print(f"  Median HU: {features['hu_median']:.1f}")

    print("\n--- Tissue Distribution ---")
    print(f"  Emphysema: {features['emphysema_percentage']:.1f}%")
    print(f"  Normal lung: {features['normal_lung_percentage']:.1f}%")
    print(f"  Ground-glass: {features['ggo_percentage']:.1f}%")
    print(f"  Consolidation: {features['consolidation_percentage']:.1f}%")

    print("\n--- Texture Features ---")
    print(f"  Entropy: {features['hu_entropy']:.2f}")
    print(f"  Variance: {features['hu_variance']:.1f}")
    print(f"  CV: {features['hu_cv']:.3f}")

    print("\n" + "="*60)
    print("[OK] Test completed!")
    print("="*60)
