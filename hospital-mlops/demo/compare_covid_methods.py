"""
COVID-19 Detection Comparison: Rule-based vs MONAI

This script runs BOTH methods on the same CT scan and generates:
1. Side-by-side results
2. Agreement/disagreement analysis
3. Visualization comparison
4. Performance metrics
5. Decision recommendations
"""

import numpy as np
import SimpleITK as sitk
import matplotlib.pyplot as plt
from pathlib import Path
from lungmask import LMInferer
import time
import json

# Import both classifiers
from feature_extractor import LungFeatureExtractor
from covid19_detection_demo import COVID19Classifier
try:
    from monai_covid_classifier import MONAICOVIDClassifier
    MONAI_AVAILABLE = True
except:
    MONAI_AVAILABLE = False
    print("[WARNING] MONAI classifier not available")


def run_both_methods(ct_array, lung_mask_array, spacing):
    """
    Run both Rule-based and MONAI methods

    Returns:
        rule_based_results, monai_results
    """
    results = {}

    # ================== METHOD 1: RULE-BASED ==================
    print("\n" + "="*70)
    print("METHOD 1: RULE-BASED COVID-19 DETECTION")
    print("="*70)

    start_time = time.time()

    # Feature extraction
    print("[1/2] Extracting HU-based features...")
    extractor = LungFeatureExtractor()
    features = extractor.extract(ct_array, lung_mask_array, spacing)
    print(f"  GGO: {features['ggo_percentage']:.1f}%")
    print(f"  Consolidation: {features['consolidation_percentage']:.1f}%")

    # Classification
    print("[2/2] Running rule-based classifier...")
    classifier = COVID19Classifier()
    rule_based_diagnosis = classifier.classify(features)

    rule_based_time = time.time() - start_time

    results['rule_based'] = {
        'diagnosis': rule_based_diagnosis,
        'features': features,
        'inference_time': rule_based_time
    }

    print(f"\n[RESULT] Rule-based:")
    print(f"  Likelihood: {rule_based_diagnosis['covid_likelihood']}")
    print(f"  Probability: {rule_based_diagnosis['covid_probability']}%")
    print(f"  Severity: {rule_based_diagnosis['severity']}")
    print(f"  Time: {rule_based_time:.1f}s")

    # ================== METHOD 2: MONAI ==================
    if MONAI_AVAILABLE:
        print("\n" + "="*70)
        print("METHOD 2: MONAI AI MODEL")
        print("="*70)

        start_time = time.time()

        try:
            # MONAI classification
            monai_classifier = MONAICOVIDClassifier()
            monai_diagnosis, monai_segmentation = monai_classifier.classify(
                ct_array, lung_mask_array, spacing
            )

            monai_time = time.time() - start_time

            results['monai'] = {
                'diagnosis': monai_diagnosis,
                'segmentation': monai_segmentation,
                'inference_time': monai_time
            }

            print(f"\n[RESULT] MONAI:")
            print(f"  Likelihood: {monai_diagnosis['covid_likelihood']}")
            print(f"  Probability: {monai_diagnosis['covid_probability']}%")
            print(f"  Severity: {monai_diagnosis['severity']}")
            print(f"  Time: {monai_time:.1f}s")

        except Exception as e:
            print(f"\n[ERROR] MONAI inference failed: {e}")
            results['monai'] = None
    else:
        print("\n[SKIP] MONAI method not available")
        results['monai'] = None

    return results


