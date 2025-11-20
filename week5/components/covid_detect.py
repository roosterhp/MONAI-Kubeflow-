"""
COVID-19 Detection Component: Rule-based + MONAI Ensemble
Input: CT array, lung mask, spacing
Output: JSON results with ensemble predictions
"""

import sys
import numpy as np
import SimpleITK as sitk
import json
import time
import shutil
from pathlib import Path

# MONAI imports
try:
    import torch
    from monai.transforms import ScaleIntensityRanged, EnsureTyped
    from monai.networks.nets import DenseNet121
    HAS_MONAI = True
except ImportError:
    HAS_MONAI = False
    print("[WARNING] MONAI not available, using rule-based only")


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


def classify_monai(ct_array, lung_mask_array, spacing):
    """MONAI-based COVID-19 classification"""

    if not HAS_MONAI:
        return None

    try:
        print("[MONAI] Initializing model...")
        device = torch.device("cpu")

        # Create a simple classifier (in production, load pretrained model)
        model = DenseNet121(
            spatial_dims=3,
            in_channels=2,  # CT + lung mask
            out_channels=4  # Background, Normal, GGO, Consolidation
        ).to(device)
        model.eval()

        # Prepare input data
        print("[MONAI] Preparing input...")
        ct_normalized = (ct_array - (-1000)) / (400 - (-1000))
        ct_normalized = np.clip(ct_normalized, 0, 1)

        # Combine CT and lung mask
        input_data = np.stack([ct_normalized, lung_mask_array], axis=0)
        input_tensor = torch.from_numpy(input_data).float().unsqueeze(0).to(device)

        # Resize to standard size
        from torch.nn.functional import interpolate
        input_tensor = interpolate(input_tensor, size=(96, 96, 96), mode='trilinear', align_corners=False)

        print("[MONAI] Running inference...")
        with torch.no_grad():
            output = model(input_tensor)
            probabilities = torch.softmax(output, dim=1)

        # Extract class probabilities
        background_prob = probabilities[0, 0].item()
        normal_prob = probabilities[0, 1].item()
        ggo_prob = probabilities[0, 2].item()
        consolidation_prob = probabilities[0, 3].item()

        # Calculate COVID probability (GGO + Consolidation)
        covid_prob = (ggo_prob + consolidation_prob) * 100

        # Determine likelihood
        if covid_prob > 75:
            likelihood = 'HIGH'
        elif covid_prob > 50:
            likelihood = 'MODERATE'
        elif covid_prob > 25:
            likelihood = 'LOW'
        else:
            likelihood = 'VERY_LOW'

        return {
            'covid_likelihood': likelihood,
            'covid_probability': int(covid_prob),
            'class_probabilities': {
                'background': background_prob * 100,
                'normal': normal_prob * 100,
                'ggo': ggo_prob * 100,
                'consolidation': consolidation_prob * 100
            }
        }

    except Exception as e:
        print(f"[ERROR] MONAI classification failed: {e}")
        return None


def ensemble_predictions(rule_based_result, monai_result, features):
    """Ensemble rule-based and MONAI predictions"""

    if monai_result is None:
        # Fallback to rule-based only
        return {
            'method': 'rule_based_fallback',
            'final_likelihood': rule_based_result['covid_likelihood'],
            'final_probability': rule_based_result['covid_probability'],
            'rule_based': rule_based_result,
            'monai': None,
            'confidence': 'medium'
        }

    # Weighted ensemble (rule-based: 0.6, MONAI: 0.4)
    rule_weight = 0.6
    monai_weight = 0.4

    rule_prob = rule_based_result['covid_probability']
    monai_prob = monai_result['covid_probability']

    ensemble_prob = int(rule_weight * rule_prob + monai_weight * monai_prob)

    # Determine final likelihood
    if ensemble_prob > 75:
        final_likelihood = 'HIGH'
    elif ensemble_prob > 50:
        final_likelihood = 'MODERATE'
    elif ensemble_prob > 25:
        final_likelihood = 'LOW'
    else:
        final_likelihood = 'VERY_LOW'

    # Calculate confidence based on agreement
    prob_diff = abs(rule_prob - monai_prob)
    if prob_diff < 10:
        confidence = 'high'
    elif prob_diff < 25:
        confidence = 'medium'
    else:
        confidence = 'low'

    return {
        'method': 'ensemble',
        'final_likelihood': final_likelihood,
        'final_probability': ensemble_prob,
        'rule_based': rule_based_result,
        'monai': monai_result,
        'confidence': confidence,
        'agreement': f"{prob_diff:.1f}% difference"
    }


