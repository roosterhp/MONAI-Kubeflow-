"""
Setup Hospital Demo Data
Tạo dữ liệu mẫu giả lập để test workflow bệnh viện
"""

import os
import json
import numpy as np
from pathlib import Path
import SimpleITK as sitk


def create_mock_ct_scan(patient_id: str, output_path: str):
    """Tạo mock CT scan giả lập cho testing"""
    print(f"Tạo mock CT scan cho {patient_id}...")

    # Tạo mock 3D CT array (giả lập胸部)
    # Size: 512x512x50 (typical chest CT)
    ct_array = np.random.randint(-1000, 400, (50, 512, 512), dtype=np.int16)

    # Thêm một số "features" giả lập:
    # - Phổi (HU -500 đến -300)
    # - Một số GGO consolidation để test detection
    lung_mask = np.zeros_like(ct_array)

    # Tạo vùng phổi cơ bản (ở giữa)
    center_x, center_y = 256, 256
    for z in range(10, 40):  # Middle slices
        for x in range(150, 350):
            for y in range(150, 350):
                dist = np.sqrt((x-center_x)**2 + (y-center_y)**2)
                if dist < 80:  # Within lung radius
                    lung_mask[z, x, y] = 1
                    # Set lung HU values
                    ct_array[z, x, y] = np.random.randint(-700, -300)

    # Thêm một số GGO giả lập (HU -700 đến -500)
    for z in range(15, 25):
        if np.random.random() > 0.3:  # 70% chance
            x_pos = np.random.randint(180, 320)
            y_pos = np.random.randint(180, 320)
            size = np.random.randint(10, 30)

            for x in range(max(0, x_pos-size), min(512, x_pos+size)):
                for y in range(max(0, y_pos-size), min(512, y_pos+size)):
                    if lung_mask[z, x, y] == 1:
                        ct_array[z, x, y] = np.random.randint(-700, -500)

    # Add some consolidation (HU > -300)
    for z in range(20, 30):
        if np.random.random() > 0.7:  # 30% chance
            x_pos = np.random.randint(200, 300)
            y_pos = np.random.randint(200, 300)
            size = np.random.randint(5, 15)

            for x in range(max(0, x_pos-size), min(512, x_pos+size)):
                for y in range(max(0, y_pos-size), min(512, y_pos+size)):
                    if lung_mask[z, x, y] == 1:
                        ct_array[z, x, y] = np.random.randint(-300, 100)

    # Tạo SimpleITK image
    ct_image = sitk.GetImageFromArray(ct_array)
    ct_image.SetSpacing((1.0, 1.0, 2.0))  # Typical CT spacing
    ct_image.SetOrigin((0, 0, 0))

    # Lưu file
    sitk.WriteImage(ct_image, output_path)
    print(f"Đã tạo mock CT: {output_path}")
    print(f"  Shape: {ct_array.shape}")
    print(f"  HU range: [{ct_array.min()}, {ct_array.max()}]")


