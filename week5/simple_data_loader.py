#!/usr/bin/env python3
"""
Simple Data Loader for Weekly Input
Loads CT files from weekly_input directory and creates patient metadata
"""

import os
import sys
import json
import shutil
from pathlib import Path
from typing import List, Dict, Any


def find_nifti_files(directory: Path) -> List[str]:
    """Find all NIfTI files in directory"""
    nifti_files = []
    for ext in ['*.nii', '*.nii.gz']:
        nifti_files.extend(directory.glob(ext))
        nifti_files.extend(directory.rglob(ext))
    return [str(f) for f in nifti_files]


def validate_ct_file(file_path: str) -> bool:
    """Check if file is a valid CT scan"""
    try:
        import SimpleITK as sitk
        # Try to read file to validate
        sitk.ReadImage(file_path)
        return True
    except:
        return False


def load_weekly_data(input_dir: str, working_dir: str, metadata_file: str):
    """
    Load weekly CT data and prepare metadata

    Args:
        input_dir: Directory with weekly CT files
        working_dir: Working directory for processing
        metadata_file: Output metadata file path
    """
    print(f"\n{'='*60}")
    print("WEEKLY DATA LOADER")
    print(f"{'='*60}")
    print(f"Input Directory: {input_dir}")
    print(f"Working Directory: {working_dir}")
    print(f"Metadata File: {metadata_file}")

    try:
        # Create working directory
        Path(working_dir).mkdir(parents=True, exist_ok=True)

        input_path = Path(input_dir)
        if not input_path.exists():
            print(f"[ERROR] Input directory does not exist: {input_dir}")
            return 1

        print(f"[INFO] Scanning input directory: {input_dir}")

        # Find all NIfTI files
        nifti_files = find_nifti_files(input_path)
        print(f"[INFO] Found {len(nifti_files)} NIfTI files")

        patients = []
        for ct_file in nifti_files:
            if validate_ct_file(ct_file):
                # Use filename as patient ID
                patient_name = Path(ct_file).stem
                patient_id = patient_name

                patient_info = {
                    "id": patient_id,
                    "name": patient_name,
                    "ct_file": ct_file,
                    "input_dir": str(input_path)
                }
                patients.append(patient_info)
                print(f"[INFO] Found patient: {patient_id} -> {ct_file}")

        if not patients:
            print("[ERROR] No valid CT files found!")
            return 1

        # Prepare working directories for each patient
        print(f"\n[INFO] Preparing working directories for {len(patients)} patients...")
        prepared_patients = []

        for i, patient_info in enumerate(patients, 1):
            print(f"  [{i}/{len(patients)}] Preparing: {patient_info['id']}")

            patient_id = patient_info["id"]
            patient_working_dir = Path(working_dir) / patient_id
            patient_working_dir.mkdir(parents=True, exist_ok=True)

            # Copy CT file to working directory
            ct_source = Path(patient_info["ct_file"])
            ct_dest = patient_working_dir / "imaging.nii.gz"

            if ct_source != ct_dest:
                shutil.copy2(ct_source, ct_dest)
                print(f"    Copied {ct_source} -> {ct_dest}")

            prepared_patient = {
                **patient_info,
                "prepared_ct_file": str(ct_dest),
                "working_dir": str(patient_working_dir)
            }
            prepared_patients.append(prepared_patient)

        # Save metadata
        print(f"\n[INFO] Saving patient metadata...")
        metadata = {
            "scan_time": "weekly_scan",
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

        print(f"[OK] Saved {len(prepared_patients)} patients to: {metadata_file}")

        # Print summary
        print(f"\n{'='*50}")
        print("WEEKLY DATA SUMMARY")
        print(f"{'='*50}")
        print(f"Total patients: {len(prepared_patients)}")
        print(f"Input directory: {input_dir}")
        print(f"Working directory: {working_dir}")

        for patient in prepared_patients:
            print(f"  - {patient['id']}: {patient['prepared_ct_file']}")

        print("[OK] Weekly data loading completed!")
        return 0

    except Exception as e:
        print(f"[ERROR] Weekly data loading failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage: python simple_data_loader.py <input_dir> <working_dir> <metadata_file>")
        print("\nExample:")
        print("  python simple_data_loader.py data/weekly_input data/working data/patients_metadata.json")
        sys.exit(1)

    input_dir = sys.argv[1]
    working_dir = sys.argv[2]
    metadata_file = sys.argv[3]

    sys.exit(load_weekly_data(input_dir, working_dir, metadata_file))