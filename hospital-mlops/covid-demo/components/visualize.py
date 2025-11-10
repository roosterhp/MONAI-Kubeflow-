"""
Visualize Component: Create COVID-19 detection visualization
Input: CT scan, lung mask, COVID detection results
Output: full_comparison_{patient_id}.png (2x3 grid visualization)
"""

import sys
import numpy as np
import SimpleITK as sitk
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import json
from pathlib import Path


def create_visualization(patient_id: str):
    """
    Create COVID-19 detection visualization

    Layout: 2x3 grid
    Row 1: CT Scan | Lung Mask | COVID Overlay
    Row 2: Metrics | Features | Decision
    """
    print(f"\n{'='*60}")
    print(f"VISUALIZATION: {patient_id}")
    print(f"{'='*60}")

    try:
        # Paths
        ct_array_file = Path(f"/mnt/data/covid_inputs/week_current/{patient_id}/ct_array.npy")
        lung_mask_file = Path(f"/mnt/data/covid_inputs/week_current/{patient_id}/lung_mask.nii.gz")
        results_file = Path(f"/mnt/data/covid_outputs/week_current/{patient_id}/covid_results.json")
        features_file = Path(f"/mnt/data/covid_outputs/week_current/{patient_id}/features.json")

        output_dir = Path(f"/mnt/data/covid_outputs/week_current/{patient_id}")
        output_file = output_dir / f"full_comparison_{patient_id}.png"

        print(f"CT array: {ct_array_file}")
        print(f"Results: {results_file}")
        print(f"Output: {output_file}")

        # Load data
        print("[Step 1/4] Loading data...")
        ct_array = np.load(ct_array_file)
        lung_mask = sitk.GetArrayFromImage(sitk.ReadImage(str(lung_mask_file)))

        with open(results_file, 'r') as f:
            results = json.load(f)

        with open(features_file, 'r') as f:
            features = json.load(f)

        diagnosis = results['diagnosis']

        print(f"  CT shape: {ct_array.shape}")
        print(f"  Diagnosis: {diagnosis['covid_likelihood']}")

        # Find best slice (middle slice with lung tissue)
        print("[Step 2/4] Finding optimal slice...")
        lung_slices = []
        for i in range(ct_array.shape[0]):
            lung_count = np.sum(lung_mask[i] > 0)
            if lung_count > 0:
                lung_slices.append((i, lung_count))

        if lung_slices:
            # Get slice with most lung tissue
            slice_idx = max(lung_slices, key=lambda x: x[1])[0]
        else:
            slice_idx = ct_array.shape[0] // 2

        print(f"  Selected slice: {slice_idx}/{ct_array.shape[0]}")

        # Create visualization
        print("[Step 3/4] Creating visualization...")

        fig = plt.figure(figsize=(22, 12))
        gs = fig.add_gridspec(2, 3, hspace=0.35, wspace=0.3)

        ct_slice = ct_array[slice_idx]
        lung_slice = lung_mask[slice_idx]

        # === Row 1, Col 1: CT Scan ===
        ax1 = fig.add_subplot(gs[0, 0])
        ax1.imshow(ct_slice, cmap='gray', vmin=-1000, vmax=500)
        ax1.set_title(f'CT Scan - {patient_id}\\nAxial Slice {slice_idx}',
                      fontsize=16, fontweight='bold')
        ax1.axis('off')

        # === Row 1, Col 2: Lung Mask ===
        ax2 = fig.add_subplot(gs[0, 1])
        ax2.imshow(ct_slice, cmap='gray', vmin=-1000, vmax=500)

        # Overlay lung mask
        lung_colored = np.zeros((*lung_slice.shape, 3))
        lung_colored[lung_slice == 1] = [0, 1, 0]  # Right lung: green
        lung_colored[lung_slice == 2] = [0, 0.7, 1]  # Left lung: cyan

        ax2.imshow(lung_colored, alpha=0.4)
        ax2.set_title('Lung Segmentation (LungMask)',
                      fontsize=16, fontweight='bold')
        ax2.axis('off')

        # === Row 1, Col 3: COVID Overlay ===
        ax3 = fig.add_subplot(gs[0, 2])
        ax3.imshow(ct_slice, cmap='gray', vmin=-1000, vmax=500)

        # Create COVID overlay based on HU thresholds
        lung_roi = ct_slice.copy().astype(np.float32)
        lung_roi[lung_slice == 0] = np.nan

        # GGO: HU -700 to -500 (yellow)
        ggo_mask = ((lung_roi > -700) & (lung_roi <= -500)) & (lung_slice > 0)

        # Consolidation: HU > -300 (red)
        cons_mask = (lung_roi > -300) & (lung_slice > 0)

        if ggo_mask.sum() > 0:
            ax3.contourf(ggo_mask, levels=[0.5, 1.5], colors=['yellow'], alpha=0.5)
        if cons_mask.sum() > 0:
            ax3.contourf(cons_mask, levels=[0.5, 1.5], colors=['red'], alpha=0.6)

        # Title with color based on likelihood
        title_color = {
            'HIGH': 'red',
            'MODERATE': 'orange',
            'LOW': 'green',
            'VERY_LOW': 'green'
        }
        ax3.set_title(
            f'COVID-19 Detection\\n{diagnosis["covid_likelihood"]} ({diagnosis["covid_probability"]}%)',
            fontsize=16,
            fontweight='bold',
            color=title_color.get(diagnosis['covid_likelihood'], 'black')
        )
        ax3.axis('off')

        # === Row 2, Col 1: Metrics ===
        ax4 = fig.add_subplot(gs[1, 0])
        ax4.axis('off')

        metrics_text = "COVID-19 METRICS\\n"
        metrics_text += "="*40 + "\\n\\n"
        metrics_text += f"Ground-Glass Opacity (GGO):\\n"
        metrics_text += f"  Percentage: {features['ggo_percentage']:.1f}%\\n"
        metrics_text += f"  Volume: {features['ggo_volume_ml']:.1f} mL\\n\\n"
        metrics_text += f"Consolidation:\\n"
        metrics_text += f"  Percentage: {features['consolidation_percentage']:.1f}%\\n"
        metrics_text += f"  Volume: {features['consolidation_volume_ml']:.1f} mL\\n\\n"
        metrics_text += f"Total Lesion: {features['total_lesion_percentage']:.1f}%\\n"
        metrics_text += f"Bilateral: {'Yes' if features['bilateral_involvement'] else 'No'}\\n"

        ax4.text(0.05, 0.95, metrics_text,
                 transform=ax4.transAxes,
                 fontsize=12,
                 verticalalignment='top',
                 family='monospace',
                 bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.9))

        # === Row 2, Col 2: Features Breakdown ===
        ax5 = fig.add_subplot(gs[1, 1])
        ax5.axis('off')

        features_text = "FEATURE ANALYSIS\\n"
        features_text += "="*40 + "\\n\\n"
        features_text += "HU-based Classification:\\n"
        features_text += f"  GGO:   HU -700 to -500\\n"
        features_text += f"  Cons:  HU > -300\\n\\n"
        features_text += "Detection Method:\\n"
        features_text += f"  Rule-based classifier\\n"
        features_text += f"  LungMask R231 segmentation\\n\\n"
        features_text += "Inference Time:\\n"
        features_text += f"  {results['inference_time']:.2f} seconds\\n"

        ax5.text(0.05, 0.95, features_text,
                 transform=ax5.transAxes,
                 fontsize=12,
                 verticalalignment='top',
                 family='monospace',
                 bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.9))

        # === Row 2, Col 3: Clinical Decision ===
        ax6 = fig.add_subplot(gs[1, 2])
        ax6.axis('off')

        # Decision box color
        decision_color = {
            'HIGH': '#ffcccc',      # Light red
            'MODERATE': '#fff4cc',  # Light orange
            'LOW': '#ccffcc',       # Light green
            'VERY_LOW': '#ccffcc'
        }

        decision_text = "CLINICAL ASSESSMENT\\n"
        decision_text += "="*40 + "\\n\\n"
        decision_text += f"COVID-19 Likelihood:\\n"
        decision_text += f"  {diagnosis['covid_likelihood']}\\n\\n"
        decision_text += f"Probability:\\n"
        decision_text += f"  {diagnosis['covid_probability']}%\\n\\n"
        decision_text += f"Severity:\\n"
        decision_text += f"  {diagnosis['severity']}\\n\\n"

        # Recommendation
        if diagnosis['covid_likelihood'] in ['HIGH', 'MODERATE']:
            decision_text += "Recommendation:\\n"
            decision_text += "  ⚠ Further clinical\\n"
            decision_text += "    evaluation recommended\\n"
        else:
            decision_text += "Recommendation:\\n"
            decision_text += "  ✓ Low suspicion\\n"
            decision_text += "    Monitor as needed\\n"

        bg_color = decision_color.get(diagnosis['covid_likelihood'], 'white')
        ax6.text(0.05, 0.95, decision_text,
                 transform=ax6.transAxes,
                 fontsize=12,
                 verticalalignment='top',
                 family='monospace',
                 bbox=dict(boxstyle='round', facecolor=bg_color, alpha=0.9))

        # Overall title
        fig.suptitle(
            f'COVID-19 Detection Pipeline - Kubeflow\\nPatient: {patient_id}',
            fontsize=18,
            fontweight='bold'
        )

        # Legend
        from matplotlib.patches import Patch
        legend_elements = [
            Patch(facecolor='yellow', alpha=0.5, label='GGO (Ground-Glass Opacity)'),
            Patch(facecolor='red', alpha=0.6, label='Consolidation'),
            Patch(facecolor='green', alpha=0.4, label='Right Lung'),
            Patch(facecolor='cyan', alpha=0.4, label='Left Lung')
        ]
        fig.legend(handles=legend_elements,
                   loc='lower center',
                   ncol=4,
                   fontsize=11,
                   frameon=True)

        plt.tight_layout()

        # Save
        print("[Step 4/4] Saving visualization...")
        plt.savefig(output_file, dpi=150, bbox_inches='tight', facecolor='white')
        plt.close()

        file_size = output_file.stat().st_size / (1024 * 1024)
        print(f"  Saved: {output_file}")
        print(f"  Size: {file_size:.2f} MB")

        print(f"[OK] Visualization complete!")
        return 0

    except Exception as e:
        print(f"[ERROR] Visualization failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python visualize.py <patient_id>")
        sys.exit(1)

    patient_id = sys.argv[1]
    sys.exit(create_visualization(patient_id))