def setup_hospital_demo():
    """Thiết lập môi trường demo cho bệnh viện"""
    print("SET UP HOSPITAL DEMO ENVIRONMENT")
    print("="*60)

    # Create directory structure
    base_dir = Path("data")
    input_dir = base_dir / "weekly_input"
    output_dir = base_dir / "hospital_output"

    # Ensure directories exist
    input_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Tạo dữ liệu mẫu cho 4 bệnh nhân
    patients = [
        "PATIENT001",
        "PATIENT002",
        "PATIENT003",
        "PATIENT004"
    ]

    print(f"\nTao du lieu mock cho {len(patients)} benh nhan...")

    for patient_id in patients:
        patient_dir = input_dir / patient_id
        patient_dir.mkdir(exist_ok=True)

        # Create mock CT scan
        ct_file = patient_dir / "imaging.nii.gz"
        create_mock_ct_scan(patient_id, str(ct_file))

        # Create patient info file
        patient_info = {
            "patient_id": patient_id,
            "scan_date": "2024-11-14",
            "description": f"Mock CT scan for {patient_id}",
            "notes": "This is simulated data for testing hospital workflow"
        }

        info_file = patient_dir / "patient_info.json"
        with open(info_file, 'w') as f:
            json.dump(patient_info, f, indent=2)

        print(f"  [OK] {patient_id}: {ct_file}")

    # Create instruction file
    instructions = {
        "hospital_workflow_instructions": {
            "input_structure": {
                "weekly_scan_folder": "data/weekly_input",
                "description": "Để dữ liệu CT scan của bệnh nhân vào đây",
                "supported_formats": [
                    "weekly_input/PATIENT001/imaging.nii.gz",
                    "weekly_input/PATIENT001/CT_001.nii.gz"
                ]
            },
            "how_to_run": {
                "local_testing": "python hospital_pipeline_runner.py",
                "kubeflow_pipeline": "python hospital_kubeflow_pipeline.py",
                "single_patient": "python run_pipeline_simple.py"
            },
            "output_structure": {
                "base_folder": "data/hospital_output",
                "description": "Kết quả sẽ tự động xuất ra đây",
                "files": [
                    "hospital_output/PATIENT001/covid_visualization.png",
                    "hospital_output/PATIENT001/covid_results.json",
                    "hospital_output/hospital_report.json"
                ]
            },
            "expected_results": {
                "visualizations": "Mỗi bệnh nhân sẽ có ảnh 2x3 grid",
                "reports": "Báo cáo y khoa với likelihood và probability",
                "summary": "Báo cáo tổng kết toàn bộ bệnh viện"
            }
        }
    }

    with open("data/hospital_instructions.json", 'w') as f:
        json.dump(instructions, f, indent=2, ensure_ascii=False)

    print(f"\n[INFO] Đã tạo file hướng dẫn: data/hospital_instructions.json")

    # Tạo README cho hospital demo
    readme_content = """# Hospital COVID-19 Detection Demo

## 🏥 Môi trường Bệnh viện Demo

Đây là môi trường giả lập để test workflow COVID-19 detection cho bệnh viện.

## 📁 Cấu trúc thư mục

### Input (Dữ liệu đầu vào)
```
data/weekly_input/
├── PATIENT001/
│   ├── imaging.nii.gz          # CT scan
│   └── patient_info.json       # Thông tin bệnh nhân
├── PATIENT002/
│   ├── imaging.nii.gz
│   └── patient_info.json
└── ...
```

### Output (Kết quả)
```
data/hospital_output/
├── PATIENT001/
│   ├── covid_visualization.png  # Ảnh 2x3 grid
│   ├── covid_results.json       # Kết quả detection
│   └── features.json            # Features chi tiết
├── PATIENT002/
│   └── ...
└── hospital_report.json         # Báo cáo tổng kết
```

## 🚀 Cách sử dụng

### 1. Local Testing (Development)
```bash
cd week5
python hospital_pipeline_runner.py
```

### 2. Kubeflow Pipeline (Production)
```bash
cd week5
python hospital_kubeflow_pipeline.py
# Tạo file: hospital_covid_detection_weekly.yaml
# Deploy lên Kubeflow cluster
```

### 3. Single Patient Testing
```bash
cd week5
python run_pipeline_simple.py
```

## 📊 Kết quả mong đợi

- **Visualizations**: 2x3 grid layout cho mỗi bệnh nhân
- **COVID Detection**: Ensemble rule-based + MONAI
- **Hospital Report**: Báo cáo tổng kết với phân bổ rủi ro
- **Auto-discovery**: Tự động phát hiện bệnh nhân trong input folder

## 🎯 Workflow

1. **Load Data**: Tự động scan `data/weekly_input/`
2. **Lung Segmentation**: LungMask R231
3. **COVID Detection**: Rule-based + MONAI ensemble
4. **Visualization**: 2x3 clinical grid
5. **Report**: Tổng kết toàn bộ bệnh viện

## 📝 Ghi chú

- Dữ liệu demo là mock data để test
- HU ranges: -1000 đến 400 (realistic CT values)
- Mock GGO và consolidation được thêm vào để test detection
- Pipeline tự động handle errors và continue với patients khác
"""

    with open("data/HOSPITAL_DEMO_README.md", 'w') as f:
        f.write(readme_content)

    print(f"[INFO] Đã tạo README: data/HOSPITAL_DEMO_README.md")

    print(f"\n[SUCCESS] Hospital demo setup completed!")
    print(f"\n[STATISTICS]:")
    print(f"  - So benh nhan demo: {len(patients)}")
    print(f"  - Input directory: {input_dir}")
    print(f"  - Output directory: {output_dir}")
    print(f"  - Mock CT scans: {len(patients)} files")
    print(f"  - Total size: ~{len(patients)*50}MB")

    print(f"\n[READY TO TEST]")
    print(f"  Run: python hospital_pipeline_runner.py")


if __name__ == "__main__":
    setup_hospital_demo()