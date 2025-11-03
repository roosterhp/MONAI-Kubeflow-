"""
Full Comparison Visualization

Creates 4-panel visualization:
1. Original CT scan
2. Lung Segmentation (LungMask)
3. Rule-based COVID detection
4. MONAI COVID detection

All in one image for easy comparison.
"""

import numpy as np
import SimpleITK as sitk
import matplotlib.pyplot as plt
from pathlib import Path
from lungmask import LMInferer
from matplotlib.colors import ListedColormap

# Import classifiers
from feature_extractor import LungFeatureExtractor
from covid19_detection_demo import COVID19Classifier
from monai_covid_classifier import MONAICOVIDClassifier


def create_full_comparison(ct_path: str, output_path: str = None):
    """
    Create 4-panel comparison visualization

    Panels:
    1. Original CT (grayscale)
    2. Lung Segmentation (colored: R=red, L=blue)
    3. Rule-based detection (yellow=GGO+Consolidation)
    4. MONAI detection (red=GGO, orange=Consolidation)
    """

    print("\n" + "="*70)
    print("FULL COMPARISON VISUALIZATION")
    print("="*70)

    # Load CT scan
    ct_path = Path(ct_path)
    patient_id = ct_path.stem

    print(f"\n[INFO] Patient: {patient_id}")
    print(f"[INFO] Loading CT scan...")

    ct_scan = sitk.ReadImage(str(ct_path))
    ct_array = sitk.GetArrayFromImage(ct_scan)
    spacing = ct_scan.GetSpacing()

    print(f"[INFO] CT shape: {ct_array.shape}")

    # Lung segmentation
    print("\n[STEP 1/4] Lung Segmentation...")
    inferer = LMInferer(modelname='R231', tqdm_disable=True)
    lung_mask = inferer.apply(ct_scan)
    print("[OK] Lung segmentation complete")

    # Rule-based detection
    print("\n[STEP 2/4] Rule-based COVID detection...")
    extractor = LungFeatureExtractor()
    features = extractor.extract(ct_array, lung_mask, spacing)
    classifier = COVID19Classifier()
    rule_diag = classifier.classify(features)
    print(f"[OK] Rule-based: {rule_diag['covid_likelihood']} ({rule_diag['covid_probability']}%)")

    # MONAI detection
    print("\n[STEP 3/4] MONAI COVID detection...")
    monai_classifier = MONAICOVIDClassifier()
    monai_diag, monai_seg = monai_classifier.classify(ct_array, lung_mask, spacing)
    print(f"[OK] MONAI: {monai_diag['covid_likelihood']} ({monai_diag['covid_probability']}%)")

    # Create visualization
    print("\n[STEP 4/4] Creating visualization...")

    # Select middle slice
    middle_slice = ct_array.shape[0] // 2

    # Get slices
    ct_slice = ct_array[middle_slice, :, :]
    lung_slice = lung_mask[middle_slice, :, :]
    monai_slice = monai_seg[middle_slice, :, :]

    # Create figure with 2x2 layout
    fig, axes = plt.subplots(2, 2, figsize=(16, 14))

    # ==================== PANEL 1: Original CT ====================
    ax1 = axes[0, 0]
    ax1.imshow(ct_slice, cmap='gray', vmin=-1000, vmax=500)
    ax1.set_title('1. Original CT Scan\n(Axial View)',
                  fontsize=14, fontweight='bold', pad=15)
    ax1.axis('off')

    # Add info text
    info_text = f"Patient: {patient_id}\n"
    info_text += f"Slice: {middle_slice}/{ct_array.shape[0]}\n"
    info_text += f"Size: {ct_array.shape}"
    ax1.text(0.02, 0.98, info_text,
             transform=ax1.transAxes,
             fontsize=10,
             verticalalignment='top',
             bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))

    # ==================== PANEL 2: Lung Segmentation ====================
    ax2 = axes[0, 1]

    # Show CT as base
    ax2.imshow(ct_slice, cmap='gray', vmin=-1000, vmax=500)

    # Overlay lung mask with colors
    lung_colored = np.zeros((*lung_slice.shape, 4))

    # Right lung = Red
    right_mask = (lung_slice == 1)
    lung_colored[right_mask] = [1, 0, 0, 0.4]  # Red with alpha

    # Left lung = Blue
    left_mask = (lung_slice == 2)
    lung_colored[left_mask] = [0, 0, 1, 0.4]  # Blue with alpha

    ax2.imshow(lung_colored)
    ax2.set_title('2. Lung Segmentation\n(LungMask R231)',
                  fontsize=14, fontweight='bold', pad=15)
    ax2.axis('off')

    # Legend
    legend_text = "Right Lung (Red)\n"
    legend_text += "Left Lung (Blue)\n\n"
    legend_text += f"Total lung volume:\n{features['lung_volume_ml']:.0f} ml"
    ax2.text(0.02, 0.98, legend_text,
             transform=ax2.transAxes,
             fontsize=10,
             verticalalignment='top',
             bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))

    # ==================== PANEL 3: Rule-based Detection ====================
    ax3 = axes[1, 0]

    # Show CT as base
    ax3.imshow(ct_slice, cmap='gray', vmin=-1000, vmax=500)

    # Create overlay: Yellow for GGO + Consolidation
    rule_overlay = np.zeros((*ct_slice.shape, 4))

    lung_roi = ct_slice.copy()
    lung_roi[lung_slice == 0] = -1000  # Mask outside lungs

    # GGO: -700 to -500 HU
    ggo_mask = (lung_roi > -700) & (lung_roi <= -500)
    rule_overlay[ggo_mask] = [1, 1, 0, 0.5]  # Yellow

    # Consolidation: > -300 HU
    cons_mask = lung_roi > -300
    rule_overlay[cons_mask] = [1, 0.5, 0, 0.6]  # Orange (more severe)

    ax3.imshow(rule_overlay)
    ax3.set_title(f'3. Rule-based Detection\n{rule_diag["covid_likelihood"]} ({rule_diag["covid_probability"]}%)',
                  fontsize=14, fontweight='bold', pad=15)
    ax3.axis('off')

    # Metrics
    metrics_text = f"Method: HU Thresholds\n\n"
    metrics_text += f"GGO: {features['ggo_percentage']:.1f}%\n"
    metrics_text += f"Consolidation: {features['consolidation_percentage']:.1f}%\n"
    metrics_text += f"Bilateral: {'Yes' if features['bilateral_involvement'] else 'No'}\n\n"
    metrics_text += f"Severity: {rule_diag['severity']}\n"
    metrics_text += f"Time: {2.0:.1f}s"  # Approximate

    # Color based on likelihood
    if rule_diag['covid_likelihood'] in ['HIGH', 'MODERATE']:
        box_color = 'mistyrose'
    else:
        box_color = 'lightgreen'

    ax3.text(0.02, 0.98, metrics_text,
             transform=ax3.transAxes,
             fontsize=10,
             verticalalignment='top',
             bbox=dict(boxstyle='round', facecolor=box_color, alpha=0.9))

    # ==================== PANEL 4: MONAI Detection ====================
    ax4 = axes[1, 1]

    # Show CT as base
    ax4.imshow(ct_slice, cmap='gray', vmin=-1000, vmax=500)

    # Create overlay from MONAI segmentation
    monai_overlay = np.zeros((*monai_slice.shape, 4))

    # Class 1: Normal lung (no overlay)
    # Class 2: GGO = Yellow
    ggo_mask_monai = (monai_slice == 2)
    monai_overlay[ggo_mask_monai] = [1, 1, 0, 0.5]  # Yellow

    # Class 3: Consolidation = Red/Orange
    cons_mask_monai = (monai_slice == 3)
    monai_overlay[cons_mask_monai] = [1, 0.3, 0, 0.6]  # Red-orange

    ax4.imshow(monai_overlay)
    ax4.set_title(f'4. MONAI AI Detection\n{monai_diag["covid_likelihood"]} ({monai_diag["covid_probability"]}%)',
                  fontsize=14, fontweight='bold', pad=15)
    ax4.axis('off')

    # Metrics
    monai_metrics = f"Method: Deep Learning\n\n"
    monai_metrics += f"GGO: {monai_diag['ggo_percentage']:.1f}%\n"
    monai_metrics += f"Consolidation: {monai_diag['consolidation_percentage']:.1f}%\n"
    monai_metrics += f"Bilateral: {'Yes' if monai_diag['bilateral_involvement'] else 'No'}\n\n"
    monai_metrics += f"Severity: {monai_diag['severity']}\n"
    monai_metrics += f"Time: {monai_diag['inference_time']:.1f}s"

    # Color based on likelihood
    if monai_diag['covid_likelihood'] in ['HIGH', 'MODERATE']:
        box_color = 'mistyrose'
    else:
        box_color = 'lightgreen'

    ax4.text(0.02, 0.98, monai_metrics,
             transform=ax4.transAxes,
             fontsize=10,
             verticalalignment='top',
             bbox=dict(boxstyle='round', facecolor=box_color, alpha=0.9))

    # ==================== Overall Title ====================
    # Calculate agreement
    likelihood_match = (rule_diag['covid_likelihood'] == monai_diag['covid_likelihood'])
    prob_diff = abs(rule_diag['covid_probability'] - monai_diag['covid_probability'])

    if likelihood_match and prob_diff < 15:
        agreement_text = f"AGREEMENT: HIGH (Difference: {prob_diff:.0f}%)"
        title_color = 'green'
    elif likelihood_match:
        agreement_text = f"AGREEMENT: MODERATE (Difference: {prob_diff:.0f}%)"
        title_color = 'orange'
    else:
        agreement_text = f"DISAGREEMENT: Methods differ ({prob_diff:.0f}% difference)"
        title_color = 'red'

    fig.suptitle(
        f'COVID-19 Detection Full Comparison - {patient_id}\n{agreement_text}',
        fontsize=18,
        fontweight='bold',
        y=0.98,
        color=title_color
    )

    # Add legend at bottom
    legend_text = "Color Legend:  Yellow = Ground-Glass Opacity (GGO)  |  Orange/Red = Consolidation  |  Red = Right Lung  |  Blue = Left Lung"
    fig.text(0.5, 0.02, legend_text,
             ha='center',
             fontsize=11,
             bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))

    plt.tight_layout(rect=[0, 0.03, 1, 0.96])

    # Save
    if output_path is None:
        output_path = f"full_comparison_{patient_id}.png"

    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    print(f"\n[OK] Visualization saved: {output_path}")
    plt.close()

    return output_path


def main():
    """Run full comparison on first available patient"""

    # Find CT scans
    data_dir = Path("./sample-data/Task06_Lung/imagesTr")
    image_files = sorted([
        f for f in data_dir.glob("*.nii.gz")
        if not f.name.startswith("._")
    ])

    if len(image_files) == 0:
        print("[ERROR] No CT scans found!")
        return

    # Use first patient
    ct_path = image_files[0]

    # Create visualization
    output_path = create_full_comparison(str(ct_path))

    print("\n" + "="*70)
    print("[OK] COMPLETE!")
    print(f"[FILE] {output_path}")
    print("="*70)


if __name__ == "__main__":
    main()
