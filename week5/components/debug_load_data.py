"""
Debug version of load_data_fixed.py - without CT validation
"""
import os
import sys
import json
from pathlib import Path

def find_nifti_files(directory):
    """Find all NIfTI files in directory"""
    nifti_files = set()
    for ext in ['*.nii.gz', '*.nii']:
        nifti_files.update(Path(directory).glob(ext))
        nifti_files.update(Path(directory).rglob(ext))
    return [str(f) for f in sorted(list(nifti_files))]

def discover_patients(input_dir):
    """Auto-discover patients in input folder"""
    input_path = Path(input_dir)

    if not input_path.exists():
        print(f"[ERROR] Input directory does not exist: {input_dir}")
        return []

    print(f"[INFO] Scanning input directory: {input_dir}")
    print(f"[INFO] Directory contents: {list(input_path.iterdir())}")

    patients = []

    # Case 1: Structure like input/PATIENT_ID/imaging.nii.gz
    for patient_dir in input_path.iterdir():
        if patient_dir.is_dir():
            print(f"[INFO] Found patient directory: {patient_dir.name}")
            nifti_files = find_nifti_files(patient_dir)
            print(f"[INFO] NIfTI files in {patient_dir.name}: {nifti_files}")

            for ct_file in nifti_files:
                # Skip validation for now
                patient_info = {
                    "id": patient_dir.name,
                    "name": patient_dir.name,
                    "ct_file": ct_file,
                    "input_dir": str(patient_dir)
                }
                patients.append(patient_info)
                print(f"[INFO] Found patient: {patient_info['id']} -> {ct_file}")
                break

    return patients

def main():
    input_dir = "/mnt/data/hospital_input/weekly_scan"
    working_dir = "/mnt/data/hospital_working"
    metadata_file = "/mnt/data/hospital_working/patients_metadata.json"

    print(f"Input Directory: {input_dir}")
    print(f"Working Directory: {working_dir}")

    # Test if input directory exists and is accessible
    input_path = Path(input_dir)
    print(f"[DEBUG] Input directory exists: {input_path.exists()}")
    print(f"[DEBUG] Input directory is readable: {os.access(input_dir, os.R_OK)}")

    # Discover patients
    patients = discover_patients(input_dir)

    print(f"[INFO] Total patients found: {len(patients)}")

    if not patients:
        print("[ERROR] No patients found!")
        return 1

    # Create working directory
    Path(working_dir).mkdir(parents=True, exist_ok=True)

    # Prepare patient list for workflow
    patient_list_file = Path(working_dir).parent / "patient_list.json"
    patient_ids = [patient['id'] for patient in patients]
    with open(patient_list_file, 'w') as f:
        json.dump(patient_ids, f)

    # Save total patients count
    total_patients_file = Path(working_dir).parent / "total_patients.txt"
    with open(total_patients_file, 'w') as f:
        f.write(str(len(patients)))

    # Save metadata
    metadata = {
        "scan_time": "weekly_scan",
        "total_patients": len(patients),
        "input_directory": input_dir,
        "working_directory": working_dir,
        "patients": patients
    }

    with open(metadata_file, 'w') as f:
        json.dump(metadata, f, indent=2)

    print(f"[SUCCESS] Found {len(patients)} patients")
    return 0

if __name__ == "__main__":
    sys.exit(main())