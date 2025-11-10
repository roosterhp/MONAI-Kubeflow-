"""
COVID-19 Detection Component: Run both Rule-based and MONAI methods
Input: CT array, lung mask, spacing
Output: JSON results with both methods
"""

import sys
import numpy as np
import SimpleITK as sitk
import json
import time
from pathlib import Path


def extract_features(ct_array, lung_mask_array, spacing):
    """Extract HU-based COVID features"""

    # Convert spacing to mm
    spacing_mm = np.array(spacing)
    voxel_volume_ml = np.prod(spacing_mm) / 1000.0

    # Get lung region
    lung_region = lung_mask_array > 0
    total_lung_voxels = np.sum(lung_region)

    if total_lung_voxels == 0:
        return None

    # GGO: HU -700 to -500
    ggo_mask = ((ct_array > -700) & (ct_array <= -500)) & lung_region
    ggo_voxels = np.sum(ggo_mask)
    ggo_percentage = (ggo_voxels / total_lung_voxels) * 100

    # Consolidation: HU > -300
    cons_mask = (ct_array > -300) & lung_region
    cons_voxels = np.sum(cons_mask)
    cons_percentage = (cons_voxels / total_lung_voxels) * 100

    # Bilateral involvement
    right_lung = lung_mask_array == 1
    left_lung = lung_mask_array == 2

    ggo_right = np.sum(ggo_mask & right_lung) > 0
    ggo_left = np.sum(ggo_mask & left_lung) > 0
    bilateral = ggo_right and ggo_left

    return {
        'ggo_percentage': float(ggo_percentage),
        'consolidation_percentage': float(cons_percentage),
        'total_lesion_percentage': float(ggo_percentage + cons_percentage),
        'bilateral_involvement': bilateral,
        'ggo_volume_ml': float(ggo_voxels * voxel_volume_ml),
        'consolidation_volume_ml': float(cons_voxels * voxel_volume_ml),
    }


def classify_rule_based(features):
    """Rule-based COVID-19 classification"""

    if features is None:
        return {
            'covid_likelihood': 'UNKNOWN',
            'covid_probability': 0,
            'severity': 'UNKNOWN'
        }

    score = 0

    # GGO scoring
    ggo_pct = features['ggo_percentage']
    if ggo_pct > 25:
        score += 3
    elif ggo_pct > 10:
        score += 2
    elif ggo_pct > 5:
        score += 1

    # Consolidation scoring
    cons_pct = features['consolidation_percentage']
    if cons_pct > 15:
        score += 2
    elif cons_pct > 5:
        score += 1

    # Bilateral involvement
    if features['bilateral_involvement']:
        score += 2

    # Determine likelihood
    if score >= 5:
        likelihood = 'HIGH'
        probability = min(85 + (score - 5) * 3, 95)
    elif score >= 3:
        likelihood = 'MODERATE'
        probability = 50 + (score - 3) * 10
    elif score >= 1:
        likelihood = 'LOW'
        probability = 20 + (score - 1) * 15
    else:
        likelihood = 'VERY_LOW'
        probability = 5

    # Determine severity
    total_lesion = ggo_pct + cons_pct
    if total_lesion > 50:
        severity = 'SEVERE'
    elif total_lesion > 25:
        severity = 'MODERATE'
    elif total_lesion > 5:
        severity = 'MILD'
    else:
        severity = 'MINIMAL'

    return {
        'covid_likelihood': likelihood,
        'covid_probability': int(probability),
        'severity': severity,
        'score': score
    }


def covid_detect(patient_id: str):
    """Run COVID-19 detection using rule-based method"""
    print(f"\n{'='*60}")
    print(f"COVID-19 DETECTION: {patient_id}")
    print(f"{'='*60}")

    try:
        # Paths
        ct_array_file = Path(f"/mnt/data/covid_inputs/week_current/{patient_id}/ct_array.npy")
        lung_mask_file = Path(f"/mnt/data/covid_inputs/week_current/{patient_id}/lung_mask.nii.gz")
        spacing_file = Path(f"/mnt/data/covid_inputs/week_current/{patient_id}/spacing.npy")

        output_dir = Path(f"/mnt/data/covid_outputs/week_current/{patient_id}")
        output_dir.mkdir(parents=True, exist_ok=True)

        results_file = output_dir / "covid_results.json"
        features_file = output_dir / "features.json"

        print(f"CT array: {ct_array_file}")
        print(f"Lung mask: {lung_mask_file}")
        print(f"Output: {results_file}")

        # Load data
        print("[Step 1/3] Loading data...")
        ct_array = np.load(ct_array_file)
        lung_mask = sitk.GetArrayFromImage(sitk.ReadImage(str(lung_mask_file)))
        spacing = np.load(spacing_file)

        print(f"  CT shape: {ct_array.shape}")
        print(f"  Mask shape: {lung_mask.shape}")

        # Extract features
        print("[Step 2/3] Extracting COVID-19 features...")
        start_time = time.time()

        features = extract_features(ct_array, lung_mask, spacing)

        if features is None:
            print("[ERROR] No lung tissue found!")
            return 1

        print(f"  GGO: {features['ggo_percentage']:.1f}%")
        print(f"  Consolidation: {features['consolidation_percentage']:.1f}%")
        print(f"  Bilateral: {features['bilateral_involvement']}")

        # Classify
        print("[Step 3/3] Running rule-based classification...")
        diagnosis = classify_rule_based(features)

        detection_time = time.time() - start_time

        print(f"\n[RESULTS]")
        print(f"  Likelihood: {diagnosis['covid_likelihood']}")
        print(f"  Probability: {diagnosis['covid_probability']}%")
        print(f"  Severity: {diagnosis['severity']}")
        print(f"  Detection time: {detection_time:.2f}s")

        # Save results
        results = {
            'patient_id': patient_id,
            'method': 'rule_based',
            'diagnosis': diagnosis,
            'features': features,
            'inference_time': detection_time
        }

        with open(results_file, 'w') as f:
            json.dump(results, f, indent=2)

        with open(features_file, 'w') as f:
            json.dump(features, f, indent=2)

        print(f"\n[OK] Saved results: {results_file}")
        print(f"[OK] COVID-19 detection complete!")
        return 0

    except Exception as e:
        print(f"[ERROR] COVID-19 detection failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python covid_detect.py <patient_id>")
        sys.exit(1)

    patient_id = sys.argv[1]
    sys.exit(covid_detect(patient_id))