def compare_results(results):
    """
    Compare results from both methods

    Returns:
        comparison: Dictionary with comparison metrics
    """
    print("\n" + "="*70)
    print("COMPARISON ANALYSIS")
    print("="*70)

    if results['monai'] is None:
        print("\n[WARNING] MONAI results not available, skipping comparison")
        return None

    rule_diag = results['rule_based']['diagnosis']
    monai_diag = results['monai']['diagnosis']

    comparison = {}

    # 1. Agreement on likelihood
    rule_likelihood = rule_diag['covid_likelihood']
    monai_likelihood = monai_diag['covid_likelihood']

    comparison['likelihood_agreement'] = (rule_likelihood == monai_likelihood)

    print(f"\n[COMPARISON] COVID-19 Likelihood:")
    print(f"  Rule-based: {rule_likelihood}")
    print(f"  MONAI:      {monai_likelihood}")
    if comparison['likelihood_agreement']:
        print(f"  -> [OK] AGREEMENT")
    else:
        print(f"  -> [X] DISAGREEMENT")

    # 2. Probability difference
    prob_diff = abs(rule_diag['covid_probability'] - monai_diag['covid_probability'])
    comparison['probability_difference'] = prob_diff

    print(f"\n[COMPARISON] COVID-19 Probability:")
    print(f"  Rule-based: {rule_diag['covid_probability']}%")
    print(f"  MONAI:      {monai_diag['covid_probability']}%")
    print(f"  Difference: {prob_diff:.1f}%")

    if prob_diff < 10:
        print(f"  -> [OK] CLOSE AGREEMENT (<10%)")
    elif prob_diff < 20:
        print(f"  -> [WARNING] MODERATE DIFFERENCE (10-20%)")
    else:
        print(f"  -> [X] LARGE DIFFERENCE (>20%)")

    # 3. Severity agreement
    rule_severity = rule_diag['severity']
    monai_severity = monai_diag['severity']

    comparison['severity_agreement'] = (rule_severity == monai_severity)

    print(f"\n[COMPARISON] Severity:")
    print(f"  Rule-based: {rule_severity}")
    print(f"  MONAI:      {monai_severity}")
    if comparison['severity_agreement']:
        print(f"  -> [OK] AGREEMENT")
    else:
        print(f"  -> [X] DISAGREEMENT")

    # 4. GGO/Consolidation metrics
    rule_ggo = results['rule_based']['features']['ggo_percentage']
    monai_ggo = monai_diag['ggo_percentage']

    rule_cons = results['rule_based']['features']['consolidation_percentage']
    monai_cons = monai_diag['consolidation_percentage']

    comparison['ggo_difference'] = abs(rule_ggo - monai_ggo)
    comparison['consolidation_difference'] = abs(rule_cons - monai_cons)

    print(f"\n[COMPARISON] Ground-Glass Opacity (GGO):")
    print(f"  Rule-based: {rule_ggo:.1f}%")
    print(f"  MONAI:      {monai_ggo:.1f}%")
    print(f"  Difference: {comparison['ggo_difference']:.1f}%")

    print(f"\n[COMPARISON] Consolidation:")
    print(f"  Rule-based: {rule_cons:.1f}%")
    print(f"  MONAI:      {monai_cons:.1f}%")
    print(f"  Difference: {comparison['consolidation_difference']:.1f}%")

    # 5. Inference time
    rule_time = results['rule_based']['inference_time']
    monai_time = results['monai']['inference_time']

    comparison['time_difference'] = monai_time - rule_time

    print(f"\n[COMPARISON] Inference Time:")
    print(f"  Rule-based: {rule_time:.1f}s")
    print(f"  MONAI:      {monai_time:.1f}s")
    if monai_time > rule_time:
        print(f"  MONAI slower by: {comparison['time_difference']:.1f}s")
    else:
        print(f"  MONAI faster by: {-comparison['time_difference']:.1f}s")

    # 6. Overall agreement score
    agreement_score = 0
    if comparison['likelihood_agreement']:
        agreement_score += 40
    if prob_diff < 15:
        agreement_score += 30
    if comparison['severity_agreement']:
        agreement_score += 20
    if comparison['ggo_difference'] < 10 and comparison['consolidation_difference'] < 10:
        agreement_score += 10

    comparison['agreement_score'] = agreement_score

    print(f"\n[OVERALL AGREEMENT]")
    print(f"  Score: {agreement_score}/100")
    if agreement_score >= 80:
        print(f"  -> [OK] HIGH AGREEMENT (Methods consistent)")
    elif agreement_score >= 60:
        print(f"  -> [WARNING] MODERATE AGREEMENT (Some differences)")
    else:
        print(f"  -> [X] LOW AGREEMENT (Significant disagreement)")

    return comparison


