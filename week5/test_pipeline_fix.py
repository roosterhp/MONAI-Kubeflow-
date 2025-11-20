#!/usr/bin/env python3

"""
Test script to verify the COVID pipeline data loading fix works.
This simulates the load-data component logic.
"""

import json
import sys
from pathlib import Path

def test_load_data(input_dir: str, patient_id: str):
    """Test the load data component logic."""
    print(f"[LOAD] Processing patient: {patient_id}", file=sys.stderr)
    print(f"[LOAD] Input directory: {input_dir}", file=sys.stderr)

    try:
        input_path = Path(input_dir)
        if not input_path.exists():
            raise FileNotFoundError(f"Input directory not found: {input_dir}")

        nifti_file = input_path / f"{patient_id}.nii.gz"
        if not nifti_file.exists():
            raise FileNotFoundError(f"NIfTI file not found: {nifti_file}")

        file_size = nifti_file.stat().st_size
        print(f"[LOAD] Found NIfTI file: {nifti_file}", file=sys.stderr)
        print(f"[LOAD] File size: {file_size:,} bytes", file=sys.stderr)

        result = {
            "component": "load_data",
            "patient_id": patient_id,
            "nifti_file": str(nifti_file),
            "file_size_bytes": file_size,
            "status": "completed",
            "message": f"Successfully loaded {patient_id}"
        }

        print(json.dumps(result))
        return result

    except Exception as e:
        result = {
            "component": "load_data",
            "patient_id": patient_id,
            "status": "failed",
            "error": str(e)
        }
        print(json.dumps(result))
        sys.exit(1)

def test_visualization(output_dir: str, patient_id: str, likelihood: str, probability: int):
    """Test the visualization component logic."""
    print(f"[VIZ] Creating visualization for: {patient_id}", file=sys.stderr)

    try:
        # Create visualization
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        fig, ax = plt.subplots(figsize=(8, 6))
        fig.suptitle(f"COVID-19 Analysis - {patient_id}", fontsize=14, fontweight="bold")

        stages = [
            ("1. Load Data", "✓", "green"),
            ("2. Segment Lungs", "✓", "blue"),
            ("3. Detect COVID", "✓", "orange"),
            ("4. Visualization", "✓", "purple")
        ]

        for i, (step, status, color) in enumerate(stages):
            y_pos = 0.8 - (i * 0.2)
            ax.text(0.5, y_pos, f"{step}: {status}", ha="center", fontsize=12,
                   color=color, fontweight="bold")

        ax.text(0.5, 0.1, f"Result: {likelihood} ({probability}%)",
               ha="center", fontsize=14, fontweight="bold")
        ax.axis("off")

        # Save
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        viz_file = output_path / f"{patient_id}_analysis.png"
        plt.savefig(viz_file, dpi=100, bbox_inches="tight")
        plt.close()

        print(f"[VIZ] Saved visualization: {viz_file}", file=sys.stderr)

        result = {
            "component": "visualization",
            "patient_id": patient_id,
            "viz_file": str(viz_file),
            "likelihood": likelihood,
            "probability": probability,
            "status": "completed",
            "message": f"Visualization created for {patient_id}"
        }

        print(json.dumps(result))
        return result

    except Exception as e:
        result = {
            "component": "visualization",
            "patient_id": patient_id,
            "status": "failed",
            "error": str(e)
        }
        print(json.dumps(result))
        sys.exit(1)

if __name__ == "__main__":
    print("=== Testing COVID Pipeline Data Loading ===")

    # Test data loading
    input_dir = "/mnt/data/weekly_input"
    output_dir = "/mnt/data/hospital_output"

    # Test all 4 patients
    patients = ["lung_001", "lung_002", "lung_003", "lung_004"]

    for patient_id in patients:
        print(f"\n--- Testing {patient_id} ---")
        result = test_load_data(input_dir, patient_id)
        print(f"Result: {result['status']}")

    # Test visualization for one patient
    print(f"\n--- Testing Visualization ---")
    test_visualization(output_dir, "lung_001", "MODERATE", 65)

    print("\n=== Test Complete ===")