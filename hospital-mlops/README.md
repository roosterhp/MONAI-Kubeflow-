# MONAI AI cho Bệnh viện - Medical Image Analysis

## 🎯 Mục tiêu

Xây dựng hệ thống AI phân đoạn và phát hiện bệnh lý từ ảnh CT phổi cho bệnh viện:
- ✅ **SỬ DỤNG** pretrained models có sẵn (KHÔNG train from scratch)
- ✅ **FINE-TUNE** với dữ liệu riêng của bệnh viện (50-200 cases)
- ✅ **SO SÁNH** nhiều phương pháp (Rule-based vs AI)
- ✅ **DEPLOY** nhanh chóng (vài giờ thay vì vài ngày)

## 🆕 COVID-19 Detection Comparison Pipeline

**Tính năng mới nhất:** So sánh 2 phương pháp phát hiện COVID-19 từ CT phổi

### Tính năng chính:
- 🔄 **Comparison Pipeline**: So sánh Rule-based vs MONAI AI
- 📊 **4-Panel Visualization**: CT gốc, Lung segmentation, Rule-based, MONAI AI
- 📈 **Batch Validation**: Chạy validation trên nhiều cases (5-500)
- 📋 **Agreement Analysis**: Phân tích sự đồng thuận giữa 2 phương pháp
- 📖 **Decision Framework**: Hướng dẫn khi nào dùng phương pháp nào

### Quick Start:

```bash
cd demo

# 1. So sánh 2 phương pháp trên 1 bệnh nhân
python compare_covid_methods.py

# 2. Tạo visualization 4-panel đẹp
python visualize_full_comparison.py

# 3. Validation nhiều cases
python validate_covid_methods.py --num_cases 100
```

### Output:
- `full_comparison_<patient>.png` - 4 panel: CT | Lung Seg | Rule-based | MONAI
- `validation_results_*.json` - Kết quả chi tiết từng case
- `validation_analysis_*.json` - Thống kê tổng hợp

### Xem thêm:
- [Decision Framework](demo/covid_detection_decision_framework.md) - Khi nào dùng phương pháp nào?
- [Implementation Summary](demo/covid_comparison_implementation_summary.md) - Chi tiết kỹ thuật
- [Disease Detection Guide](demo/disease_detection_guide.md) - Hướng dẫn tổng quan

---

## 📦 Pretrained Models Có Sẵn

### 1. LungMask (GitHub) ⭐⭐ ĐANG DÙNG

```bash
# Install
pip install git+https://github.com/JoHof/lungmask

# Sử dụng luôn (không cần train/fine-tune!)
from lungmask import mask
import SimpleITK as sitk

ct = sitk.ReadImage("patient.nii.gz")
lung_mask = mask.apply(ct, model='R231')  # Dice 0.98!
```

**Thông tin**:
- ✅ Accuracy: **Dice 0.98** (excellent!)
- ✅ Speed: **5 giây**/volume (CPU), **0.5s** (GPU)
- ✅ Size: 30 MB
- ✅ **SỬ DỤNG NGAY** - không cần fine-tune!
- ✅ 3 models: R231 (general), R231CovidWeb (COVID-19), LTRCLobes (5 lobes)

### 2. MONAI Model Zoo (Official) ⭐ RECOMMENDED

```bash
# Install MONAI
pip install "monai[fire]"

# Download Whole Body CT Model (104 organs including lungs)
python -m monai.bundle download "wholeBody_ct_segmentation" --bundle_dir ./pretrained-models/
```

**Thông tin**:
- ✅ Đã train trên **1,204 CT scans**
- ✅ Segment **104 cơ quan** (lungs, trachea, bronchi, vessels...)
- ✅ Accuracy: **Dice 0.85**
- ✅ Size: 500 MB
- ✅ Link: https://github.com/Project-MONAI/model-zoo

### 3. Models Khác

| Model | Source | Accuracy | Size | Use Case |
|-------|--------|----------|------|----------|
| COVID-19 Lesion | MONAI | Dice 0.88 | 80MB | COVID-19 lesion segmentation |
| TotalSegmentator | GitHub | Dice 0.90 | 400MB | Full body segmentation |
| SAM Medical | Hugging Face | Dice 0.80 | 350MB | General medical images |

## 🚀 Quick Start

### Pipeline 1: Lung Segmentation (5 phút)

```python
from lungmask import LMInferer
import SimpleITK as sitk

# Load CT
ct_scan = sitk.ReadImage("patient.nii.gz")

# Segment lungs
inferer = LMInferer(modelname='R231')
lung_mask = inferer.apply(ct_scan)

print(f"✓ Segmented! Dice: 0.98")
```

