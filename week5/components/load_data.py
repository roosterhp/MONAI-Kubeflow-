"""
Hospital Data Loader Component
Tự động quét folder input và tìm tất cả bệnh nhân có dữ liệu CT
"""

import os
import sys
import json
from pathlib import Path
from typing import List, Dict, Any
import shutil


def find_nifti_files(directory: Path) -> List[str]:
    """Tìm tất cả file NIfTI trong thư mục"""
    nifti_files = []
    for ext in ['*.nii', '*.nii.gz']:
        nifti_files.extend(directory.glob(ext))
        nifti_files.extend(directory.rglob(ext))
    return [str(f) for f in nifti_files]


def validate_ct_file(file_path: str) -> bool:
    """Kiểm tra xem file có phải là CT scan hợp lệ không"""
    try:
        import SimpleITK as sitk
        # Thử đọc file để kiểm tra tính hợp lệ
        sitk.ReadImage(file_path)
        return True
    except:
        return False


def discover_patients(input_dir: str) -> List[Dict[str, Any]]:
    """
    Tự động phát hiện bệnh nhân trong input folder

    Args:
        input_dir: Đường dẫn đến folder input chứa dữ liệu tuần

    Returns:
        List of patient info: [{"id": "patient_name", "ct_file": "path/to/file"}]
    """
    input_path = Path(input_dir)

    if not input_path.exists():
        print(f"[ERROR] Input directory does not exist: {input_dir}")
        return []

    print(f"[INFO] Scanning input directory: {input_dir}")

    patients = []

    # Case 1: Structure dạng input/PATIENT_ID/imaging.nii.gz
    for patient_dir in input_path.iterdir():
        if patient_dir.is_dir():
            # Tìm file CT trong thư mục bệnh nhân
            nifti_files = find_nifti_files(patient_dir)

            for ct_file in nifti_files:
                if validate_ct_file(ct_file):
                    patient_info = {
                        "id": patient_dir.name,
                        "name": patient_dir.name,
                        "ct_file": ct_file,
                        "input_dir": str(patient_dir)
                    }
                    patients.append(patient_info)
                    print(f"[INFO] Tìm thấy bệnh nhân: {patient_info['id']} -> {ct_file}")
                    break  # Chỉ lấy 1 file CT đầu tiên cho mỗi bệnh nhân

    # Case 2: Structure dạng input/*.nii.gz (tất cả file trong cùng thư mục)
    if not patients:
        nifti_files = find_nifti_files(input_path)

        for ct_file in nifti_files:
            if validate_ct_file(ct_file):
                patient_name = Path(ct_file).stem
                patient_info = {
                    "id": patient_name,
                    "name": patient_name,
                    "ct_file": ct_file,
                    "input_dir": input_dir
                }
                patients.append(patient_info)
                print(f"[INFO] Tìm thấy bệnh nhân: {patient_info['id']} -> {ct_file}")

    print(f"[INFO] Tổng số bệnh nhân tìm thấy: {len(patients)}")
    return patients


def prepare_patient_data(patient_info: Dict[str, Any], working_dir: str) -> str:
    """
    Chuẩn bị dữ liệu cho 1 bệnh nhân

    Args:
        patient_info: Thông tin bệnh nhân
        working_dir: Thư mục làm việc

    Returns:
        Đường dẫn đến file CT đã chuẩn bị
    """
    patient_id = patient_info["id"]
    patient_working_dir = Path(working_dir) / patient_id
    patient_working_dir.mkdir(parents=True, exist_ok=True)

    # Copy CT file đến working directory
    ct_source = Path(patient_info["ct_file"])
    ct_dest = patient_working_dir / "imaging.nii.gz"

    if ct_source != ct_dest:
        shutil.copy2(ct_source, ct_dest)
        print(f"[INFO] Copy {ct_source} -> {ct_dest}")

    return str(ct_dest)


def load_hospital_data(input_dir: str, working_dir: str, metadata_file: str):
    """
    Main function: Load và chuẩn bị dữ liệu bệnh viện

    Args:
        input_dir: Folder input chứa dữ liệu tuần của bệnh nhân
        working_dir: Thư mục làm việc để xử lý
        metadata_file: File JSON để lưu thông tin bệnh nhân

    Returns:
        0 thành công, 1 thất bại
    """
    print(f"\n{'='*70}")
    print("HOSPITAL DATA LOADER")
    print(f"{'='*70}")
    print(f"Input Directory: {input_dir}")
    print(f"Working Directory: {working_dir}")
    print(f"Metadata File: {metadata_file}")

    try:
        # Tạo working directory
        Path(working_dir).mkdir(parents=True, exist_ok=True)

        # Tự động phát hiện bệnh nhân
        print("\n[Step 1/3] Phát hiện bệnh nhân trong input folder...")
        patients = discover_patients(input_dir)

        if not patients:
            print("[ERROR] Không tìm thấy bệnh nhân nào trong input directory!")
            print("Hãy kiểm tra lại cấu trúc thư mục:")
            print("  - input/PATIENT_ID/imaging.nii.gz")
            print("  - hoặc input/*.nii.gz")
            return 1

        # Chuẩn bị dữ liệu cho từng bệnh nhân
        print(f"\n[Step 2/3] Chuẩn bị dữ liệu cho {len(patients)} bệnh nhân...")
        prepared_patients = []

        for i, patient_info in enumerate(patients, 1):
            print(f"\n  [{i}/{len(patients)}] Xử lý bệnh nhân: {patient_info['id']}")

            ct_file = prepare_patient_data(patient_info, working_dir)

            prepared_patient = {
                **patient_info,
                "prepared_ct_file": ct_file,
                "working_dir": str(Path(working_dir) / patient_info['id'])
            }
            prepared_patients.append(prepared_patient)

        # Lưu metadata
        print(f"\n[Step 3/3] Lưu thông tin bệnh nhân...")
        metadata = {
            "scan_time": str(Path(input_dir).name) if Path(input_dir).name != "input" else "weekly_scan",
            "total_patients": len(prepared_patients),
            "input_directory": input_dir,
            "working_directory": working_dir,
            "patients": prepared_patients,
            "pipeline_config": {
                "lung_segmentation": True,
                "covid_detection": True,
                "visualization": True,
                "ensemble_method": "rule_based_monai"
            }
        }

        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)

        print(f"[OK] Đã lưu thông tin {len(prepared_patients)} bệnh nhân vào: {metadata_file}")

        # In summary
        print(f"\n{'='*50}")
        print("TÓM TẮT DỮ LIỆU BỆNH VIỆN")
        print(f"{'='*50}")
        print(f"Tổng bệnh nhân: {len(prepared_patients)}")
        print(f"Input directory: {input_dir}")
        print(f"Working directory: {working_dir}")

        for patient in prepared_patients:
            print(f"  • {patient['id']}: {patient['prepared_ct_file']}")

        print(f"[OK] Hospital data loading completed!")
        return 0

    except Exception as e:
        print(f"[ERROR] Hospital data loading failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage: python load_data.py <input_dir> <working_dir> <metadata_file>")
        print("\nVí dụ:")
        print("  python load_data.py data/weekly_input data/working data/patients_metadata.json")
        print("\nStructure Examples:")
        print("  data/weekly_input/PATIENT001/imaging.nii.gz")
        print("  data/weekly_input/PATIENT001/CT_001.nii.gz")
        print("  data/weekly_input/*.nii.gz")
        sys.exit(1)

    input_dir = sys.argv[1]
    working_dir = sys.argv[2]
    metadata_file = sys.argv[3]

    sys.exit(load_hospital_data(input_dir, working_dir, metadata_file))