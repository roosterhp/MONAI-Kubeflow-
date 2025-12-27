"""
Simple Pipeline Runner for COVID-19 Detection
Runs: load_data -> lung_segment -> covid_detect_enhanced -> visualize
"""

import sys
import subprocess
import time
from pathlib import Path

PATIENTS = ["lung_001", "lung_002", "lung_003", "lung_004"]

def run_component(component_name, patient_id):
    """Run a single component"""
    print(f"\n{'='*60}")
    print(f"Running {component_name} for {patient_id}")
    print(f"{'='*60}")

    script_path = Path(f"components/{component_name}.py")
    if not script_path.exists():
        print(f"[ERROR] Script not found: {script_path}")
        return False

    try:
        result = subprocess.run([
            sys.executable, str(script_path), patient_id
        ], capture_output=True, text=True, timeout=300)

        if result.returncode == 0:
            print(f"[OK] {component_name} completed successfully")
            if result.stdout:
                print(f"Output: {result.stdout[-200:]}")  # Last 200 chars
            return True
        else:
            print(f"[ERROR] {component_name} failed")
            print(f"Error: {result.stderr}")
            return False
    except subprocess.TimeoutExpired:
        print(f"[ERROR] {component_name} timed out")
        return False
    except Exception as e:
        print(f"[ERROR] {component_name} failed: {e}")
        return False

def run_pipeline():
    """Run the complete pipeline"""
    print("COVID-19 Detection Pipeline - Simple Runner")
    print("=" * 70)

    components = [
        ("load_data", "load_data"),
        ("lung_segment", "lung_segment"),
        ("covid_detect_enhanced", "enhanced COVID detection"),
        ("visualize", "visualization")
    ]

    results = {}

    start_time = time.time()

    for patient_id in PATIENTS:
        print(f"\n\n{'#'*70}")
        print(f"# Processing Patient: {patient_id}")
        print(f"{'#'*70}")

        patient_results = []

        for component_name, description in components:
            success = run_component(component_name, patient_id)
            patient_results.append({
                'component': component_name,
                'success': success
            })

            if not success:
                print(f"[STOP] Pipeline failed at {component_name} for {patient_id}")
                break

        results[patient_id] = patient_results

    total_time = time.time() - start_time

    # Summary
    print(f"\n\n{'#'*70}")
    print(f"# PIPELINE SUMMARY")
    print(f"{'#'*70}")

    success_count = 0
    for patient_id, patient_results in results.items():
        print(f"\nPatient {patient_id}:")
        all_success = all(r['success'] for r in patient_results)
        status = "SUCCESS" if all_success else "FAILED"
        print(f"  Status: {status}")

        for result in patient_results:
            symbol = "OK" if result['success'] else "FAIL"
            print(f"  {symbol} {result['component']}")

        if all_success:
            success_count += 1

    print(f"\nOverall: {success_count}/{len(PATIENTS)} patients processed successfully")
    print(f"Total time: {total_time:.2f} seconds")
    print(f"Average time per patient: {total_time/len(PATIENTS):.2f} seconds")

    return success_count == len(PATIENTS)

if __name__ == "__main__":
    success = run_pipeline()
    sys.exit(0 if success else 1)