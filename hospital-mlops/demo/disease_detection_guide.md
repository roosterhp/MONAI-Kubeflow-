# Hướng Dẫn Tích Hợp Chức Năng Chẩn Đoán Bệnh Phổi

## 📋 Tổng Quan

Document này hướng dẫn mở rộng pipeline từ **chỉ segmentation phổi** sang **multi-task pipeline** bao gồm:
1. **Lung Segmentation** (LungMask) - Phân đoạn phổi
2. **Disease Detection** - Phát hiện bệnh lý
3. **Lesion Segmentation** - Phân đoạn tổn thương (nodules, lesions)
4. **Disease Classification** - Phân loại bệnh

---

## 🎯 Các Loại Bệnh Có Thể Detect

### 1. **COVID-19 Pneumonia**
- Ground-glass opacity (GGO)
- Consolidation
- Crazy paving pattern
- **Model:** MONAI COVID-19 CT Segmentation

### 2. **Lung Nodules/Cancer**
- Pulmonary nodules
- Masses
- **Model:** MONAI TotalSegmentator, Lung Nodule Detection

### 3. **Interstitial Lung Disease (ILD)**
- Fibrosis patterns
- Reticulation
- Honeycombing

### 4. **Emphysema**
- Low attenuation areas
- Bullae

### 5. **Pneumonia (Bacterial/Viral)**
- Consolidation patterns
- Infiltrates

---

## 🏗️ Kiến Trúc Multi-Task Pipeline

```
┌─────────────────────────────────────────────────────────────────┐
│              Multi-Task Disease Detection Pipeline               │
└─────────────────────────────────────────────────────────────────┘

Input CT Scan
     │
     ▼
┌──────────────────────┐
│  Preprocessing       │
│  - Load             │
│  - Normalize        │
│  - Resample         │
└──────────────────────┘
     │
     ├─────────────────────────────────────────────────────┐
     │                                                      │
     ▼                                                      ▼
┌─────────────────────┐                        ┌──────────────────────┐
│  Task 1:            │                        │  Task 2:             │
│  Lung Segmentation  │                        │  Lesion Detection    │
│  (LungMask R231)    │                        │  (MONAI COVID-19)    │
│                     │                        │                      │
│  Output:            │                        │  Output:             │
│  - Right lung mask  │                        │  - Lesion mask       │
│  - Left lung mask   │                        │  - Lesion locations  │
└─────────────────────┘                        └──────────────────────┘
     │                                                      │
     └──────────────────────┬───────────────────────────────┘
                            │
                            ▼
                   ┌─────────────────────┐
                   │  Task 3:            │
                   │  Feature Extraction │
                   │                     │
                   │  - Lung volume      │
                   │  - Lesion volume    │
                   │  - Lesion count     │
                   │  - HU statistics    │
                   │  - Texture features │
                   └─────────────────────┘
                            │
                            ▼
                   ┌─────────────────────┐
                   │  Task 4:            │
                   │  Disease Classifier │
                   │  (Rule-based or ML) │
                   │                     │
                   │  Rules:             │
                   │  - GGO present      │
                   │  - Lesion volume    │
                   │  - Distribution     │
                   └─────────────────────┘
                            │
                            ▼
                   ┌─────────────────────┐
                   │  Final Report       │
                   │                     │
                   │  1. Normal/Abnormal │
                   │  2. Disease type    │
                   │  3. Severity score  │
                   │  4. Recommendations │
                   └─────────────────────┘
```

---

## 🔬 Approaches Chi Tiết

### Approach 1: Lesion Segmentation (MONAI COVID-19)

**Mô tả:**
- Sử dụng MONAI COVID-19 CT Segmentation model
- Pretrained trên 1000+ COVID CT scans
- Output: Lung mask + Lesion mask

**Implementation:**

