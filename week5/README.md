# Week5 COVID-19 Detection Pipeline

Clean implementation of COVID-19 detection using Kubeflow pipelines with lung segmentation and clinical visualization.

## Overview

This pipeline provides a streamlined COVID-19 detection workflow:

1. **Lung Segmentation** - Uses LungMask R231 to segment right and left lungs
2. **COVID-19 Detection** - Ensemble of rule-based HU analysis + MONAI deep learning
3. **Clinical Visualization** - 2x3 grid layout for medical review

## Architecture

```
CT Input → Lung Segmentation → COVID Detection → Visualization
```

### Components

- **`lung_segment.py`** - Lung segmentation using LungMask R231
- **`covid_detect.py`** - COVID detection with ensemble approach
- **`visualize.py`** - Clinical visualization with 2x3 grid layout
- **`pipeline.py`** - Kubeflow pipeline definition
- **`run_pipeline_simple.py`** - Local testing runner

## Features

### Lung Segmentation
- **LungMask R231** model for accurate lung separation
- Right lung (green) and left lung (cyan) visualization
- Handles various CT formats with fallback mechanisms

### COVID-19 Detection
- **Ensemble Approach**: Rule-based (60%) + MONAI (40%)
- **Rule-based**: HU threshold analysis
  - GGO: HU -700 to -500
  - Consolidation: HU > -300
  - Bilateral involvement scoring
- **MONAI**: DenseNet121 with CT+lung mask input
- **Risk Levels**: VERY_LOW, LOW, MODERATE, HIGH

### Clinical Visualization
- **2x3 Grid Layout**:
  - Row 1: CT Scan | Lung Mask | COVID Overlay
  - Row 2: Metrics | Features | Clinical Decision
- **Color-coded** risk assessment
- **Professional medical** formatting

## Quick Start

### Local Testing

1. **Prepare Environment**:
```bash
# Install dependencies
pip install -r config/requirements.txt
pip install git+https://github.com/JoHof/lungmask.git
```

2. **Set up Data**:
```bash
# Create input directory structure
mkdir -p data/input/lung_001 data/input/lung_002 data/input/lung_003 data/input/lung_004

# Place CT scans (imaging.nii.gz) in each patient directory
# Expected structure:
# data/input/lung_001/imaging.nii.gz
# data/input/lung_002/imaging.nii.gz
# data/input/lung_003/imaging.nii.gz
# data/input/lung_004/imaging.nii.gz
```

3. **Run Pipeline**:
```bash
python run_pipeline_simple.py
```

### Hospital Workflow (Recommended for Production)

#### **1. Prepare Hospital Data**
```bash
# Structure: CT scans directly in weekly_input folder
mkdir -p week5/data/weekly_input

# Copy real CT scans (from covid-demo data)
cp hospital-mlops/covid-demo/data/input/lung_001.nii.gz week5/data/weekly_input/
cp hospital-mlops/covid-demo/data/input/lung_002.nii.gz week5/data/weekly_input/
cp hospital-mlops/covid-demo/data/input/lung_003.nii.gz week5/data/weekly_input/
cp hospital-mlops/covid-demo/data/input/lung_004.nii.gz week5/data/weekly_input/
```

#### **2. Run Local Hospital Workflow**
```bash
cd week5

# Auto-detect and process all patients
python hospital_pipeline_runner.py

# Results saved in data/hospital_output/
├── lung_001.nii/
│   ├── covid_visualization.png
│   └── covid_results.json
└── lung_002.nii/
    └── ...
```

#### **3. Build Container for Kubeflow**
```bash
cd week5
docker build -t covid-hospital-pipeline:latest -f config/Dockerfile .
```

#### **4. Deploy to Kubeflow UI**

**Option A: Using kfp Python SDK**
```python
import kfp

# Upload hospital pipeline
client = kfp.Client()
pipeline = client.upload_pipeline(
    pipeline_file='hospital_covid_detection_week5.yaml',
    pipeline_name='Hospital COVID Detection Week5'
)

# Run pipeline
experiment = client.create_experiment(name='hospital-covid-experiment')
run = client.run_pipeline(
    experiment_id=experiment.id,
    pipeline_id=pipeline.id,
    params={
        'input-weekly-dir': '/mnt/data/hospital_input/weekly_scan',
        'output-base-dir': '/mnt/data/hospital_output'
    }
)
```

**Option B: Using kubectl**
```bash
# Apply to Kubernetes
kubectl apply -f hospital_covid_detection_week5.yaml

# Check status
kubectl get workflows
kubectl get pods
```

**Option C: Using Kubeflow UI**
1. Open Kubeflow UI in browser
2. Click "Upload Pipeline"
3. Select `hospital_covid_detection_week5.yaml`
4. Configure parameters:
   - `input-weekly-dir`: `/mnt/data/hospital_input/weekly_scan`
   - `output-base-dir`: `/mnt/data/hospital_output`
5. Click "Start"