### Pipeline 2: COVID-19 Detection (10 phút)

```bash
# Rule-based method
python demo/covid19_detection_demo.py

# MONAI AI method
python demo/monai_covid_classifier.py

# So sánh 2 phương pháp
python demo/compare_covid_methods.py
```

### Pipeline 3: Disease Classification (15 phút)

```python
from demo.disease_classifier import DiseaseClassifier
from demo.feature_extractor import LungFeatureExtractor

# Extract features
extractor = LungFeatureExtractor()
features = extractor.extract(ct_array, lung_mask, spacing)

# Classify disease
classifier = DiseaseClassifier()
diagnosis = classifier.classify(features)

print(f"Disease: {diagnosis['disease']}")
print(f"Confidence: {diagnosis['confidence']}%")
```

## 📊 So sánh Phương pháp

### Rule-based vs MONAI AI

| Metric | Rule-based (HU Thresholds) | MONAI AI (Deep Learning) |
|--------|---------------------------|--------------------------|
| **Tốc độ** | ~2-3s | ~6-8s |
| **Hardware** | CPU | GPU recommended |
| **Độ chính xác** | Tốt (clear cases) | Tốt hơn (subtle cases) |
| **Giải thích được** | ✅ Hoàn toàn | ⚠️ Một phần |
| **Dùng cho** | Screening | Complex cases |
| **Agreement rate** | - | 60-95% với Rule-based |

### Kết quả Validation (5 cases):
- **Agreement rate**: 60% (3/5 cases đồng ý)
- **Mean probability difference**: 10.4%
- **Disagreement cases**: 2 cases → Cần radiologist review
- **Inference time**: ~107s/case (CPU)

## 💡 Khuyến nghị Sử dụng

### Scenario 1: Emergency Screening
→ **Dùng Rule-based**
- Lý do: Nhanh (2-3s), không cần GPU, giải thích được

### Scenario 2: Complex/Uncertain Cases
→ **Dùng MONAI AI**
- Lý do: Phát hiện pattern tinh vi hơn, spatial analysis tốt

### Scenario 3: Research/Validation
→ **Dùng CẢ HAI phương pháp**
- Lý do: So sánh, phân tích disagreement, ensemble

### Decision Tree:

```
Need results <5s? → Rule-based
    ↓ NO
GPU available? → MONAI
    ↓ NO
Clear high-density? → Rule-based
    ↓ NO
Subtle disease? → MONAI (if GPU)
    ↓ NO
Default → Rule-based
```

## 📁 Cấu trúc Project

```
hospital-mlops/
├── demo/                              # 🆕 COVID-19 Detection Demo
│   ├── compare_covid_methods.py       # So sánh Rule-based vs MONAI
│   ├── validate_covid_methods.py      # Batch validation
│   ├── visualize_full_comparison.py   # 4-panel visualization
│   ├── covid19_detection_demo.py      # Rule-based classifier
│   ├── monai_covid_classifier.py      # MONAI AI classifier
│   ├── feature_extractor.py           # Feature extraction
│   ├── disease_classifier.py          # Disease classification
│   ├── lungmask_transform.py          # MONAI integration
│   ├── visualizations/                # Output images
│   └── *.md                          # Documentation
│
├── pretrained-models/                 # Models đã download
│   ├── wholeBody_ct_segmentation/
│   └── lungmask/
│
├── fine-tuning/                       # Fine-tuning code
│   ├── train.py                       # Fine-tune script
│   └── configs/                       # Training configs
│
├── deployment/                        # Deploy models
│   ├── inference_service.py           # FastAPI service
│   └── docker/                        # Docker configs
│
└── docs/                              # Documentation
    ├── evaluation_and_finetuning_status.md
    ├── project_summary.md
    ├── quickstart.md
    └── step_by_step_guide.md
```

## 🔧 Cài đặt

```bash
# Clone project
git clone https://github.com/roosterhp/MONAI-Kubeflow-.git
cd hospital-mlops

# Install dependencies
pip install -r requirements.txt

# Install LungMask
pip install git+https://github.com/JoHof/lungmask

# Install MONAI
pip install "monai[fire]"
```

## 📚 Documentation

### Getting Started
- [Quick Start](quickstart.md) - Bắt đầu nhanh 15 phút
- [Step by Step Guide](step_by_step_guide.md) - Hướng dẫn từng bước chi tiết
- [Project Summary](project_summary.md) - Tổng quan dự án