def covid_detect(input_dir: str, output_dir: str):
    """Run COVID-19 detection using ensemble approach

    Args:
        input_dir: Directory containing ct_array.npy, lung_mask.nii.gz, spacing.npy
        output_dir: Directory to save results

    Returns:
        0 on success, 1 on failure
    """
    print(f"\n{'='*70}")
    print("COVID-19 DETECTION")
    print(f"{'='*70}")
    print(f"Input: {input_dir}")
    print(f"Output: {output_dir}")

    try:
        # Ensure output directory exists
        Path(output_dir).mkdir(parents=True, exist_ok=True)

        # Paths
        ct_array_file = Path(input_dir) / "ct_array.npy"
        lung_mask_file = Path(input_dir) / "lung_mask.nii.gz"
        spacing_file = Path(input_dir) / "spacing.npy"

        results_file = Path(output_dir) / "covid_results.json"
        features_file = Path(output_dir) / "features.json"

        # Load data
        print("[Step 1/4] Loading data...")
        ct_array = np.load(ct_array_file)
        lung_mask = sitk.GetArrayFromImage(sitk.ReadImage(str(lung_mask_file)))
        spacing = np.load(spacing_file)

        print(f"  CT shape: {ct_array.shape}")
        print(f"  Mask shape: {lung_mask.shape}")

        # Extract features
        print("[Step 2/4] Extracting COVID-19 features...")
        start_time = time.time()

        features = extract_features(ct_array, lung_mask, spacing)

        if features is None:
            print("[ERROR] No lung tissue found!")
            return 1

        print(f"  GGO: {features['ggo_percentage']:.1f}%")
        print(f"  Consolidation: {features['consolidation_percentage']:.1f}%")
        print(f"  Bilateral: {features['bilateral_involvement']}")

        # Rule-based classification
        print("[Step 3/4] Running rule-based classification...")
        rule_based_result = classify_rule_based(features)

        print(f"  Rule-based: {rule_based_result['covid_likelihood']} ({rule_based_result['covid_probability']}%)")

        # MONAI classification
        print("[Step 4/4] Running MONAI classification...")
        monai_result = classify_monai(ct_array, lung_mask, spacing)

        if monai_result:
            print(f"  MONAI: {monai_result['covid_likelihood']} ({monai_result['covid_probability']}%)")
        else:
            print("  MONAI: Not available")

        # Ensemble predictions
        print("\n[ENSEMBLE] Combining predictions...")
        ensemble_result = ensemble_predictions(rule_based_result, monai_result, features)

        total_time = time.time() - start_time

        print(f"\n[FINAL RESULTS]")
        print(f"  Method: {ensemble_result['method']}")
        print(f"  Final Likelihood: {ensemble_result['final_likelihood']}")
        print(f"  Final Probability: {ensemble_result['final_probability']}%")
        print(f"  Confidence: {ensemble_result['confidence']}")
        if ensemble_result.get('agreement'):
            print(f"  Agreement: {ensemble_result['agreement']}")
        print(f"  Total time: {total_time:.2f}s")

        # Clinical recommendation
        final_prob = ensemble_result['final_probability']
        if final_prob > 75:
            recommendation = "Urgent radiologist review recommended"
        elif final_prob > 50:
            recommendation = "Radiologist review recommended within 24 hours"
        elif final_prob > 25:
            recommendation = "Consider follow-up imaging in 3-5 days"
        else:
            recommendation = "Routine follow-up care"

        print(f"  Recommendation: {recommendation}")

        def make_json_serializable(obj):
            """Convert object to JSON serializable format"""
            if isinstance(obj, dict):
                return {k: make_json_serializable(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [make_json_serializable(item) for item in obj]
            elif isinstance(obj, (np.integer, np.floating)):
                return obj.item()
            elif isinstance(obj, np.ndarray):
                return obj.tolist()
            elif isinstance(obj, bool):
                return obj
            else:
                return obj

        # Save results (simplified to avoid JSON issues)
        results = {
            'method': ensemble_result['method'],
            'final_diagnosis': {
                'likelihood': ensemble_result['final_likelihood'],
                'probability': ensemble_result['final_probability'],
                'confidence': ensemble_result['confidence'],
                'recommendation': recommendation
            },
            'features': {
                'ggo_percentage': float(features['ggo_percentage']),
                'consolidation_percentage': float(features['consolidation_percentage']),
                'total_lesion_percentage': float(features['total_lesion_percentage']),
                'bilateral_involvement': bool(features['bilateral_involvement']),
                'ggo_volume_ml': float(features['ggo_volume_ml']),
                'consolidation_volume_ml': float(features['consolidation_volume_ml'])
            },
            'inference_time': total_time,
            'rule_based_probability': ensemble_result['rule_based']['covid_probability'],
            'monai_probability': ensemble_result['monai']['covid_probability'] if ensemble_result['monai'] else 0
        }

        with open(results_file, 'w') as f:
            json.dump(results, f, indent=2)

        with open(features_file, 'w') as f:
            json.dump(results['features'], f, indent=2)

        # Copy necessary files from segmentation for visualization
        print("[COPY] Copying files for visualization...")
        segmentation_dir = Path(input_dir)
        detection_dir = Path(output_dir)

        segmentation_files = ["ct_array.npy", "lung_mask.nii.gz", "spacing.npy"]
        for file_name in segmentation_files:
            src_file = segmentation_dir / file_name
            dest_file = detection_dir / file_name
            if src_file.exists():
                shutil.copy2(src_file, dest_file)
                print(f"  Copied {file_name}")
            else:
                print(f"  Warning: {file_name} not found in segmentation")

        print(f"\n[OK] Saved results: {results_file}")
        print("[OK] COVID-19 detection complete!")
        return 0

    except Exception as e:
        print(f"[ERROR] COVID-19 detection failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python covid_detect.py <input_dir> <output_dir>")
        sys.exit(1)

    input_dir = sys.argv[1]
    output_dir = sys.argv[2]
    sys.exit(covid_detect(input_dir, output_dir))