#### **5. Configure Persistent Volume**
```bash
# Create PVC for data storage
kubectl apply -f - <<EOF
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: hospital-data-pvc
  namespace: kubeflow
spec:
  accessModes:
  - ReadWriteOnce
  resources:
    requests:
      storage: 20Gi
EOF
```

### Local Testing (Development)

#### **1. Install Dependencies**
```bash
cd week5

# Install Python dependencies
pip install -r config/requirements.txt
pip install git+https://github.com/JoHof/lungmask.git
```

#### **2. Test Individual Components**
```bash
# Test data loading
python components/load_data_fixed.py data/weekly_input data/hospital_working metadata.json

# Test lung segmentation
python components/lung_segment.py data/hospital_working/lung_001.nii/imaging.nii.gz temp/segmentation

# Test COVID detection
python components/covid_detect.py temp/segmentation temp/detection

# Test visualization
python components/visualize.py temp/detection temp/visualization
```

#### **3. Run Simple Pipeline**
```bash
python run_pipeline_simple.py
```

## Output Structure

### Hospital Workflow Output
```
data/hospital_output/
├── lung_001.nii/                 # Patient folder (named from CT filename)
│   ├── covid_visualization.png  # 2x3 clinical visualization
│   ├── covid_results.json       # Final diagnosis with ensemble results
│   ├── features.json            # Detailed COVID features
│   ├── detection/
│   │   ├── covid_results.json   # AI detection results
│   │   └── features.json        # HU-based features
│   ├── segmentation/
│   │   ├── lung_mask.nii.gz     # LungMask R231 segmentation
│   │   ├── ct_array.npy         # Processed CT array
│   │   └── spacing.npy          # Voxel spacing
│   └── visualization/
│       └── covid_visualization.png
├── lung_002.nii/
│   └── ... (same structure)
├── lung_003.nii/
│   └── ... (same structure)
└── hospital_report.json         # Summary of all patients
```

### Simple Pipeline Output (Development)
```
data/output/
├── lung_001/
│   ├── covid_results.json      # Final diagnosis and probabilities
│   ├── features.json           # HU-based features
│   └── covid_visualization.png # 2x3 grid visualization
├── lung_002/
└── pipeline_summary.json       # Overall pipeline summary
```

## Clinical Results

### Diagnosis Format
```json
{
  "final_diagnosis": {
    "likelihood": "MODERATE",
    "probability": 65,
    "confidence": "medium",
    "recommendation": "Radiologist review recommended within 24 hours"
  }
}
```

### Risk Levels
- **HIGH (>75%)**: Urgent radiologist review recommended
- **MODERATE (50-75%)**: Radiologist review recommended within 24 hours
- **LOW (25-50%)**: Consider follow-up imaging in 3-5 days
- **VERY_LOW (<25%)**: Routine follow-up care

## Dependencies

### Core Requirements
- Python 3.10+
- PyTorch 2.0+
- MONAI 1.3.0
- SimpleITK 2.3.1
- nibabel 5.2.0
- lungmask (from source)
- matplotlib 3.8.2

### Kubeflow
- kfp 2.5.0
- Accessible Kubeflow cluster
- PVC volume for data persistence

## Performance

- **Processing Time**: ~30-60s per patient
- **Memory Usage**: ~2-4GB per component
- **Accuracy**: Ensemble approach improves detection reliability
- **Confidence**: High agreement between rule-based and MONAI methods

## Usage Examples

### Single Component Testing
```bash
# Test lung segmentation
python components/lung_segment.py data/input/lung_001/imaging.nii.gz temp/segmentation

# Test COVID detection
python components/covid_detect.py temp/segmentation temp/detection

# Test visualization
python components/visualize.py temp/detection temp/visualization
```

### Batch Processing
```bash
# Process all test patients
python run_pipeline_simple.py

# Check results
ls data/output/
```

## Configuration

### Input Requirements
- **Format**: NIfTI (.nii.gz)
- **Modality**: CT scans
- **HU Range**: -1000 to 400
- **Patients**: lung_001, lung_002, lung_003, lung_004

### Output Settings
- **Visualization**: PNG format, 150 DPI
- **Results**: JSON format with detailed analysis
- **Reports**: Summary statistics and recommendations

## Clinical Validation

This pipeline combines:
- **Proven HU-based analysis** (rule-based)
- **Advanced deep learning** (MONAI DenseNet121)
- **Medical-grade visualization** (clinical format)

The ensemble approach provides both:
- **Reliability** (rule-based fallback)
- **Advanced detection** (deep learning)

## Support

For issues and questions:
1. Check component logs in `data/output/*/`
2. Review `pipeline_summary.json` for overview
3. Verify input data format and structure
4. Ensure all dependencies are installed

## Version History

- **Week5**: Clean implementation with streamlined components
- Based on hospital-mlops/covid-demo with improvements:
  - Simplified component interfaces
  - Enhanced error handling
  - Better documentation
  - Cleaner file organization