def create_comparison_visualization(ct_array, lung_mask_array, results, output_path):
    """
    Create side-by-side visualization comparing both methods

    Layout: 2x3 grid
    Row 1: CT | Rule-based Overlay | MONAI Overlay
    Row 2: Metrics Comparison | Confusion | Decision
    """
    if results['monai'] is None:
        print("[SKIP] Visualization requires MONAI results")
        return

    fig = plt.figure(figsize=(22, 12))
    gs = fig.add_gridspec(2, 3, hspace=0.35, wspace=0.3)

    # Get middle slice
    slice_idx = ct_array.shape[0] // 2
    ct_slice = ct_array[slice_idx]
    lung_slice = lung_mask_array[slice_idx]

    rule_diag = results['rule_based']['diagnosis']
    monai_diag = results['monai']['diagnosis']
    monai_seg = results['monai']['segmentation']

    # === Row 1, Col 1: Original CT ===
    ax1 = fig.add_subplot(gs[0, 0])
    ax1.imshow(ct_slice, cmap='gray', vmin=-1000, vmax=500)
    ax1.set_title('CT Scan - Axial View', fontsize=16, fontweight='bold')
    ax1.axis('off')

    # === Row 1, Col 2: Rule-based Pattern ===
    ax2 = fig.add_subplot(gs[0, 1])
    ax2.imshow(ct_slice, cmap='gray', vmin=-1000, vmax=500)

    # Overlay rule-based patterns (HU-based)
    lung_roi = ct_slice.copy().astype(np.float32)
    lung_roi[lung_slice == 0] = np.nan

    ggo_mask = ((lung_roi > -700) & (lung_roi <= -500)) & (lung_slice > 0)
    cons_mask = (lung_roi > -300) & (lung_slice > 0)

    if ggo_mask.sum() > 0:
        ax2.contourf(ggo_mask, levels=[0.5, 1.5], colors=['yellow'], alpha=0.5)
    if cons_mask.sum() > 0:
        ax2.contourf(cons_mask, levels=[0.5, 1.5], colors=['red'], alpha=0.6)

    title_color = {'HIGH': 'red', 'MODERATE': 'orange', 'LOW': 'green', 'LOW-MODERATE': 'orange'}
    ax2.set_title(
        f'Rule-based: {rule_diag["covid_likelihood"]} ({rule_diag["covid_probability"]}%)',
        fontsize=16,
        fontweight='bold',
        color=title_color.get(rule_diag['covid_likelihood'], 'black')
    )
    ax2.axis('off')

    # === Row 1, Col 3: MONAI Segmentation ===
    ax3 = fig.add_subplot(gs[0, 2])
    ax3.imshow(ct_slice, cmap='gray', vmin=-1000, vmax=500)

    monai_slice = monai_seg[slice_idx]

    # Overlay MONAI classes
    ggo_monai = (monai_slice == 2)
    cons_monai = (monai_slice == 3)

    if ggo_monai.sum() > 0:
        ax3.contourf(ggo_monai, levels=[0.5, 1.5], colors=['yellow'], alpha=0.5)
    if cons_monai.sum() > 0:
        ax3.contourf(cons_monai, levels=[0.5, 1.5], colors=['red'], alpha=0.6)

    ax3.set_title(
        f'MONAI: {monai_diag["covid_likelihood"]} ({monai_diag["covid_probability"]}%)',
        fontsize=16,
        fontweight='bold',
        color=title_color.get(monai_diag['covid_likelihood'], 'black')
    )
    ax3.axis('off')

    # === Row 2, Col 1: Metrics Comparison ===
    ax4 = fig.add_subplot(gs[1, 0])
    ax4.axis('off')

    rule_features = results['rule_based']['features']

    metrics_text = "METRICS COMPARISON\n"
    metrics_text += "="*35 + "\n\n"
    metrics_text += "Ground-Glass Opacity (GGO):\n"
    metrics_text += f"  Rule-based: {rule_features['ggo_percentage']:.1f}%\n"
    metrics_text += f"  MONAI:      {monai_diag['ggo_percentage']:.1f}%\n"
    metrics_text += f"  Δ: {abs(rule_features['ggo_percentage'] - monai_diag['ggo_percentage']):.1f}%\n\n"

    metrics_text += "Consolidation:\n"
    metrics_text += f"  Rule-based: {rule_features['consolidation_percentage']:.1f}%\n"
    metrics_text += f"  MONAI:      {monai_diag['consolidation_percentage']:.1f}%\n"
    metrics_text += f"  Δ: {abs(rule_features['consolidation_percentage'] - monai_diag['consolidation_percentage']):.1f}%\n\n"

    metrics_text += "Inference Time:\n"
    metrics_text += f"  Rule-based: {results['rule_based']['inference_time']:.1f}s\n"
    metrics_text += f"  MONAI:      {results['monai']['inference_time']:.1f}s\n"

    ax4.text(0.05, 0.95, metrics_text,
             transform=ax4.transAxes,
             fontsize=11,
             verticalalignment='top',
             family='monospace',
             bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.9))

    # === Row 2, Col 2: Agreement Analysis ===
    ax5 = fig.add_subplot(gs[1, 1])
    ax5.axis('off')

    # Agreement metrics
    likelihood_match = (rule_diag['covid_likelihood'] == monai_diag['covid_likelihood'])
    severity_match = (rule_diag['severity'] == monai_diag['severity'])
    prob_diff = abs(rule_diag['covid_probability'] - monai_diag['covid_probability'])

    agreement_text = "AGREEMENT ANALYSIS\n"
    agreement_text += "="*35 + "\n\n"
    agreement_text += f"Likelihood:\n"
    agreement_text += f"  {'[OK] MATCH' if likelihood_match else '[X] DIFFER'}\n\n"

    agreement_text += f"Severity:\n"
    agreement_text += f"  {'[OK] MATCH' if severity_match else '[X] DIFFER'}\n\n"

    agreement_text += f"Probability:\n"
    agreement_text += f"  Diff = {prob_diff:.1f}%\n"
    if prob_diff < 10:
        agreement_text += f"  [OK] Close\n\n"
    else:
        agreement_text += f"  [WARN] Different\n\n"

    # Overall
    if likelihood_match and severity_match and prob_diff < 15:
        agreement_text += "OVERALL: [OK] HIGH AGREEMENT\n"
        bg_color = 'lightgreen'
    elif likelihood_match or severity_match:
        agreement_text += "OVERALL: [WARN] PARTIAL AGREEMENT\n"
        bg_color = 'lightyellow'
    else:
        agreement_text += "OVERALL: [X] DISAGREEMENT\n"
        bg_color = 'mistyrose'

    ax5.text(0.05, 0.95, agreement_text,
             transform=ax5.transAxes,
             fontsize=11,
             verticalalignment='top',
             family='monospace',
             bbox=dict(boxstyle='round', facecolor=bg_color, alpha=0.9))

    # === Row 2, Col 3: Decision Recommendation ===
    ax6 = fig.add_subplot(gs[1, 2])
    ax6.axis('off')

    decision_text = "CLINICAL DECISION\n"
    decision_text += "="*35 + "\n\n"

    # Decision logic
    if likelihood_match and rule_diag['covid_likelihood'] in ['HIGH', 'MODERATE']:
        decision_text += "[OK] BOTH METHODS AGREE\n"
        decision_text += f"  COVID-19: {rule_diag['covid_likelihood']}\n\n"
        decision_text += "RECOMMENDATION:\n"
        decision_text += "  - RT-PCR testing\n"
        decision_text += "  - Isolation protocols\n"
        decision_text += "  - Clinical correlation\n"
        decision_color = 'mistyrose'

    elif not likelihood_match:
        decision_text += "[WARN] METHODS DISAGREE\n\n"
        decision_text += "RECOMMENDATION:\n"
        decision_text += "  - Radiologist review\n"
        decision_text += "  - Consider RT-PCR\n"
        decision_text += "  - Follow-up imaging\n"
        decision_text += "  - Clinical correlation\n"
        decision_color = 'lightyellow'

    else:
        decision_text += "[OK] BOTH METHODS AGREE\n"
        decision_text += f"  COVID-19: LOW\n\n"
        decision_text += "RECOMMENDATION:\n"
        decision_text += "  - Standard follow-up\n"
        decision_text += "  - RT-PCR if symptomatic\n"
        decision_color = 'lightgreen'

    ax6.text(0.05, 0.95, decision_text,
             transform=ax6.transAxes,
             fontsize=11,
             verticalalignment='top',
             family='monospace',
             bbox=dict(boxstyle='round', facecolor=decision_color, alpha=0.9))

    # Overall title
    fig.suptitle(
        'COVID-19 Detection Comparison: Rule-based vs MONAI AI',
        fontsize=18,
        fontweight='bold'
    )

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    print(f"\n[OK] Comparison visualization saved: {output_path}")
    plt.close()


