# 📋 Hospital MLOps Project - Cấu trúc và Chức năng

**Dự án**: MONAI Medical Imaging với Kubeflow Pipeline
**Mục tiêu**: Phát triển hệ thống MLOps cho phân tích hình ảnh y tế (COVID-19 detection)
**Công nghệ**: MONAI, PyTorch, Kubeflow, LungMask

---

## 📂 Cấu trúc Tổng quan

```
hospital-mlops/
├── demo/                           # Demo scripts và workflows chính
├── pretrained-models/              # Pretrained MONAI models
├── deployment/                     # Production deployment
├── docs/                          # Documentation
└── [Configuration files]          # Setup và guides
```

---

## 📁 Chi tiết Folders và Files

### 1. 📂 `demo/` - Demo Workflows và Core Implementation

Folder chứa tất cả demo scripts và implementation chính của project.

#### **A. COVID-19 Detection Pipeline**

##### `lungmask_transform.py` ⭐ **CORE**
**Chức năng**: Custom MONAI Transform để tích hợp LungMask vào MONAI pipeline
- Convert giữa MONAI MetaTensor và SimpleITK Image
- Preserve metadata (spacing, affine, orientation)
- Class `LungMaskTransform`: Transform cơ bản
- Class `LungMaskTransformd`: Dictionary-based transform (MONAI compatible)
- **Input**: CT scan (MetaTensor)
- **Output**: Lung segmentation mask (0=background, 1=right lung, 2=left lung)

##### `feature_extractor.py` ⭐ **CORE**
**Chức năng**: Trích xuất đặc trưng COVID-19 từ CT scan
- Class `LungFeatureExtractor`: Extract HU-based features
- Phân tích Ground-Glass Opacity (GGO): HU -700 to -500
- Phân tích Consolidation: HU > -300
- Đếm voxels, tính phần trăm, phân tích phân bố không gian
- Bilateral involvement detection
- **Input**: CT array, lung mask, spacing
- **Output**: Dictionary với COVID features

##### `covid19_detection_demo.py` ⭐ **CORE**
**Chức năng**: Rule-based COVID-19 classifier
- Class `COVID19Classifier`: Rule-based classification
- Scoring system dựa trên:
  - GGO percentage
  - Consolidation percentage
  - Bilateral involvement
  - Peripheral distribution
- **Output**: COVID likelihood (HIGH/MODERATE/LOW), probability, severity

##### `monai_covid_classifier.py` ⭐ **CORE**
**Chức năng**: AI-based COVID-19 classifier sử dụng MONAI pretrained model
- Class `MONAICOVIDClassifier`: Deep learning classifier
- Load MONAI bundle (covid19_lung_ct_segmentation)
- 4-class segmentation: Background, Normal, GGO, Consolidation
- Sliding window inference
- **Output**: Segmentation mask + COVID analysis

##### `compare_covid_methods.py` ⭐ **CORE**
**Chức năng**: So sánh Rule-based vs MONAI AI methods
- Chạy cả 2 methods trên cùng CT scan
- Agreement analysis (likelihood, probability, severity)
- Metrics comparison (GGO%, Consolidation%)
- Generate visualization và recommendations
- **Output**: Comparison report + visualization

##### `validate_covid_methods.py`
**Chức năng**: Validation script trên multiple cases
- Test trên nhiều CT scans
- Calculate agreement rate giữa 2 methods
- Statistical analysis
- **Output**: validation_results.json, validation_analysis.json

##### `visualize_full_comparison.py`
**Chức năng**: Tạo visualization cho comparison results
- Multi-panel comparison plots
- Metrics visualization
- Agreement analysis charts

---

#### **B. Fine-tuning Workflows**

##### `finetune_covid_model.py` ⭐ **IMPORTANT**
**Chức năng**: Production-ready fine-tuning script
- Class `COVIDFineTuner`: Complete fine-tuning pipeline
- Load pretrained MONAI model
- Freeze encoder layers (transfer learning)
- Custom data loader
- Training loop với validation
- Model saving và checkpointing
- **Use case**: Fine-tune với dữ liệu riêng của bệnh viện

##### `prepare_custom_data.py`
**Chức năng**: Chuẩn bị dữ liệu custom cho fine-tuning
- Class `DataPreparator`: Data organization
- Convert DICOM → NIfTI
- Create train/val split
- Generate dummy masks (for demo)
- Validate data quality
- **Output**: Organized data structure

##### `demo_finetune_workflow.py` ⭐ **DEMO**
**Chức năng**: Demo hoàn chỉnh của fine-tuning workflow
- Sử dụng sample data có sẵn
- Tạo synthetic COVID labels
- Mini training loop (5 epochs)
- Demonstrate full workflow
- **Output**: demo_finetuned_model.pth, training data

