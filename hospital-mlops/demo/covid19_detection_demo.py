"""
COVID-19 Detection Demo - Tạo trường hợp bệnh nhân COVID-19

Pipeline:
1. Load CT scan
2. Lung segmentation (LungMask R231)
3. Feature extraction
4. COVID-19 specific analysis
5. Comprehensive visualization

Output: PNG file với chẩn đoán COVID-19
"""

import numpy as np
import SimpleITK as sitk
import matplotlib.pyplot as plt
from pathlib import Path
from lungmask import LMInferer
import time

# Import our modules
from feature_extractor import LungFeatureExtractor


class COVID19Classifier:
    """
    COVID-19 specific classifier dựa trên đặc điểm CT scan

    COVID-19 CT characteristics:
    - Ground-glass opacities (GGO) - bilateral, peripheral
    - Consolidation
    - Crazy-paving pattern
    - Bilateral involvement
    - Peripheral distribution
    """

    def __init__(self):
        self.name = "COVID-19 Detection System"

    def classify(self, features):
        """
        Phân loại dựa trên features để phát hiện COVID-19

        COVID-19 indicators:
        - High GGO percentage (>15%)
        - Bilateral (both lungs affected)
        - Peripheral distribution
        - Moderate consolidation
        """

        # COVID-19 scoring
        covid_score = 0
        indicators = []

        # 1. Ground-glass opacity (strongest indicator)
        ggo_pct = features['ggo_percentage']
        if ggo_pct > 25:
            covid_score += 4
            indicators.append(f"High GGO: {ggo_pct:.1f}% (Severe)")
        elif ggo_pct > 15:
            covid_score += 3
            indicators.append(f"Moderate GGO: {ggo_pct:.1f}% (Typical)")
        elif ggo_pct > 8:
            covid_score += 2
            indicators.append(f"Mild GGO: {ggo_pct:.1f}%")

        # 2. Consolidation (secondary indicator)
        cons_pct = features['consolidation_percentage']
        if cons_pct > 15:
            covid_score += 2
            indicators.append(f"Consolidation: {cons_pct:.1f}% (Progressive)")
        elif cons_pct > 5:
            covid_score += 1
            indicators.append(f"Mild Consolidation: {cons_pct:.1f}%")

        # 3. Bilateral involvement (check both lungs)
        if features['bilateral_involvement']:
            covid_score += 2
            indicators.append("Bilateral lung involvement")

        # 4. Normal lung tissue reduction
        normal_pct = features['normal_lung_percentage']
        if normal_pct < 60:
            covid_score += 1
            indicators.append(f"Reduced normal tissue: {normal_pct:.1f}%")

        # 5. HU distribution shift
        hu_mean = features['hu_mean']
        if hu_mean > -800:  # Increased density
            covid_score += 1
            indicators.append(f"Increased lung density (HU: {hu_mean:.0f})")

        # Determine COVID-19 likelihood
        if covid_score >= 7:
            covid_likelihood = "HIGH"
            covid_probability = 85 + min(covid_score - 7, 5) * 3  # 85-100%
            severity = "SEVERE"
            color = "red"
        elif covid_score >= 5:
            covid_likelihood = "MODERATE"
            covid_probability = 65 + (covid_score - 5) * 10  # 65-85%
            severity = "MODERATE"
            color = "orange"
        elif covid_score >= 3:
            covid_likelihood = "LOW-MODERATE"
            covid_probability = 40 + (covid_score - 3) * 12.5  # 40-65%
            severity = "MILD"
            color = "yellow"
        else:
            covid_likelihood = "LOW"
            covid_probability = min(covid_score * 13, 40)  # 0-40%
            severity = "MINIMAL"
            color = "green"

        # Generate recommendations
        recommendations = []
        if covid_score >= 5:
            recommendations.append("Immediate RT-PCR testing recommended")
            recommendations.append("Isolation protocols should be initiated")
            recommendations.append("Monitor oxygen saturation closely")
            recommendations.append("Consider antiviral therapy if PCR positive")
            recommendations.append("Follow-up CT in 7-14 days")
        elif covid_score >= 3:
            recommendations.append("RT-PCR testing recommended")
            recommendations.append("Clinical correlation advised")
            recommendations.append("Monitor symptoms closely")
            recommendations.append("Follow-up CT if symptoms worsen")
        else:
            recommendations.append("RT-PCR if clinical suspicion remains")
            recommendations.append("Alternative diagnoses should be considered")
            recommendations.append("Standard clinical follow-up")

        # CT pattern classification
        if ggo_pct > 20 and cons_pct > 10:
            ct_pattern = "Mixed GGO + Consolidation (Progressive COVID-19)"
        elif ggo_pct > 15:
            ct_pattern = "Predominantly GGO (Typical Early COVID-19)"
        elif cons_pct > 15:
            ct_pattern = "Predominantly Consolidation (Advanced COVID-19)"
        else:
            ct_pattern = "Minimal findings (Low suspicion)"

        return {
            'covid_likelihood': covid_likelihood,
            'covid_probability': covid_probability,
            'covid_score': covid_score,
            'severity': severity,
            'color': color,
            'indicators': indicators,
            'recommendations': recommendations,
            'ct_pattern': ct_pattern,
            'num_indicators': len(indicators)
        }