```python
from monai.bundle import download, load

# Download pretrained model
download(name="covid19_lung_ct_segmentation", bundle_dir="./models")

# Load model
covid_model = load(
    name="covid19_lung_ct_segmentation",
    model_dir="./models"
)

# Inference
outputs = covid_model(ct_scan)
# outputs[0]: lung mask
# outputs[1]: lesion mask
```

**Ưu điểm:**
- ✅ Pretrained, ready to use
- ✅ Detect COVID-19 lesions (GGO, consolidation)
- ✅ Dice ~0.88 (lung), ~0.75 (lesion)

**Nhược điểm:**
- ❌ Chỉ detect COVID-19 patterns
- ❌ Không detect nodules, masses
- ❌ Cần GPU (model lớn)

---

### Approach 2: Rule-Based Disease Classification

**Mô tả:**
- Dùng lung segmentation + feature extraction
- Apply clinical rules để classify
- Không cần training model mới

**Features:**

1. **Lung Volume**
   - Normal: 4000-6000 ml
   - Low: < 4000 ml (restriction)
   - High: > 6000 ml (hyperinflation/emphysema)

2. **HU Distribution in Lungs**
   - Normal lung: -950 to -700 HU
   - Emphysema: < -950 HU (air trapping)
   - Consolidation: > -300 HU (fluid/pus)
   - Ground-glass: -700 to -500 HU

3. **Texture Features**
   - Variance, entropy, contrast
   - High variance → heterogeneous (ILD)
   - Low variance → homogeneous

**Classification Rules:**

```python
def classify_disease(features):
    """
    Rule-based classifier
    """
    diagnosis = []

    # Rule 1: Emphysema
    if features['hu_mean'] < -900:
        diagnosis.append("Emphysema (suspected)")

    # Rule 2: Consolidation/Pneumonia
    consolidation_ratio = features['hu_above_minus300'] / features['lung_volume']
    if consolidation_ratio > 0.05:  # > 5% consolidation
        diagnosis.append("Consolidation/Pneumonia (suspected)")

    # Rule 3: Ground-glass opacity
    ggo_ratio = features['hu_between_minus700_minus500'] / features['lung_volume']
    if ggo_ratio > 0.10:  # > 10% GGO
        diagnosis.append("Ground-glass opacity (suspected)")

    # Rule 4: Lung volume
    if features['lung_volume_ml'] < 3000:
        diagnosis.append("Restrictive pattern")
    elif features['lung_volume_ml'] > 7000:
        diagnosis.append("Hyperinflation")

    if len(diagnosis) == 0:
        return "Normal (no abnormalities detected)"
    else:
        return diagnosis
```

**Ưu điểm:**
- ✅ Không cần training
- ✅ Interpretable (giải thích được)
- ✅ Fast (chỉ cần LungMask)
- ✅ Không cần GPU

**Nhược điểm:**
- ❌ Accuracy thấp hơn ML models
- ❌ Hard-coded thresholds
- ❌ Không detect specific lesions (nodules)

---

### Approach 3: Ensemble Multi-Model

**Mô tả:**
- Kết hợp nhiều models
- Voting hoặc weighted average

**Pipeline:**

```python
# Model 1: LungMask (lung segmentation)
lung_mask = lungmask_model(ct_scan)

# Model 2: MONAI COVID-19 (lesion detection)
covid_pred = covid_model(ct_scan)

# Model 3: Classification model (normal vs abnormal)
classifier_pred = classifier_model(ct_scan)

# Ensemble
final_diagnosis = {
    'lung_mask': lung_mask,
    'lesions': covid_pred,
    'classification': classifier_pred,
    'confidence': compute_confidence([lung_mask, covid_pred, classifier_pred])
}
```

**Ưu điểm:**
- ✅ Highest accuracy
- ✅ Multiple disease types
- ✅ Robust

**Nhược điểm:**
- ❌ Phức tạp
- ❌ Slow inference
- ❌ Cần nhiều models

---

## 💻 Implementation: Multi-Task Pipeline

