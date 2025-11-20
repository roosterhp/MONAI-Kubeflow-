"""
Hospital Pipeline Runner
Chạy toàn bộ pipeline COVID-19 detection cho dữ liệu tuần của bệnh viện
"""

import os
import sys
import json
import time
import shutil
from pathlib import Path
from datetime import datetime
import subprocess


def run_component_with_timeout(component_name: str, args: list, timeout: int = 600):
    """Run component với timeout và error handling"""
    print(f"\n{'='*60}")
    print(f"CHẠY COMPONENT: {component_name.upper()}")
    print(f"{'='*60}")
    print(f"Command: python {args}")

    start_time = time.time()

    try:
        result = subprocess.run(
            ['python'] + args,
            timeout=timeout,
            capture_output=True,
            text=True
        )

        elapsed_time = time.time() - start_time

        if result.returncode == 0:
            print(f"[OK] {component_name} hoàn thành trong {elapsed_time:.1f}s")
            if result.stdout:
                print("Output:", result.stdout[-500:])  # Hiển thị 500 ký tự cuối
            return True
        else:
            print(f"[ERROR] {component_name} thất bại sau {elapsed_time:.1f}s")
            print("Error:", result.stderr)
            return False

    except subprocess.TimeoutExpired:
        print(f"[ERROR] {component_name} timeout sau {timeout}s")
        return False
    except Exception as e:
        print(f"[ERROR] {component_name} thất bại: {e}")
        return False


def process_single_patient(patient_info: dict, base_output_dir: str) -> bool:
    """
    Xử lý 1 bệnh nhân: Lung Seg -> COVID Detect -> Visualization
    """
    patient_id = patient_info["id"]
    ct_file = patient_info["prepared_ct_file"]
    working_dir = patient_info["working_dir"]

    print(f"\n{'🏥'*20}")
    print(f"XỬ LÝ BỆNH NHÂN: {patient_id}")
    print(f"{'🏥'*20}")
    print(f"CT File: {ct_file}")
    print(f"Working: {working_dir}")

    # Create output directories
    patient_output_dir = Path(base_output_dir) / patient_id
    segmentation_dir = patient_output_dir / "segmentation"
    detection_dir = patient_output_dir / "detection"
    visualization_dir = patient_output_dir / "visualization"

    # Step 1: Lung Segmentation
    if not run_component_with_timeout(
        "lung_segmentation",
        ["components/lung_segment.py", ct_file, str(segmentation_dir)]
    ):
        return False

    # Step 2: COVID Detection
    if not run_component_with_timeout(
        "covid_detection",
        ["components/covid_detect.py", str(segmentation_dir), str(detection_dir)]
    ):
        return False

    # Step 3: Visualization
    if not run_component_with_timeout(
        "visualization",
        ["components/visualize.py", str(detection_dir), str(visualization_dir)]
    ):
        return False

    # Copy final results to main patient directory
    results_file = detection_dir / "covid_results.json"
    features_file = detection_dir / "features.json"
    viz_file = visualization_dir / "covid_visualization.png"

    if results_file.exists():
        shutil.copy2(results_file, patient_output_dir)
    if features_file.exists():
        shutil.copy2(features_file, patient_output_dir)
    if viz_file.exists():
        shutil.copy2(viz_file, patient_output_dir)

    print(f"\n[SUCCESS] Bệnh nhân {patient_id} xử lý xong!")
    return True


def generate_hospital_report(output_dir: str, metadata: dict, patient_results: dict):
    """Tạo báo cáo tổng kết cho bệnh viện"""
    print(f"\n{'📊'*20}")
    print("TẠO BÁO CÁO BỆNH VIỆN")
    print(f"{'📊'*20}")

    report = {
        "hospital_report": {
            "scan_date": metadata["scan_time"],
            "report_generated": datetime.now().isoformat(),
            "total_patients": len(patient_results),
            "successful": sum(1 for result in patient_results.values() if result),
            "failed": sum(1 for result in patient_results.values() if not result),
            "success_rate": f"{sum(1 for result in patient_results.values() if result)/len(patient_results)*100:.1f}%",
            "pipeline_config": metadata["pipeline_config"]
        },
        "patients": {},
        "summary": {
            "high_risk": 0,
            "moderate_risk": 0,
            "low_risk": 0,
            "very_low_risk": 0
        }
    }

    # Analyze each patient's results
    for patient_id, success in patient_results.items():
        patient_dir = Path(output_dir) / patient_id

        if success:
            results_file = patient_dir / "covid_results.json"

            if results_file.exists():
                try:
                    with open(results_file, 'r') as f:
                        results = json.load(f)

                    diagnosis = results['final_diagnosis']
                    likelihood = diagnosis['likelihood']

                    report["patients"][patient_id] = {
                        "status": "completed",
                        "likelihood": likelihood,
                        "probability": diagnosis['probability'],
                        "confidence": diagnosis['confidence'],
                        "recommendation": diagnosis['recommendation']
                    }

                    # Update summary counts
                    if likelihood == 'HIGH':
                        report["summary"]["high_risk"] += 1
                    elif likelihood == 'MODERATE':
                        report["summary"]["moderate_risk"] += 1
                    elif likelihood == 'LOW':
                        report["summary"]["low_risk"] += 1
                    else:
                        report["summary"]["very_low_risk"] += 1

                except Exception as e:
                    report["patients"][patient_id] = {
                        "status": "completed",
                        "error": f"Lỗi đọc kết quả: {e}"
                    }
            else:
                report["patients"][patient_id] = {
                    "status": "completed",
                    "error": "Không tìm thấy file kết quả"
                }
        else:
            report["patients"][patient_id] = {
                "status": "failed",
                "error": "Xử lý thất bại"
            }

    # Save hospital report
    report_file = Path(output_dir) / "hospital_report.json"
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print(f"Báo cáo bệnh viện đã lưu: {report_file}")

    # Print summary
    print(f"\n{'='*60}")
    print("BÁO CÁO TỔNG KẾT BỆNH VIỆN")
    print(f"{'='*60}")
    print(f"Ngày scan: {report['hospital_report']['scan_date']}")
    print(f"Tổng bệnh nhân: {report['hospital_report']['total_patients']}")
    print(f"Thành công: {report['hospital_report']['successful']}")
    print(f"Thất bại: {report['hospital_report']['failed']}")
    print(f"Tỷ lệ thành công: {report['hospital_report']['success_rate']}")

    print(f"\nPHÂN BỔ RỦI RO COVID-19:")
    print(f"  🔴 Cao risco: {report['summary']['high_risk']} bệnh nhân")
    print(f"  🟡 Trung bình: {report['summary']['moderate_risk']} bệnh nhân")
    print(f"  🟢 Thấp: {report['summary']['low_risk']} bệnh nhân")
    print(f"  ✅ Rất thấp: {report['summary']['very_low_risk']} bệnh nhân")

    # Alert for high-risk patients
    if report['summary']['high_risk'] > 0:
        print(f"\n⚠️  CẢNH BÁO: Có {report['summary']['high_risk']} bệnh nhân nguy cơ cao!")
        print("   Khuyến nghị: Bác sĩ cần xem xét gấp các ca này")

    return report