##### `visualize_demo_results.py`
**Chức năng**: Visualize kết quả demo fine-tuning
- Training loss curve
- Sample data visualization
- Summary report
- **Output**: 3 PNG images trong demo_data/

---

#### **C. Disease Detection (General)**

##### `disease_classifier.py`
**Chức năng**: Generic disease classifier framework
- Expandable cho nhiều bệnh khác ngoài COVID-19
- Rule-based classification system
- Feature-based detection

---

#### **D. Utilities và Downloads**

##### `download_monai_covid_model.py`
**Chức năng**: Download MONAI COVID-19 pretrained model
- Use MONAI Bundle API
- Download model: `covid19_lung_ct_segmentation`
- Extract và organize
- **Output**: monai_models/covid19_lung_ct_segmentation/

---

#### **E. Documentation trong demo/**

##### `lungmask_monai_integration_guide.md` ⭐ **GUIDE**
**Nội dung**: Hướng dẫn tích hợp LungMask với MONAI
- Kiến trúc integration
- Code examples
- Best practices
- Troubleshooting

##### `covid_comparison_implementation_summary.md`
**Nội dung**: Tóm tắt implementation của COVID comparison pipeline
- Pipeline architecture
- Methods comparison
- Results interpretation

##### `covid_detection_decision_framework.md`
**Nội dung**: Framework để ra quyết định lâm sàng
- Decision tree
- Clinical recommendations
- When to use which method

##### `disease_detection_guide.md`
**Nội dung**: Hướng dẫn chung về disease detection
- General concepts
- Feature engineering
- Classification strategies

##### `why_not_wholebody.md`
**Nội dung**: Giải thích tại sao không dùng WholeBody model cho COVID
- Model comparison
- Performance analysis
- Recommendation: Specialized models tốt hơn

---

#### **F. Sample Data**

##### `sample-data/Task06_Lung/`
**Chức năng**: Sample CT scans từ Medical Segmentation Decathlon
- `dataset.json`: Metadata
- `imagesTr/`: Training CT scans (.nii.gz)
- **Purpose**: Demo và testing

---

### 2. 📂 `pretrained-models/` - MONAI Pretrained Models

#### `wholeBody_ct_segmentation/`
**Chức năng**: MONAI Bundle cho whole-body organ segmentation
- `configs/`: JSON configs cho train, inference, evaluate
  - `train.json`: Training configuration
  - `inference.json`: Inference settings
  - `evaluate.json`: Evaluation metrics
  - `metadata.json`: Model metadata
- `docs/README.md`: Model documentation
- **Model**: SegResNet
- **Classes**: 104 organ classes (liver, kidney, spleen, etc.)

#### `download.py`
**Chức năng**: Script để download MONAI bundles
- Use MONAI Bundle API
- Download và extract models

---

### 3. 📂 `deployment/` - Production Deployment

#### `serve.py`
**Chức năng**: Model serving script
- REST API endpoint
- Model inference service
- Production-ready deployment

#### `README.md`
**Nội dung**: Deployment guide
- How to deploy
- API documentation
- Configuration

---

### 4. 📂 `docs/` - Documentation

#### `PRETRAINED_MODELS.md`
**Nội dung**: Danh sách và mô tả các pretrained models
- Model comparison table
- Performance metrics
- Use case recommendations

---

### 5. 📄 Root Configuration Files

#### `README.md` ⭐ **MAIN DOCS**
**Nội dung**: Main documentation
- Project overview
- Quick start guide
- Installation instructions
- Examples

#### `quickstart.md`
**Nội dung**: Quick start guide
- 5-minute setup
- Basic usage
- First demo

#### `step_by_step_guide.md`
**Nội dung**: Chi tiết từng bước
- Detailed walkthrough
- Screenshots
- Troubleshooting

#### `evaluation_and_finetuning_status.md`
**Nội dung**: Status report
- Current progress
- Completed tasks
- Future work

#### `FINE_TUNING_GUIDE.md`
**Nội dung**: Hướng dẫn fine-tuning chi tiết
- Kịch bản 1: Fine-tune MONAI COVID Model
- Kịch bản 2: Fine-tune LungMask Model
- Kịch bản 3: Fine-tune với MONAI Bundle
- Troubleshooting và best practices

---

## 🔑 Key Workflows

### **Workflow 1: COVID-19 Detection**
```
CT Scan
  → lungmask_transform.py (Lung Segmentation)
    → feature_extractor.py (Extract Features)
      → covid19_detection_demo.py (Rule-based) OR
      → monai_covid_classifier.py (AI-based)
        → COVID-19 Analysis Result
```

### **Workflow 2: Method Comparison**
```
CT Scan
  → compare_covid_methods.py
    → Run both methods in parallel
    → Agreement analysis
    → Visualization
    → Clinical recommendation
```