### Step 1: Tích Hợp MONAI COVID-19 Model

**Download model:**

```bash
cd hospital-mlops/pretrained-models
python -c "from monai.bundle import download; download(name='covid19_lung_ct_segmentation', bundle_dir='.')"
```

**Create transform:**

```python
# hospital-mlops/demo/covid_transform.py

from monai.transforms import MapTransform
from monai.bundle import load
import torch

class COVIDLesionTransformd(MapTransform):
    """
    Transform để detect COVID-19 lesions
    """

    def __init__(self, keys, model_dir="./pretrained-models"):
        super().__init__(keys)

        # Lazy load model
        self._model = None
        self.model_dir = model_dir

    @property
    def model(self):
        if self._model is None:
            print("[INFO] Loading COVID-19 lesion detection model...")
            self._model = load(
                name="covid19_lung_ct_segmentation",
                model_dir=self.model_dir
            )
            self._model.eval()
        return self._model

    def __call__(self, data):
        d = dict(data)

        for key in self.key_iterator(d):
            image = d[key]

            # Run inference
            with torch.no_grad():
                outputs = self.model(image[None])  # Add batch dim

            # outputs: [lung_mask, lesion_mask]
            d["lung_mask"] = outputs[0][0]  # Remove batch dim
            d["lesion_mask"] = outputs[1][0]

        return d
```

### Step 2: Feature Extraction

```python
# hospital-mlops/demo/feature_extractor.py

import numpy as np
import SimpleITK as sitk
from scipy import ndimage

class LungFeatureExtractor:
    """
    Extract clinical features từ CT scan và lung mask
    """

    def __init__(self):
        pass

    def extract(self, ct_array, lung_mask_array):
        """
        Extract features

        Args:
            ct_array: CT scan (HU values)
            lung_mask_array: Lung segmentation mask

        Returns:
            dict: Clinical features
        """
        features = {}

        # Lung ROI
        lung_roi = ct_array[lung_mask_array > 0]

        # Feature 1: Lung volume
        spacing = (1.0, 1.0, 1.0)  # Will be passed from metadata
        voxel_volume = np.prod(spacing)
        lung_voxels = (lung_mask_array > 0).sum()
        features['lung_volume_ml'] = (lung_voxels * voxel_volume) / 1000

        # Feature 2: HU statistics
        features['hu_mean'] = lung_roi.mean()
        features['hu_std'] = lung_roi.std()
        features['hu_min'] = lung_roi.min()
        features['hu_max'] = lung_roi.max()
        features['hu_median'] = np.median(lung_roi)

        # Feature 3: HU distribution (percentage in ranges)
        total_voxels = lung_roi.size

        # Emphysema: < -950 HU
        features['emphysema_ratio'] = (lung_roi < -950).sum() / total_voxels

        # Normal: -950 to -700 HU
        features['normal_ratio'] = ((lung_roi >= -950) & (lung_roi <= -700)).sum() / total_voxels

        # Ground-glass: -700 to -500 HU
        features['ggo_ratio'] = ((lung_roi > -700) & (lung_roi <= -500)).sum() / total_voxels

        # Consolidation: > -300 HU
        features['consolidation_ratio'] = (lung_roi > -300).sum() / total_voxels

        # Feature 4: Texture features
        features['hu_variance'] = np.var(lung_roi)
        features['hu_entropy'] = self._calculate_entropy(lung_roi)

        # Feature 5: Spatial distribution
        # Center of mass
        com = ndimage.center_of_mass(lung_mask_array)
        features['center_of_mass'] = com

        return features

    def _calculate_entropy(self, values, bins=100):
        """Calculate entropy of HU distribution"""
        hist, _ = np.histogram(values, bins=bins)
        hist = hist / hist.sum()  # Normalize
        hist = hist[hist > 0]  # Remove zeros
        entropy = -np.sum(hist * np.log2(hist))
        return entropy
```