def main():
    """Main hospital pipeline runner"""
    print("🏥 HỆ THỐNG PHÁT HIỆN COVID-19 BỆNH VIỆN - TUẦN SCAN 🏥")
    print("=" * 70)
    print("Tự động xử lý toàn bộ dữ liệu CT scan tuần của bệnh viện")
    print("=" * 70)

    # Configuration
    config = {
        "input_weekly_dir": "data/weekly_input",      # Folder chứa dữ liệu tuần
        "working_dir": "data/hospital_working",       # Thư mục làm việc
        "metadata_file": "data/hospital_working/patients_metadata.json",
        "output_dir": "data/hospital_output"          # Folder kết quả cuối cùng
    }

    # Create output directory
    Path(config["output_dir"]).mkdir(parents=True, exist_ok=True)

    print(f"\nCấu hình:")
    print(f"  Input tuần: {config['input_weekly_dir']}")
    print(f"  Working: {config['working_dir']}")
    print(f"  Output: {config['output_dir']}")

    # Step 1: Load dữ liệu bệnh viện
    print(f"\n{'='*60}")
    print("BƯỚC 1: TỰ ĐỘNG TẢI DỮ LIỆU BỆNH VIỆN")
    print(f"{'='*60}")

    if not run_component_with_timeout(
        "load_data",
        ["components/load_data.py",
         config["input_weekly_dir"],
         config["working_dir"],
         config["metadata_file"]]
    ):
        print("[ERROR] Không thể tải dữ liệu bệnh viện!")
        return 1

    # Load patient metadata
    try:
        with open(config["metadata_file"], 'r') as f:
            metadata = json.load(f)

        patients = metadata["patients"]
        print(f"[INFO] Tìm thấy {len(patients)} bệnh nhân cần xử lý")
    except Exception as e:
        print(f"[ERROR] Không thể đọc metadata: {e}")
        return 1

    # Step 2: Process tất cả bệnh nhân
    print(f"\n{'='*60}")
    print("BƯỚC 2: XỬ LÝ COVID-19 CHO TỪNG BỆNH NHÂN")
    print(f"{'='*60}")

    patient_results = {}
    total_start_time = time.time()

    for i, patient_info in enumerate(patients, 1):
        print(f"\n{'='*60}")
        print(f"BỆNH NHÂN {i}/{len(patients)}: {patient_info['id']}")
        print(f"{'='*60}")

        success = process_single_patient(patient_info, config["output_dir"])
        patient_results[patient_info['id']] = success

    total_elapsed_time = time.time() - total_start_time

    # Step 3: Generate hospital report
    print(f"\n{'='*60}")
    print("BƯỚC 3: TẠO BÁO CÁO TỔNG KẾT")
    print(f"{'='*60}")

    hospital_report = generate_hospital_report(
        config["output_dir"],
        metadata,
        patient_results
    )

    # Final status
    print(f"\n{'='*60}")
    print("PIPELINE HOÀN TẤT")
    print(f"{'='*60}")
    print(f"Thời gian tổng: {total_elapsed_time:.1f}s")
    print(f"Trung bình/bệnh nhân: {total_elapsed_time/len(patients):.1f}s")

    successful_count = sum(1 for result in patient_results.values() if result)
    if successful_count == len(patients):
        print("🎉 Tất cả bệnh nhân xử lý thành công!")
        print(f"\n📁 Kết quả đã lưu trong: {config['output_dir']}")
        print("   - Mỗi bệnh nhân có folder riêng với visualization")
        print("   - Báo cáo tổng: hospital_report.json")
        return 0
    else:
        print(f"⚠️  {len(patients) - successful_count} bệnh nhân thất bại")
        return 1


if __name__ == "__main__":
    sys.exit(main())