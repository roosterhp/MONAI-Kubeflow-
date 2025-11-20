"""
Create Simple Test Data for Hospital Pipeline
"""

import os
import json
import numpy as np
from pathlib import Path
import SimpleITK as sitk


def create_simple_mock_ct(output_path: str):
    """Create simple mock CT scan"""
    print(f"Creating mock CT: {output_path}")

    # Create simple 3D array (50x100x100 for faster processing)
    ct_array = np.random.randint(-800, 200, (50, 100, 100), dtype=np.int16)

    # Add some lung-like regions (HU -600 to -400)
    ct_array[10:40, 25:75, 25:75] = np.random.randint(-600, -400, (30, 50, 50))

    # Add some GGO (HU -700 to -500)
    ct_array[20:25, 40:60, 40:60] = np.random.randint(-700, -500, (5, 20, 20))

    # Add some consolidation (HU > -300)
    ct_array[25:28, 45:55, 45:55] = np.random.randint(-300, 100, (3, 10, 10))

    # Create SimpleITK image
    ct_image = sitk.GetImageFromArray(ct_array)
    ct_image.SetSpacing((2.0, 2.0, 3.0))

    # Save file
    sitk.WriteImage(ct_image, output_path)
    print(f"  Shape: {ct_array.shape}")
    print(f"  HU range: [{ct_array.min()}, {ct_array.max()}]")


def setup_test_data():
    """Setup test data for hospital pipeline"""
    print("Setting up hospital test data...")

    # Create directories
    input_dir = Path("data/weekly_input")
    input_dir.mkdir(parents=True, exist_ok=True)

    # Create test patients
    patients = ["PATIENT001", "PATIENT002", "PATIENT003"]

    for patient_id in patients:
        patient_dir = input_dir / patient_id
        patient_dir.mkdir(exist_ok=True)

        # Create CT scan
        ct_file = patient_dir / "imaging.nii.gz"
        create_simple_mock_ct(str(ct_file))

        print(f"  [OK] Created: {patient_id}")

    print(f"\nTest data created for {len(patients)} patients")
    print(f"Input directory: {input_dir}")
    print(f"Ready to run: python hospital_pipeline_runner.py")


if __name__ == "__main__":
    setup_test_data()