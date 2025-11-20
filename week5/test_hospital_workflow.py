"""
Test Hospital Workflow
Simple test for hospital COVID-19 detection workflow
"""

import os
import sys
import json
import time
import subprocess
from pathlib import Path


def run_component_simple(component_name: str, args: list, timeout: int = 300):
    """Run component with simple output"""
    print(f"\n{'='*60}")
    print(f"RUNNING: {component_name.upper()}")
    print(f"{'='*60}")
    print(f"Command: python {' '.join(args)}")

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
            print(f"[OK] {component_name} completed in {elapsed_time:.1f}s")
            return True
        else:
            print(f"[ERROR] {component_name} failed after {elapsed_time:.1f}s")
            print("Error output:", result.stderr)
            return False

    except subprocess.TimeoutExpired:
        print(f"[ERROR] {component_name} timed out after {timeout}s")
        return False
    except Exception as e:
        print(f"[ERROR] {component_name} failed: {e}")
        return False


def test_hospital_workflow():
    """Test complete hospital workflow"""
    print("HOSPITAL COVID-19 DETECTION WORKFLOW TEST")
    print("="*60)

    # Configuration
    config = {
        "input_weekly_dir": "data/weekly_input",
        "working_dir": "data/hospital_working",
        "metadata_file": "data/hospital_working/patients_metadata.json",
        "output_dir": "data/hospital_output"
    }

    # Create output directory
    Path(config["output_dir"]).mkdir(parents=True, exist_ok=True)

    print(f"Configuration:")
    print(f"  Input: {config['input_weekly_dir']}")
    print(f"  Working: {config['working_dir']}")
    print(f"  Output: {config['output_dir']}")

    # Step 1: Load hospital data
    print(f"\n{'='*60}")
    print("STEP 1: LOAD HOSPITAL DATA")
    print(f"{'='*60}")

    if not run_component_simple(
        "load_data",
        ["components/load_data_fixed.py",
         config["input_weekly_dir"],
         config["working_dir"],
         config["metadata_file"]]
    ):
        print("[ERROR] Failed to load hospital data!")
        return 1

    # Load patient metadata
    try:
        with open(config["metadata_file"], 'r') as f:
            metadata = json.load(f)

        patients = metadata["patients"]
        print(f"[INFO] Found {len(patients)} patients to process")
    except Exception as e:
        print(f"[ERROR] Cannot read metadata: {e}")
        return 1

    # Process patients one by one (simplified)
    print(f"\n{'='*60}")
    print("STEP 2: PROCESS PATIENTS")
    print(f"{'='*60}")

    successful_patients = 0
    total_patients = len(patients)

    for i, patient_info in enumerate(patients[:2], 1):  # Test only first 2 patients
        patient_id = patient_info["id"]
        print(f"\n{'='*40}")
        print(f"PATIENT {i}/{total_patients}: {patient_id}")
        print(f"{'='*40}")

        # Create patient output directory
        patient_output_dir = Path(config["output_dir"]) / patient_id
        patient_output_dir.mkdir(parents=True, exist_ok=True)

        # Step 1: Lung segmentation
        segmentation_dir = patient_output_dir / "segmentation"
        if not run_component_simple(
            "lung_segmentation",
            ["components/lung_segment.py",
             patient_info["prepared_ct_file"],
             str(segmentation_dir)]
        ):
            print(f"[SKIP] Patient {patient_id} - lung segmentation failed")
            continue

        # Step 2: COVID detection
        detection_dir = patient_output_dir / "detection"
        if not run_component_simple(
            "covid_detection",
            ["components/covid_detect.py",
             str(segmentation_dir),
             str(detection_dir)]
        ):
            print(f"[SKIP] Patient {patient_id} - COVID detection failed")
            continue

        # Step 3: Visualization
        visualization_dir = patient_output_dir / "visualization"
        if not run_component_simple(
            "visualization",
            ["components/visualize.py",
             str(detection_dir),
             str(visualization_dir)]
        ):
            print(f"[SKIP] Patient {patient_id} - visualization failed")
            continue

        # Copy required files for visualization and main patient directory
        results_file = detection_dir / "covid_results.json"
        viz_file = visualization_dir / "covid_visualization.png"

        # Copy necessary files to detection folder for visualization
        segmentation_files = [
            "ct_array.npy",
            "lung_mask.nii.gz",
            "spacing.npy"
        ]

        for file_name in segmentation_files:
            src_file = Path(segmentation_dir) / file_name
            dest_file = Path(detection_dir) / file_name
            if src_file.exists():
                import shutil
                shutil.copy2(src_file, dest_file)

        if results_file.exists():
            import shutil
            shutil.copy2(results_file, patient_output_dir)
            print(f"[OK] Results saved for {patient_id}")

        if viz_file.exists():
            shutil.copy2(viz_file, patient_output_dir)
            print(f"[OK] Visualization saved for {patient_id}")
            successful_patients += 1

    # Generate summary
    print(f"\n{'='*60}")
    print("WORKFLOW SUMMARY")
    print(f"{'='*60}")
    print(f"Total patients: {total_patients}")
    print(f"Successful: {successful_patients}")
    print(f"Success rate: {successful_patients/total_patients*100:.1f}%")

    # Check output structure
    print(f"\nOutput structure:")
    output_path = Path(config["output_dir"])
    for patient_dir in output_path.iterdir():
        if patient_dir.is_dir():
            files = list(patient_dir.glob("*"))
            print(f"  {patient_dir.name}/: {len(files)} files")
            for file in files:
                print(f"    - {file.name}")

    if successful_patients > 0:
        print(f"\n[SUCCESS] Hospital workflow test completed!")
        print(f"Results saved in: {config['output_dir']}")
        print(f"Each patient folder contains:")
        print(f"  - covid_visualization.png (2x3 clinical grid)")
        print(f"  - covid_results.json (detection results)")
        return 0
    else:
        print(f"\n[ERROR] No patients processed successfully")
        return 1


if __name__ == "__main__":
    sys.exit(test_hospital_workflow())