def create_covid19_visualization(
    ct_array,
    lung_mask_array,
    features,
    diagnosis,
    patient_id,
    inference_time,
    spacing,
    output_path
):
    """
    Create COVID-19 specific visualization

    Layout: 2x3 grid
    Row 1: CT | Lung Mask | COVID Pattern Overlay
    Row 2: HU Distribution | Tissue Composition | COVID-19 Report
    """
    fig = plt.figure(figsize=(22, 13))
    gs = fig.add_gridspec(2, 3, hspace=0.35, wspace=0.3)

    # Get middle slice
    num_slices = ct_array.shape[0]
    slice_idx = num_slices // 2

    ct_slice = ct_array[slice_idx]
    lung_slice = lung_mask_array[slice_idx]

    # === Row 1, Col 1: Original CT ===
    ax1 = fig.add_subplot(gs[0, 0])
    ax1.imshow(ct_slice, cmap='gray', vmin=-1000, vmax=500)
    ax1.set_title('CT Scan - Axial View', fontsize=16, fontweight='bold', color='navy')
    ax1.axis('off')

    ax1.text(
        0.02, 0.98,
        f'Slice: {slice_idx}/{num_slices}\n'
        f'Spacing: {spacing[0]:.2f} mm',
        transform=ax1.transAxes,
        fontsize=11,
        verticalalignment='top',
        bbox=dict(boxstyle='round', facecolor='white', alpha=0.9),
        family='monospace'
    )

    # === Row 1, Col 2: Lung Mask ===
    ax2 = fig.add_subplot(gs[0, 1])
    ax2.imshow(ct_slice, cmap='gray', vmin=-1000, vmax=500)

    from matplotlib.colors import ListedColormap
    lung_colors = ['none', 'red', 'darkred']
    lung_cmap = ListedColormap(lung_colors)

    ax2.imshow(lung_slice, cmap=lung_cmap, alpha=0.5, vmin=0, vmax=2)
    ax2.set_title('Lung Segmentation', fontsize=16, fontweight='bold', color='darkred')
    ax2.axis('off')

    legend_text = '1: Right Lung\n2: Left Lung'
    ax2.text(
        0.02, 0.98,
        legend_text,
        transform=ax2.transAxes,
        fontsize=11,
        verticalalignment='top',
        bbox=dict(boxstyle='round', facecolor='white', alpha=0.9, edgecolor='red'),
        family='monospace'
    )

    # === Row 1, Col 3: COVID-19 Pattern Overlay ===
    ax3 = fig.add_subplot(gs[0, 2])
    ax3.imshow(ct_slice, cmap='gray', vmin=-1000, vmax=500)

    # Highlight COVID-19 patterns
    lung_roi_slice = ct_slice.copy().astype(np.float32)
    lung_roi_slice[lung_slice == 0] = np.nan

    # COVID-19 characteristic patterns
    ggo_mask = ((lung_roi_slice > -700) & (lung_roi_slice <= -500)) & (lung_slice > 0)
    consolidation_mask = ((lung_roi_slice > -300) & (lung_roi_slice <= 100)) & (lung_slice > 0)
    severe_consolidation = (lung_roi_slice > 100) & (lung_slice > 0)

    # Overlay GGO (yellow - typical COVID)
    if ggo_mask.sum() > 0:
        ax3.contourf(ggo_mask, levels=[0.5, 1.5], colors=['yellow'], alpha=0.6)

    # Overlay consolidation (orange)
    if consolidation_mask.sum() > 0:
        ax3.contourf(consolidation_mask, levels=[0.5, 1.5], colors=['orange'], alpha=0.7)

    # Overlay severe consolidation (red)
    if severe_consolidation.sum() > 0:
        ax3.contourf(severe_consolidation, levels=[0.5, 1.5], colors=['red'], alpha=0.8)

    ax3.set_title('COVID-19 Pattern Detection', fontsize=16, fontweight='bold', color='red')
    ax3.axis('off')

    overlay_legend = (
        'YELLOW: Ground-Glass Opacity\n'
        '   (-700 to -500 HU)\n'
        '   Typical COVID-19\n\n'
        'ORANGE: Consolidation\n'
        '   (-300 to 100 HU)\n'
        '   Progressive disease\n\n'
        'RED: Severe Consolidation\n'
        '   (>100 HU)\n'
        '   Advanced COVID-19'
    )
    ax3.text(
        0.02, 0.98,
        overlay_legend,
        transform=ax3.transAxes,
        fontsize=10,
        verticalalignment='top',
        bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.95, edgecolor='red', linewidth=2),
        family='monospace'
    )

    # === Row 2, Col 1: HU Distribution ===
    ax4 = fig.add_subplot(gs[1, 0])

    lung_roi = ct_array[lung_mask_array > 0]

    ax4.hist(lung_roi, bins=100, range=(-1000, 500), alpha=0.7, color='steelblue', edgecolor='black')

    # COVID-19 relevant thresholds
    ax4.axvline(-700, color='yellow', linestyle='--', linewidth=2.5, label='GGO start (-700)')
    ax4.axvline(-500, color='orange', linestyle='--', linewidth=2.5, label='GGO end (-500)')
    ax4.axvline(-300, color='red', linestyle='--', linewidth=2.5, label='Consolidation (-300)')

    ax4.set_xlabel('HU Value', fontsize=13, fontweight='bold')
    ax4.set_ylabel('Frequency (voxels)', fontsize=13, fontweight='bold')
    ax4.set_title('HU Distribution - COVID-19 Zones', fontsize=15, fontweight='bold')
    ax4.legend(loc='upper right', fontsize=10)
    ax4.grid(alpha=0.3)

    # Add mean line
    ax4.axvline(features['hu_mean'], color='green', linestyle='-', linewidth=3, alpha=0.7)
    ax4.text(features['hu_mean'], ax4.get_ylim()[1]*0.9, f"Mean\n{features['hu_mean']:.0f}",
             ha='center', fontsize=10, fontweight='bold', color='green')

    # === Row 2, Col 2: Tissue Composition ===
    ax5 = fig.add_subplot(gs[1, 1])

    tissues = {
        'Normal Lung': features['normal_lung_percentage'],
        'Ground-Glass\n(COVID)': features['ggo_percentage'],
        'Consolidation\n(COVID)': features['consolidation_percentage'],
        'Soft Tissue': features['soft_tissue_percentage']
    }

    tissues = {k: v for k, v in tissues.items() if v > 0.5}

    colors_pie = ['lightgreen', 'gold', 'orangered', 'lightcoral']
    explode = [0.05 if 'COVID' in k else 0 for k in tissues.keys()]

    wedges, texts, autotexts = ax5.pie(
        tissues.values(),
        labels=tissues.keys(),
        autopct='%1.1f%%',
        startangle=90,
        colors=colors_pie[:len(tissues)],
        explode=explode,
        textprops={'fontsize': 11, 'fontweight': 'bold'}
    )

    # Highlight COVID-related segments
    for i, text in enumerate(texts):
        if 'COVID' in text.get_text():
            text.set_color('red')
            text.set_fontweight('bold')

    ax5.set_title('Lung Tissue Composition\n(COVID-19 Analysis)', fontsize=15, fontweight='bold')

    # === Row 2, Col 3: COVID-19 Diagnostic Report ===
    ax6 = fig.add_subplot(gs[1, 2])
    ax6.axis('off')

    report_lines = []
    report_lines.append("╔" + "═"*42 + "╗")
    report_lines.append("║   COVID-19 AI DIAGNOSTIC REPORT          ║")
    report_lines.append("╚" + "═"*42 + "╝")
    report_lines.append("")

    # Status
    likelihood_symbol = {
        'HIGH': '[!!!] HIGH RISK',
        'MODERATE': '[!!] MODERATE RISK',
        'LOW-MODERATE': '[!] LOW-MODERATE',
        'LOW': '[OK] LOW RISK'
    }

    report_lines.append(f"COVID-19 LIKELIHOOD:")
    report_lines.append(f"  {likelihood_symbol[diagnosis['covid_likelihood']]}")
    report_lines.append(f"  Probability: {diagnosis['covid_probability']:.0f}%")
    report_lines.append(f"  Severity: {diagnosis['severity']}")
    report_lines.append(f"  Score: {diagnosis['covid_score']}/10")
    report_lines.append("")

    # CT Pattern
    report_lines.append(f"CT PATTERN:")
    report_lines.append(f"  {diagnosis['ct_pattern']}")
    report_lines.append("")

    # Findings
    report_lines.append(f"CLINICAL INDICATORS ({diagnosis['num_indicators']}):")
    for i, indicator in enumerate(diagnosis['indicators'][:5], 1):
        # Wrap long text
        if len(indicator) > 38:
            indicator = indicator[:35] + "..."
        report_lines.append(f"  {i}. {indicator}")

    report_lines.append("")
    report_lines.append("─" * 42)
    report_lines.append("KEY MEASUREMENTS:")
    report_lines.append(f"  Lung Volume: {features['lung_volume_ml']:.0f} ml")
    report_lines.append(f"  Mean HU: {features['hu_mean']:.1f}")
    report_lines.append(f"  Ground-Glass: {features['ggo_percentage']:.1f}% [!]")
    report_lines.append(f"  Consolidation: {features['consolidation_percentage']:.1f}% [!]")
    report_lines.append(f"  Normal Tissue: {features['normal_lung_percentage']:.1f}%")

    report_lines.append("")
    report_lines.append("─" * 42)
    report_lines.append("RECOMMENDATIONS:")
    for i, rec in enumerate(diagnosis['recommendations'][:4], 1):
        if len(rec) > 36:
            rec = rec[:33] + "..."
        report_lines.append(f"  {i}. {rec}")

    report_text = "\n".join(report_lines)

    # Color based on risk
    risk_colors = {
        'HIGH': ('darkred', 'mistyrose'),
        'MODERATE': ('darkorange', 'lightyellow'),
        'LOW-MODERATE': ('orange', 'lightyellow'),
        'LOW': ('darkgreen', 'lightgreen')
    }
    text_color, bg_color = risk_colors[diagnosis['covid_likelihood']]

    ax6.text(
        0.05, 0.95,
        report_text,
        transform=ax6.transAxes,
        fontsize=9.5,
        verticalalignment='top',
        family='monospace',
        bbox=dict(boxstyle='round,pad=1', facecolor=bg_color, alpha=0.95,
                  edgecolor=text_color, linewidth=3),
        color=text_color
    )

    # === Overall Title ===
    title_color = {'HIGH': 'red', 'MODERATE': 'orange', 'LOW-MODERATE': 'orange', 'LOW': 'green'}
    title_text = (
        f'COVID-19 AI-Assisted Detection: {patient_id}\n'
        f'Likelihood: {diagnosis["covid_likelihood"]} ({diagnosis["covid_probability"]:.0f}%) | '
        f'Severity: {diagnosis["severity"]} | Pattern: {diagnosis["ct_pattern"]} | '
        f'Inference: {inference_time:.1f}s'
    )

    fig.suptitle(
        title_text,
        fontsize=15,
        fontweight='bold',
        color=title_color[diagnosis['covid_likelihood']]
    )

    # Save
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    print(f"\n[OK] Visualization saved: {output_path}")
    plt.close()