### Step 3: Disease Classifier

```python
# hospital-mlops/demo/disease_classifier.py

class DiseaseClassifier:
    """
    Rule-based disease classifier
    """

    def __init__(self):
        self.rules = self._define_rules()

    def _define_rules(self):
        """
        Clinical decision rules
        """
        return {
            'emphysema': {
                'condition': lambda f: f['emphysema_ratio'] > 0.20,  # > 20% low attenuation
                'severity': lambda f: 'Severe' if f['emphysema_ratio'] > 0.40 else 'Moderate'
            },
            'ground_glass_opacity': {
                'condition': lambda f: f['ggo_ratio'] > 0.10,  # > 10% GGO
                'severity': lambda f: 'Severe' if f['ggo_ratio'] > 0.30 else 'Mild'
            },
            'consolidation': {
                'condition': lambda f: f['consolidation_ratio'] > 0.05,  # > 5% consolidation
                'severity': lambda f: 'Severe' if f['consolidation_ratio'] > 0.20 else 'Moderate'
            },
            'hyperinflation': {
                'condition': lambda f: f['lung_volume_ml'] > 7000,
                'severity': lambda f: 'Severe' if f['lung_volume_ml'] > 8000 else 'Moderate'
            },
            'restriction': {
                'condition': lambda f: f['lung_volume_ml'] < 3000,
                'severity': lambda f: 'Severe' if f['lung_volume_ml'] < 2000 else 'Moderate'
            }
        }

    def classify(self, features):
        """
        Classify disease based on features

        Args:
            features: dict from LungFeatureExtractor

        Returns:
            dict: {
                'is_normal': bool,
                'findings': list of detected abnormalities,
                'severity': overall severity score,
                'recommendations': clinical recommendations
            }
        """
        findings = []

        # Check each rule
        for disease, rule in self.rules.items():
            if rule['condition'](features):
                severity = rule['severity'](features)
                findings.append({
                    'disease': disease.replace('_', ' ').title(),
                    'severity': severity,
                    'confidence': 'High'  # Can compute based on feature values
                })

        # Overall assessment
        is_normal = len(findings) == 0

        # Compute severity score (0-10)
        severity_score = self._compute_severity_score(findings)

        # Generate recommendations
        recommendations = self._generate_recommendations(findings, features)

        return {
            'is_normal': is_normal,
            'findings': findings,
            'severity_score': severity_score,
            'recommendations': recommendations,
            'features_summary': self._summarize_features(features)
        }

    def _compute_severity_score(self, findings):
        """
        Compute overall severity (0-10 scale)
        """
        if len(findings) == 0:
            return 0

        severity_map = {'Mild': 3, 'Moderate': 6, 'Severe': 9}
        scores = [severity_map.get(f['severity'], 5) for f in findings]

        return min(10, sum(scores) / len(scores))

    def _generate_recommendations(self, findings, features):
        """
        Generate clinical recommendations
        """
        recommendations = []

        if len(findings) == 0:
            return ["No significant abnormalities detected", "Routine follow-up as needed"]

        # Specific recommendations based on findings
        diseases = [f['disease'] for f in findings]

        if 'Ground Glass Opacity' in diseases:
            recommendations.append("Consider viral pneumonia or early interstitial lung disease")
            recommendations.append("Clinical correlation with symptoms and lab results recommended")

        if 'Consolidation' in diseases:
            recommendations.append("Suggests bacterial pneumonia or atelectasis")
            recommendations.append("Consider antibiotic therapy and follow-up imaging")

        if 'Emphysema' in diseases:
            recommendations.append("Consistent with COPD")
            recommendations.append("Pulmonary function tests recommended")

        if 'Hyperinflation' in diseases:
            recommendations.append("Air trapping detected")
            recommendations.append("Assess for obstructive lung disease")

        # General recommendations
        recommendations.append("Recommend clinical correlation and follow-up imaging in 3-6 months")

        return recommendations

    def _summarize_features(self, features):
        """
        Create human-readable summary
        """
        return {
            'Lung Volume': f"{features['lung_volume_ml']:.0f} ml",
            'Mean HU': f"{features['hu_mean']:.1f}",
            'Emphysema': f"{features['emphysema_ratio']*100:.1f}%",
            'Ground-Glass': f"{features['ggo_ratio']*100:.1f}%",
            'Consolidation': f"{features['consolidation_ratio']*100:.1f}%"
        }
```