def generate_recommendation(results, comparison):
    """
    Generate clinical recommendation based on both methods

    Returns:
        recommendation: Dictionary with recommendations
    """
    if results['monai'] is None:
        return{
            'method': 'rule_based_only',
            'recommendation': 'Use rule-based results (MONAI not available)'
        }

    rule_diag = results['rule_based']['diagnosis']
    monai_diag = results['monai']['diagnosis']

    recommendation = {}

    # Case 1: Both HIGH -> Strong COVID suspicion
    if rule_diag['covid_likelihood'] == 'HIGH' and monai_diag['covid_likelihood'] == 'HIGH':
        recommendation['confidence'] = 'VERY HIGH'
        recommendation['action'] = 'IMMEDIATE'
        recommendation['decision'] = 'Strong COVID-19 suspicion - Both methods agree'
        recommendation['next_steps'] = [
            'Immediate RT-PCR testing',
            'Initiate isolation protocols',
            'Monitor oxygen saturation',
            'Consider ICU admission if severe'
        ]

    # Case 2: One HIGH, one MODERATE -> Moderate-High suspicion
    elif 'HIGH' in [rule_diag['covid_likelihood'], monai_diag['covid_likelihood']]:
        recommendation['confidence'] = 'HIGH'
        recommendation['action'] = 'URGENT'
        recommendation['decision'] = 'COVID-19 likely - One method shows high suspicion'
        recommendation['next_steps'] = [
            'RT-PCR testing recommended',
            'Clinical correlation advised',
            'Isolation precautions',
            'Follow-up imaging in 7 days'
        ]

    # Case 3: Disagreement (one says HIGH/MODERATE, other says LOW)
    elif (rule_diag['covid_likelihood'] in ['HIGH', 'MODERATE'] and
          monai_diag['covid_likelihood'] == 'LOW') or \
         (monai_diag['covid_likelihood'] in ['HIGH', 'MODERATE'] and
          rule_diag['covid_likelihood'] == 'LOW'):
        recommendation['confidence'] = 'UNCERTAIN'
        recommendation['action'] = 'REVIEW'
        recommendation['decision'] = 'Methods disagree - Radiologist review required'
        recommendation['next_steps'] = [
            'Expert radiologist review',
            'RT-PCR if clinically indicated',
            'Consider follow-up CT',
            'Clinical correlation essential'
        ]

    # Case 4: Both LOW -> Low suspicion
    else:
        recommendation['confidence'] = 'HIGH'
        recommendation['action'] = 'ROUTINE'
        recommendation['decision'] = 'Low COVID-19 suspicion - Both methods agree'
        recommendation['next_steps'] = [
            'RT-PCR if symptoms persist',
            'Standard clinical follow-up',
            'Alternative diagnoses'
        ]

    return recommendation