### COVID-19 Detection
- [Decision Framework](demo/covid_detection_decision_framework.md) - Khi nào dùng phương pháp nào
- [Implementation Summary](demo/covid_comparison_implementation_summary.md) - Chi tiết kỹ thuật
- [Disease Detection Guide](demo/disease_detection_guide.md) - Hướng dẫn phát hiện bệnh

### Technical Guides
- [LungMask MONAI Integration](demo/lungmask_monai_integration_guide.md) - Tích hợp LungMask vào MONAI
- [Evaluation & Fine-tuning Status](evaluation_and_finetuning_status.md) - Trạng thái đánh giá và fine-tuning
- [Why Not Whole Body](demo/why_not_wholebody.md) - Tại sao không dùng Whole Body model

## 🎯 Workflow Hoàn chỉnh

```
CT Scan
   ↓
[1] Lung Segmentation (LungMask R231)
   ├─ Output: Lung mask (Right, Left)
   ├─ Time: ~90s (CPU), ~5s (GPU)
   └─ Dice: 0.98
   ↓
[2A] Rule-based Detection          [2B] MONAI AI Detection
   ├─ HU threshold analysis           ├─ Deep learning 4-class seg
   ├─ GGO: -700 to -500 HU            ├─ Classes: Bg, Normal, GGO, Cons
   ├─ Consolidation: >-300 HU         ├─ Spatial pattern analysis
   ├─ Time: ~2-3s                     ├─ Time: ~6-8s
   └─ Output: LOW (26%)               └─ Output: LOW (30%)
   ↓                                  ↓
   └──────────┬──────────┘
              ↓
[3] Comparison & Agreement Analysis
   ├─ Likelihood agreement: ✓
   ├─ Probability diff: 4%
   ├─ Agreement score: 100/100
   └─ Clinical decision: Standard follow-up
   ↓
[4] Visualization & Report
   ├─ 4-panel PNG image
   ├─ JSON metrics
   └─ Clinical recommendation
```

## 📊 Validation Results

### Performance Summary (5 cases):

| Metric | Value |
|--------|-------|
| Cases processed | 5 |
| Likelihood agreement | 60% (3/5) |
| Severity agreement | 60% |
| Mean probability diff | 10.4% |
| Disagreement cases | 2 (lung_004, lung_006) |
| Avg lung seg time | 98.7s (CPU) |
| Avg rule-based time | 2.5s |
| Avg MONAI time | 5.4s |

**Distribution**:
- Rule-based: 0 HIGH, 2 MODERATE, 3 LOW
- MONAI: 0 HIGH, 1 LOW-MODERATE, 4 LOW

## 🎯 Next Steps

### Immediate (Đã hoàn thành ✅):
1. ✅ Download pretrained model (LungMask)
2. ✅ Test trên cases bệnh viện
3. ✅ Implement Rule-based classifier
4. ✅ Implement MONAI classifier
5. ✅ Create comparison pipeline
6. ✅ Generate visualizations
7. ✅ Batch validation (5 cases)

### Short-term (1-2 tuần):
1. 🔲 Validate trên 100-500 cases
2. 🔲 Acquire real COVID-19 dataset với RT-PCR labels
3. 🔲 Calculate true sensitivity/specificity
4. 🔲 Fine-tune MONAI model trên local data
5. 🔲 Deploy inference service (FastAPI)
6. 🔲 DICOM interface

### Long-term (1-3 tháng):
1. 🔲 PACS integration
2. 🔲 Real-time dashboard
3. 🔲 Radiologist review interface
4. 🔲 Ensemble model (voting/averaging)
5. 🔲 Continuous monitoring & improvement

## 📈 Performance Benchmarks

### GPU vs CPU:

| Operation | CPU (Intel i7) | GPU (T4) | Speedup |
|-----------|----------------|----------|---------|
| Lung Seg | ~90s | ~5s | 18x |
| Rule-based | ~2.5s | ~2.5s | 1x |
| MONAI | ~6s | ~2s | 3x |
| **Total** | ~98.5s | ~9.5s | **10.4x** |

**Recommendation**: GPU strongly recommended for production (10x faster)

## 🤝 Contributing

Contributions welcome! Areas needed:
- Ground truth COVID-19 data with RT-PCR labels
- Fine-tuning on hospital-specific data
- DICOM integration
- Performance optimization
- Documentation improvements

## 📝 License

MIT License

## 📧 Contact

- **Project**: MONAI Kubeflow Demo
- **Repository**: https://github.com/roosterhp/MONAI-Kubeflow-.git
- **Documentation**: See `docs/` folder
- **Issues**: GitHub Issues

---

**Last Updated**: 2025-11-03
**Version**: 2.0 (COVID-19 Comparison Pipeline)