---

## 🎨 Visualization

### Enhanced Visualization với Disease Detection

```python
def visualize_disease_detection(
    ct_path,
    lung_mask,
    lesion_mask,
    features,
    diagnosis,
    output_path
):
    """
    Create comprehensive visualization

    Layout:
    Row 1: CT | Lung Mask | Lesion Mask
    Row 2: Overlay | HU Distribution | Findings Report
    """

    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle

    fig, axes = plt.subplots(2, 3, figsize=(18, 12))

    # Get middle slice
    slice_idx = ct_array.shape[0] // 2
    ct_slice = ct_array[slice_idx]
    lung_slice = lung_mask[slice_idx]
    lesion_slice = lesion_mask[slice_idx] if lesion_mask is not None else None

    # Row 1, Col 1: CT
    axes[0, 0].imshow(ct_slice, cmap='gray', vmin=-1000, vmax=500)
    axes[0, 0].set_title('CT Scan', fontsize=14, fontweight='bold')
    axes[0, 0].axis('off')

    # Row 1, Col 2: Lung Mask
    axes[0, 1].imshow(ct_slice, cmap='gray', vmin=-1000, vmax=500)
    axes[0, 1].imshow(lung_slice, cmap='Reds', alpha=0.5)
    axes[0, 1].set_title('Lung Segmentation', fontsize=14, fontweight='bold')
    axes[0, 1].axis('off')

    # Row 1, Col 3: Lesion Mask
    if lesion_slice is not None:
        axes[0, 2].imshow(ct_slice, cmap='gray', vmin=-1000, vmax=500)
        axes[0, 2].imshow(lesion_slice, cmap='Oranges', alpha=0.6)
        axes[0, 2].set_title('Lesion Detection', fontsize=14, fontweight='bold')
    else:
        axes[0, 2].text(0.5, 0.5, 'No Lesions\nDetected',
                        ha='center', va='center', fontsize=16)
    axes[0, 2].axis('off')

    # Row 2, Col 1: Full Overlay
    axes[1, 0].imshow(ct_slice, cmap='gray', vmin=-1000, vmax=500)
    axes[1, 0].imshow(lung_slice, cmap='Reds', alpha=0.3)
    if lesion_slice is not None:
        axes[1, 0].imshow(lesion_slice, cmap='Oranges', alpha=0.5)
    axes[1, 0].set_title('Complete Overlay', fontsize=14, fontweight='bold')
    axes[1, 0].axis('off')

    # Row 2, Col 2: HU Distribution
    lung_roi = ct_array[lung_mask > 0]
    axes[1, 1].hist(lung_roi, bins=100, range=(-1000, 500), alpha=0.7, color='steelblue')
    axes[1, 1].axvline(-950, color='red', linestyle='--', label='Emphysema threshold')
    axes[1, 1].axvline(-700, color='orange', linestyle='--', label='GGO threshold')
    axes[1, 1].axvline(-300, color='green', linestyle='--', label='Consolidation threshold')
    axes[1, 1].set_xlabel('HU Value', fontsize=12)
    axes[1, 1].set_ylabel('Frequency', fontsize=12)
    axes[1, 1].set_title('HU Distribution in Lungs', fontsize=14, fontweight='bold')
    axes[1, 1].legend()
    axes[1, 1].grid(alpha=0.3)

    # Row 2, Col 3: Findings Report
    axes[1, 2].axis('off')

    # Create report text
    report_text = "=== DIAGNOSTIC REPORT ===\n\n"

    if diagnosis['is_normal']:
        report_text += "Status: NORMAL\n"
        report_text += "No significant abnormalities detected\n\n"
    else:
        report_text += "Status: ABNORMAL\n\n"
        report_text += f"Severity Score: {diagnosis['severity_score']:.1f}/10\n\n"
        report_text += "Findings:\n"
        for i, finding in enumerate(diagnosis['findings'], 1):
            report_text += f"{i}. {finding['disease']}\n"
            report_text += f"   Severity: {finding['severity']}\n\n"

    report_text += "Features:\n"
    for key, value in diagnosis['features_summary'].items():
        report_text += f"  {key}: {value}\n"

    report_text += "\nRecommendations:\n"
    for i, rec in enumerate(diagnosis['recommendations'], 1):
        report_text += f"{i}. {rec}\n"

    axes[1, 2].text(
        0.05, 0.95,
        report_text,
        transform=axes[1, 2].transAxes,
        fontsize=10,
        verticalalignment='top',
        family='monospace',
        bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8)
    )

    # Overall title
    status_color = 'green' if diagnosis['is_normal'] else 'red'
    status_text = 'NORMAL' if diagnosis['is_normal'] else 'ABNORMAL'

    fig.suptitle(
        f'AI-Assisted Lung CT Analysis\n'
        f'Status: {status_text} | Severity: {diagnosis["severity_score"]:.1f}/10',
        fontsize=16,
        fontweight='bold',
        color=status_color
    )

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()
```