def main():
    """Main comparison pipeline"""

    print("\n" + "="*70)
    print("COVID-19 DETECTION METHOD COMPARISON")
    print("Rule-based (HU Thresholds) vs MONAI (AI Model)")
    print("="*70)

    # Find test data
    data_dir = Path("./sample-data/Task06_Lung/imagesTr")
    image_files = sorted([f for f in data_dir.glob("*.nii.gz") if not f.name.startswith("._")])

    if len(image_files) == 0:
        print("\n[ERROR] No CT scans found!")
        return

    # Use first patient
    image_path = image_files[0]
    patient_id = image_path.stem

    print(f"\n[INFO] Patient: {patient_id}")
    print(f"[INFO] Loading CT scan...")

    # Load CT
    ct_scan = sitk.ReadImage(str(image_path))
    ct_array = sitk.GetArrayFromImage(ct_scan)
    spacing = ct_scan.GetSpacing()

    print(f"[INFO] CT shape: {ct_array.shape}")

    # Lung segmentation (shared by both methods)
    print("\n[LUNG SEGMENTATION] Using LungMask R231...")
    start_time = time.time()
    inferer = LMInferer(modelname='R231')
    lung_mask_array = inferer.apply(ct_scan)
    seg_time = time.time() - start_time
    print(f"[OK] Segmentation completed in {seg_time:.1f}s")

    # Run both methods
    results = run_both_methods(ct_array, lung_mask_array, spacing)

    # Compare results
    comparison = compare_results(results)

    # Generate recommendation
    recommendation = generate_recommendation(results, comparison)

    print("\n" + "="*70)
    print("CLINICAL RECOMMENDATION")
    print("="*70)
    print(f"\nConfidence: {recommendation['confidence']}")
    print(f"Action Level: {recommendation['action']}")
    print(f"\nDecision: {recommendation['decision']}")
    print(f"\nNext Steps:")
    for i, step in enumerate(recommendation['next_steps'], 1):
        print(f"  {i}. {step}")

    # Create visualization
    output_path = Path(f"comparison_{patient_id}.png")
    create_comparison_visualization(ct_array, lung_mask_array, results, output_path)

    # Save results to JSON
    results_json = {
        'patient_id': patient_id,
        'rule_based': {
            'likelihood': results['rule_based']['diagnosis']['covid_likelihood'],
            'probability': results['rule_based']['diagnosis']['covid_probability'],
            'severity': results['rule_based']['diagnosis']['severity'],
            'ggo_percentage': results['rule_based']['features']['ggo_percentage'],
            'consolidation_percentage': results['rule_based']['features']['consolidation_percentage'],
            'inference_time': results['rule_based']['inference_time']
        }
    }

    if results['monai'] is not None:
        results_json['monai'] = {
            'likelihood': results['monai']['diagnosis']['covid_likelihood'],
            'probability': results['monai']['diagnosis']['covid_probability'],
            'severity': results['monai']['diagnosis']['severity'],
            'ggo_percentage': results['monai']['diagnosis']['ggo_percentage'],
            'consolidation_percentage': results['monai']['diagnosis']['consolidation_percentage'],
            'inference_time': results['monai']['inference_time']
        }
        results_json['comparison'] = comparison

    results_json['recommendation'] = recommendation

    json_path = Path(f"comparison_{patient_id}.json")
    with open(json_path, 'w') as f:
        json.dump(results_json, f, indent=2)

    print(f"\n[OK] Results saved: {json_path}")

    print("\n" + "="*70)
    print("COMPARISON COMPLETE")
    print("="*70)
    print(f"\n[FILES]")
    print(f"  Visualization: {output_path}")
    print(f"  Results JSON: {json_path}")
    print("\n" + "="*70)


if __name__ == "__main__":
    main()
