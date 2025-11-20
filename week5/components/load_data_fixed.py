"""
Hospital Data Loader Component - Fixed Unicode
Automatically scan input folder and find all patients with CT data
"""

import os
import sys
import json
from pathlib import Path
from typing import List, Dict, Any
import shutil


def find_nifti_files(directory: Path) -> List[str]:
    """Find all NIfTI files in directory (avoid duplicates)"""
    nifti_files = set()  # Use set to avoid duplicates
    for ext in ['*.nii.gz', '*.nii']:  # Prioritize .nii.gz
        nifti_files.update(directory.glob(ext))
        nifti_files.update(directory.rglob(ext))
    return [str(f) for f in sorted(list(nifti_files))]


def validate_ct_file(file_path: str) -> bool:
    """Check if file is a valid CT scan"""
    try:
        import SimpleITK as sitk
        sitk.ReadImage(file_path)
        return True
    except:
        return False


def discover_patients(input_dir: str) -> List[Dict[str, Any]]:
    """
    Auto-discover patients in input folder

    Args:
        input_dir: Path to weekly input folder

    Returns:
        List of patient info: [{"id": "patient_name", "ct_file": "path/to/file"}]
    """
    input_path = Path(input_dir)

    if not input_path.exists():
        print(f"[ERROR] Input directory does not exist: {input_dir}")
        return []

    print(f"[INFO] Scanning input directory: {input_dir}")

    patients = []

    # Case 1: Structure like input/PATIENT_ID/imaging.nii.gz
    for patient_dir in input_path.iterdir():
        if patient_dir.is_dir():
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
                    print(f"[INFO] Found patient: {patient_info['id']} -> {ct_file}")
                    break

    # Case 2: Structure like input/*.nii.gz (all files in same directory)
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
                print(f"[INFO] Found patient: {patient_info['id']} -> {ct_file}")

    print(f"[INFO] Total patients found: {len(patients)}")
    return patients


def prepare_patient_data(patient_info: Dict[str, Any], working_dir: str) -> str:
    """
    Prepare data for one patient

    Args:
        patient_info: Patient information
        working_dir: Working directory

    Returns:
        Path to prepared CT file
    """
    patient_id = patient_info["id"]
    patient_working_dir = Path(working_dir) / patient_id
    patient_working_dir.mkdir(parents=True, exist_ok=True)

    # Copy CT file to working directory
    ct_source = Path(patient_info["ct_file"])
    ct_dest = patient_working_dir / "imaging.nii.gz"

    if ct_source != ct_dest:
        shutil.copy2(ct_source, ct_dest)
        print(f"[INFO] Copied {ct_source} -> {ct_dest}")

    return str(ct_dest)


def load_hospital_data(input_dir: str, working_dir: str, metadata_file: str):
    """
    Main function: Load and prepare hospital data

    Args:
        input_dir: Input folder containing weekly patient data
        working_dir: Working directory for processing
        metadata_file: JSON file to save patient information

    Returns:
        0 success, 1 failure
    """
    print(f"\n{'='*70}")
    print("HOSPITAL DATA LOADER")
    print(f"{'='*70}")
    print(f"Input Directory: {input_dir}")
    print(f"Working Directory: {working_dir}")
    print(f"Metadata File: {metadata_file}")

    try:
        # Create working directory
        Path(working_dir).mkdir(parents=True, exist_ok=True)

        # Auto-discover patients
        print("\n[Step 1/3] Discovering patients in input folder...")
        patients = discover_patients(input_dir)

        if not patients:
            print("[ERROR] No patients found in input directory!")
            print("Please check folder structure:")
            print("  - input/PATIENT_ID/imaging.nii.gz")
            print("  - or input/*.nii.gz")
            return 1

        # Prepare data for each patient
        print(f"\n[Step 2/3] Preparing data for {len(patients)} patients...")
        prepared_patients = []

        for i, patient_info in enumerate(patients, 1):
            print(f"\n  [{i}/{len(patients)}] Processing patient: {patient_info['id']}")

            ct_file = prepare_patient_data(patient_info, working_dir)

            prepared_patient = {
                **patient_info,
                "prepared_ct_file": ct_file,
                "working_dir": str(Path(working_dir) / patient_info['id'])
            }
            prepared_patients.append(prepared_patient)

        # Save metadata
        print(f"\n[Step 3/3] Saving patient metadata...")
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
            json.dump(metadata, f, indent=2)

        # Also save total patients count to text file for workflow
        total_patients_file = Path(working_dir).parent / "total_patients.txt"
        with open(total_patients_file, 'w') as f:
            f.write(str(len(prepared_patients)))

        # Save patient list as simple array for workflow withParam
        patient_list_file = Path(working_dir).parent / "patient_list.json"
        patient_ids = [patient['id'] for patient in prepared_patients]
        with open(patient_list_file, 'w') as f:
            json.dump(patient_ids, f)

        print(f"[OK] Saved metadata for {len(prepared_patients)} patients to: {metadata_file}")

        # Print summary
        print(f"\n{'='*50}")
        print("HOSPITAL DATA SUMMARY")
        print(f"{'='*50}")
        print(f"Total patients: {len(prepared_patients)}")
        print(f"Input directory: {input_dir}")
        print(f"Working directory: {working_dir}")

        for patient in prepared_patients:
            print(f"  * {patient['id']}: {patient['prepared_ct_file']}")

        print(f"[OK] Hospital data loading completed!")
        return 0

    except Exception as e:
        print(f"[ERROR] Hospital data loading failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage: python load_data_fixed.py <input_dir> <working_dir> <metadata_file>")
        print("\nExample:")
        print("  python load_data_fixed.py data/weekly_input data/working data/patients_metadata.json")
        print("\nStructure Examples:")
        print("  data/weekly_input/PATIENT001/imaging.nii.gz")
        print("  data/weekly_input/PATIENT001/CT_001.nii.gz")
        print("  data/weekly_input/*.nii.gz")
        sys.exit(1)

    input_dir = sys.argv[1]
    working_dir = sys.argv[2]
    metadata_file = sys.argv[3]

    sys.exit(load_hospital_data(input_dir, working_dir, metadata_file))