---

## 📊 Output Report Format

```json
{
  "patient_id": "lung_001",
  "scan_date": "2025-01-21",
  "analysis_timestamp": "2025-01-21T19:30:00",

  "segmentation": {
    "lung_volume_ml": 4521.3,
    "right_lung_ml": 2341.2,
    "left_lung_ml": 2180.1
  },

  "features": {
    "hu_mean": -852.3,
    "hu_std": 142.5,
    "emphysema_ratio": 0.08,
    "ggo_ratio": 0.15,
    "consolidation_ratio": 0.03
  },

  "diagnosis": {
    "is_normal": false,
    "severity_score": 4.5,
    "findings": [
      {
        "disease": "Ground Glass Opacity",
        "severity": "Mild",
        "confidence": "High",
        "description": "Bilateral GGO pattern detected, 15% of lung volume affected"
      }
    ],
    "recommendations": [
      "Consider viral pneumonia or early ILD",
      "Clinical correlation recommended",
      "Follow-up CT in 3 months"
    ]
  },

  "model_info": {
    "lung_segmentation_model": "LungMask R231",
    "lesion_detection_model": "MONAI COVID-19 CT Segmentation",
    "classifier": "Rule-based clinical algorithm v1.0"
  }
}
```

---

## 🚀 Next Steps

1. **Download MONAI COVID-19 model** (nếu cần lesion detection):
   ```bash
   python -c "from monai.bundle import download; download(name='covid19_lung_ct_segmentation', bundle_dir='./pretrained-models')"
   ```

2. **Run disease detection demo**:
   ```bash
   python demo/disease_detection_demo.py
   ```

3. **Customize thresholds** trong `disease_classifier.py` dựa trên clinical guidelines của bệnh viện

4. **Validate với radiologists** để tune sensitivity/specificity

---

**Lưu ý quan trọng:**
- ⚠️ Đây là **Computer-Aided Detection (CAD)**, không thay thế radiologist
- ⚠️ Cần validation với ground truth trước khi clinical use
- ⚠️ False positives/negatives có thể xảy ra
- ⚠️ Chỉ dùng trong môi trường DEV/research, chưa phải production medical device

---

**Tác giả:** AI Assistant
**Ngày:** 2025-01-21
**Version:** 1.0