### **Workflow 3: Fine-tuning**
```
Custom Data
  → prepare_custom_data.py (Data Preparation)
    → finetune_covid_model.py (Training)
      → Fine-tuned Model
```

### **Workflow 4: Demo Fine-tuning**
```
Sample Data
  → demo_finetune_workflow.py (Complete Demo)
    → visualize_demo_results.py (Visualization)
      → Training Report + Images
```

---

## 📊 Thống kê Project

### **Code Files**
- Python scripts: 19 files
- Core implementation: 8 files
- Demo/utilities: 11 files

### **Documentation**
- Markdown files: 10 files
- Guides: 4 files
- READMEs: 3 files

### **Models**
- Pretrained models: 2 bundles
- Config files: 7 JSON configs

### **Functionality Coverage**
- ✅ Lung segmentation (LungMask integration)
- ✅ COVID-19 detection (Rule-based + AI)
- ✅ Method comparison và validation
- ✅ Fine-tuning pipeline (production-ready)
- ✅ Demo workflows
- ✅ Visualization tools
- ✅ Documentation đầy đủ

---

## 🎯 Files quan trọng nhất (Top 10)

1. **`lungmask_transform.py`** - Core integration với MONAI
2. **`feature_extractor.py`** - Feature engineering
3. **`covid19_detection_demo.py`** - Rule-based classifier
4. **`monai_covid_classifier.py`** - AI classifier
5. **`compare_covid_methods.py`** - Comparison pipeline
6. **`finetune_covid_model.py`** - Production fine-tuning
7. **`demo_finetune_workflow.py`** - Demo workflow
8. **`prepare_custom_data.py`** - Data preparation
9. **`lungmask_monai_integration_guide.md`** - Integration guide
10. **`README.md`** - Main documentation

---

## 🚀 Use Cases

### **Use Case 1: Phân tích COVID-19**
**Files cần**: `lungmask_transform.py`, `feature_extractor.py`, `covid19_detection_demo.py`
**Output**: COVID likelihood, severity, detailed metrics

### **Use Case 2: So sánh Methods**
**Files cần**: `compare_covid_methods.py`, `validate_covid_methods.py`
**Output**: Comparison report, agreement analysis

### **Use Case 3: Fine-tune Model**
**Files cần**: `prepare_custom_data.py`, `finetune_covid_model.py`
**Output**: Custom trained model

### **Use Case 4: Demo cho Presentation**
**Files cần**: `demo_finetune_workflow.py`, `visualize_demo_results.py`
**Output**: Training visualizations, report images

---

## 📈 Kết quả Demo Fine-tuning (Đã chạy thành công)

### **Training Results**
- **Epochs**: 5 (mini demo)
- **Initial Loss**: 2.5641
- **Final Loss**: 2.2206
- **Improvement**: 13.4%
- **Model saved**: `demo_data/demo_finetuned_model.pth`

### **Visualizations Created**
1. `01_training_loss.png` - Training loss curve
2. `02_sample_data.png` - Sample CT + COVID labels (4 classes)
3. `03_summary_report.png` - Complete training summary

### **Data Generated**
- **Train**: 3 CT scans với synthetic COVID labels
- **Val**: 3 CT scans với synthetic COVID labels
- **Classes**: Background (0), Normal (1), GGO (2), Consolidation (3)

---

## 📈 Progress Status

### **Completed ✅**
- [x] LungMask integration với MONAI
- [x] Rule-based COVID classifier
- [x] MONAI AI classifier
- [x] Method comparison pipeline
- [x] Fine-tuning framework (production + demo)
- [x] Demo workflows thành công
- [x] Visualization tools
- [x] Documentation đầy đủ

### **In Progress 🔄**
- [ ] Deploy lên Kubeflow Pipeline
- [ ] REST API endpoint
- [ ] Frontend interface

### **Future Work 🔮**
- [ ] Multi-disease detection
- [ ] Real-time inference
- [ ] Cloud deployment
- [ ] Clinical validation

---

## 📖 Tài liệu tham khảo

### **Documentation Files**
1. `README.md` - Hướng dẫn tổng quan
2. `quickstart.md` - Quick start 5 phút
3. `step_by_step_guide.md` - Chi tiết từng bước
4. `FINE_TUNING_GUIDE.md` - Hướng dẫn fine-tuning
5. `evaluation_and_finetuning_status.md` - Status báo cáo

### **Technical Guides**
- `demo/lungmask_monai_integration_guide.md` - Tích hợp LungMask
- `demo/covid_comparison_implementation_summary.md` - So sánh methods
- `demo/covid_detection_decision_framework.md` - Clinical decision framework
- `docs/PRETRAINED_MODELS.md` - Pretrained models

---

**Generated**: November 5, 2025
**Last Updated**: Demo fine-tuning workflow completed successfully
**Version**: 2.0
**Status**: ✅ Ready for presentation