def main():
    """
    Main COVID-19 detection demo
    """
    print("\n" + "="*70)
    print("COVID-19 Detection Demo - AI-Assisted CT Analysis")
    print("="*70)

    # Find data
    data_dir = Path("./sample-data/Task06_Lung/imagesTr")
    image_files = sorted([f for f in data_dir.glob("*.nii.gz") if not f.name.startswith("._")])

    if len(image_files) == 0:
        print("\n[ERROR] No CT scans found!")
        return

    # Use first patient (or you can select specific one)
    image_path = image_files[0]
    patient_id = f"COVID19_{image_path.stem}"

    print(f"\n[INFO] Patient ID: {patient_id}")
    print(f"[INFO] Loading CT scan...")

    # Load CT
    ct_scan = sitk.ReadImage(str(image_path))
    ct_array = sitk.GetArrayFromImage(ct_scan)
    spacing = ct_scan.GetSpacing()

    print(f"[INFO] CT shape: {ct_array.shape}")
    print(f"[INFO] Spacing: {spacing}")

    # === Step 1: Lung Segmentation ===
    print("\n" + "-"*70)
    print("[1/4] Running Lung Segmentation (LungMask R231)...")
    print("-"*70)

    start_time = time.time()
    inferer = LMInferer(modelname='R231')
    lung_mask_array = inferer.apply(ct_scan)
    segmentation_time = time.time() - start_time

    print(f"[OK] Segmentation completed in {segmentation_time:.1f}s")

    # === Step 2: Feature Extraction ===
    print("\n" + "-"*70)
    print("[2/4] Extracting COVID-19 Relevant Features...")
    print("-"*70)

    extractor = LungFeatureExtractor()
    features = extractor.extract(ct_array, lung_mask_array, spacing)

    print(f"[OK] Extracted {len(features)} features")
    print(f"\nCOVID-19 Relevant Metrics:")
    print(f"  Lung volume: {features['lung_volume_ml']:.0f} ml")
    print(f"  Mean HU: {features['hu_mean']:.1f}")
    print(f"  Ground-glass (GGO): {features['ggo_percentage']:.1f}% {'[!] HIGH' if features['ggo_percentage'] > 15 else '[OK] Normal'}")
    print(f"  Consolidation: {features['consolidation_percentage']:.1f}% {'[!] HIGH' if features['consolidation_percentage'] > 10 else '[OK] Normal'}")
    print(f"  Normal tissue: {features['normal_lung_percentage']:.1f}%")

    # === Step 3: COVID-19 Classification ===
    print("\n" + "-"*70)
    print("[3/4] Running COVID-19 Detection Analysis...")
    print("-"*70)

    classifier = COVID19Classifier()
    diagnosis = classifier.classify(features)

    print(f"[OK] Analysis completed")
    print(f"\nCOVID-19 Assessment:")
    print(f"  Likelihood: {diagnosis['covid_likelihood']}")
    print(f"  Probability: {diagnosis['covid_probability']:.0f}%")
    print(f"  Severity: {diagnosis['severity']}")
    print(f"  Risk Score: {diagnosis['covid_score']}/10")
    print(f"  CT Pattern: {diagnosis['ct_pattern']}")

    if diagnosis['covid_score'] >= 5:
        print(f"\n[WARNING] HIGH COVID-19 SUSPICION - Immediate action required!")
    elif diagnosis['covid_score'] >= 3:
        print(f"\n[CAUTION] Moderate COVID-19 suspicion - Further testing recommended")
    else:
        print(f"\n[INFO] Low COVID-19 suspicion")

    print(f"\nClinical Indicators ({diagnosis['num_indicators']}):")
    for i, indicator in enumerate(diagnosis['indicators'], 1):
        print(f"  {i}. {indicator}")

    # === Step 4: Create Visualization ===
    print("\n" + "-"*70)
    print("[4/4] Creating COVID-19 Visualization...")
    print("-"*70)

    output_path = Path(f"covid19_detection_{image_path.stem}.png")

    create_covid19_visualization(
        ct_array=ct_array,
        lung_mask_array=lung_mask_array,
        features=features,
        diagnosis=diagnosis,
        patient_id=patient_id,
        inference_time=segmentation_time,
        spacing=spacing,
        output_path=output_path
    )

    # === Summary ===
    print("\n" + "="*70)
    print("COVID-19 ANALYSIS COMPLETE")
    print("="*70)

    print(f"\n[OUTPUT FILE]: {output_path}")
    print(f"   <- OPEN THIS FILE TO SEE COVID-19 VISUALIZATION")

    print(f"\n[SUMMARY]")
    print(f"  Patient: {patient_id}")
    print(f"  COVID-19 Likelihood: {diagnosis['covid_likelihood']} ({diagnosis['covid_probability']:.0f}%)")
    print(f"  Severity: {diagnosis['severity']}")
    print(f"  CT Pattern: {diagnosis['ct_pattern']}")
    print(f"  Processing Time: {segmentation_time:.1f}s")

    print(f"\n[RECOMMENDATIONS]:")
    for i, rec in enumerate(diagnosis['recommendations'], 1):
        print(f"  {i}. {rec}")

    # Save text report
    report_path = Path(f"covid19_report_{image_path.stem}.txt")
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write("="*70 + "\n")
        f.write("COVID-19 AI-ASSISTED DIAGNOSTIC REPORT\n")
        f.write("="*70 + "\n\n")
        f.write(f"Patient ID: {patient_id}\n")
        f.write(f"Analysis Date: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write(f"COVID-19 ASSESSMENT:\n")
        f.write(f"  Likelihood: {diagnosis['covid_likelihood']}\n")
        f.write(f"  Probability: {diagnosis['covid_probability']:.0f}%\n")
        f.write(f"  Severity: {diagnosis['severity']}\n")
        f.write(f"  Risk Score: {diagnosis['covid_score']}/10\n")
        f.write(f"  CT Pattern: {diagnosis['ct_pattern']}\n\n")
        f.write(f"CLINICAL INDICATORS:\n")
        for i, ind in enumerate(diagnosis['indicators'], 1):
            f.write(f"  {i}. {ind}\n")
        f.write(f"\nKEY MEASUREMENTS:\n")
        f.write(f"  Lung Volume: {features['lung_volume_ml']:.0f} ml\n")
        f.write(f"  Mean HU: {features['hu_mean']:.1f}\n")
        f.write(f"  Ground-Glass Opacity: {features['ggo_percentage']:.1f}%\n")
        f.write(f"  Consolidation: {features['consolidation_percentage']:.1f}%\n")
        f.write(f"  Normal Tissue: {features['normal_lung_percentage']:.1f}%\n")
        f.write(f"\nRECOMMENDATIONS:\n")
        for i, rec in enumerate(diagnosis['recommendations'], 1):
            f.write(f"  {i}. {rec}\n")
        f.write(f"\n{'='*70}\n")
        f.write("DISCLAIMER: This is AI-assisted analysis for research purposes.\n")
        f.write("Final diagnosis must be made by qualified radiologists and\n")
        f.write("confirmed with RT-PCR testing.\n")
        f.write("="*70 + "\n")

    print(f"[OK] Text report saved: {report_path}")

    print("\n" + "="*70)
    print("DISCLAIMER:")
    print("   This is AI-assisted analysis for research/educational purposes.")
    print("   COVID-19 diagnosis requires:")
    print("   1. RT-PCR confirmation")
    print("   2. Clinical correlation")
    print("   3. Radiologist interpretation")
    print("="*70 + "\n")


if __name__ == "__main__":
    main()
