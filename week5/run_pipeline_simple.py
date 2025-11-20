"""
Simple Pipeline Runner for Week5 COVID-19 Detection
Local testing version of Kubeflow pipeline
"""

import os
import sys
import time
import json
import shutil
from pathlib import Path
import subprocess
from datetime import datetime


def run_component(component_name: str, input_path: str, output_path: str, timeout: int = 300):
    """Run a pipeline component with timeout"""
    print(f"\n{'='*60}")
    print(f"RUNNING COMPONENT: {component_name.upper()}")
    print(f"{'='*60}")
    print(f"Input: {input_path}")
    print(f"Output: {output_path}")

    start_time = time.time()

    try:
        # Run the component
        result = subprocess.run([
            'python', f'components/{component_name}.py',
            input_path, output_path
        ], timeout=timeout, capture_output=True, text=True)

        elapsed_time = time.time() - start_time

        if result.returncode == 0:
            print(f"[OK] {component_name} completed in {elapsed_time:.2f}s")
            if result.stdout:
                print("Output:", result.stdout)
            return True
        else:
            print(f"[ERROR] {component_name} failed after {elapsed_time:.2f}s")
            print("Error:", result.stderr)
            return False

    except subprocess.TimeoutExpired:
        print(f"[ERROR] {component_name} timed out after {timeout}s")
        return False
    except Exception as e:
        print(f"[ERROR] {component_name} failed: {e}")
        return False


def run_patient_pipeline(patient_id: str, input_base_dir: str, output_base_dir: str):
    """Run complete pipeline for a single patient"""

    print(f"\n{'🏥'*20}")
    print(f"PATIENT PIPELINE: {patient_id}")
    print(f"{'🏥'*20}")

    # Create output directories
    patient_output_dir = Path(output_base_dir) / patient_id
    segmentation_dir = patient_output_dir / "segmentation"
    detection_dir = patient_output_dir / "detection"
    visualization_dir = patient_output_dir / "visualization"

    # Input CT file
    input_ct_file = Path(input_base_dir) / patient_id / "imaging.nii.gz"

    if not input_ct_file.exists():
        print(f"[ERROR] Input file not found: {input_ct_file}")
        return False

    # Step 1: Lung Segmentation
    if not run_component("lung_segment", str(input_ct_file), str(segmentation_dir)):
        return False

    # Step 2: COVID Detection
    if not run_component("covid_detect", str(segmentation_dir), str(detection_dir)):
        return False

    # Step 3: Visualization
    if not run_component("visualize", str(detection_dir), str(visualization_dir)):
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

    print(f"\n[SUCCESS] Patient {patient_id} pipeline completed!")
    return True


def generate_summary_report(output_dir: str, patient_results: dict):
    """Generate summary report of all patients"""

    print(f"\n{'📊'*20}")
    print("GENERATING SUMMARY REPORT")
    print(f"{'📊'*20}")

    summary = {
        "pipeline_name": "COVID-19 Detection Week5",
        "timestamp": datetime.now().isoformat(),
        "total_patients": len(patient_results),
        "successful": sum(1 for result in patient_results.values() if result),
        "failed": sum(1 for result in patient_results.values() if not result),
        "patients": {}
    }

    # Analyze each patient's results
    for patient_id, success in patient_results.items():
        if success:
            patient_dir = Path(output_dir) / patient_id
            results_file = patient_dir / "covid_results.json"

            if results_file.exists():
                try:
                    with open(results_file, 'r') as f:
                        results = json.load(f)

                    diagnosis = results['final_diagnosis']
                    summary["patients"][patient_id] = {
                        "status": "completed",
                        "likelihood": diagnosis['likelihood'],
                        "probability": diagnosis['probability'],
                        "confidence": diagnosis['confidence'],
                        "recommendation": diagnosis['recommendation']
                    }
                except Exception as e:
                    summary["patients"][patient_id] = {
                        "status": "completed",
                        "error": f"Failed to parse results: {e}"
                    }
            else:
                summary["patients"][patient_id] = {
                    "status": "completed",
                    "error": "Results file not found"
                }
        else:
            summary["patients"][patient_id] = {
                "status": "failed"
            }

    # Save summary report
    summary_file = Path(output_dir) / "pipeline_summary.json"
    with open(summary_file, 'w') as f:
        json.dump(summary, f, indent=2)

    print(f"Summary report saved to: {summary_file}")

    # Print summary
    print(f"\n{'='*60}")
    print("PIPELINE SUMMARY")
    print(f"{'='*60}")
    print(f"Total Patients: {summary['total_patients']}")
    print(f"Successful: {summary['successful']}")
    print(f"Failed: {summary['failed']}")
    print(f"Success Rate: {summary['successful']/summary['total_patients']*100:.1f}%")

    print(f"\nPatient Results:")
    for patient_id, result in summary["patients"].items():
        status_emoji = "✅" if result["status"] == "completed" else "❌"
        print(f"  {status_emoji} {patient_id}: {result['status'].upper()}")
        if result["status"] == "completed" and "likelihood" in result:
            print(f"    → {result['likelihood']} ({result['probability']}%)")

    return summary


def main():
    """Main pipeline runner"""
    print("🦠 COVID-19 DETECTION PIPELINE - WEEK5 🦠")
    print("=" * 60)
    print("Clean implementation with lung segmentation and clinical visualization")
    print("=" * 60)

    # Configuration
    input_dir = "data/input"
    output_dir = "data/output"

    # Test patients (same as covid-demo)
    patients = ["lung_001", "lung_002", "lung_003", "lung_004"]

    # Create output directory
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    # Check if components exist
    components_dir = Path("components")
    required_components = ["lung_segment.py", "covid_detect.py", "visualize.py"]

    missing_components = []
    for component in required_components:
        if not (components_dir / component).exists():
            missing_components.append(component)

    if missing_components:
        print(f"[ERROR] Missing components: {missing_components}")
        print("Please ensure all component files are in the 'components' directory.")
        return 1

    print(f"\nProcessing {len(patients)} patients...")
    print(f"Input directory: {input_dir}")
    print(f"Output directory: {output_dir}")

    # Run pipeline for each patient
    patient_results = {}
    total_start_time = time.time()

    for i, patient_id in enumerate(patients, 1):
        print(f"\n{'='*60}")
        print(f"PROCESSING PATIENT {i}/{len(patients)}: {patient_id}")
        print(f"{'='*60}")

        success = run_patient_pipeline(patient_id, input_dir, output_dir)
        patient_results[patient_id] = success

    total_elapsed_time = time.time() - total_start_time

    # Generate summary
    generate_summary_report(output_dir, patient_results)

    print(f"\n{'='*60}")
    print("PIPELINE COMPLETED")
    print(f"{'='*60}")
    print(f"Total time: {total_elapsed_time:.2f}s")
    print(f"Average time per patient: {total_elapsed_time/len(patients):.2f}s")

    # Final status
    successful_count = sum(1 for result in patient_results.values() if result)
    if successful_count == len(patients):
        print("🎉 All patients processed successfully!")
        return 0
    else:
        print(f"⚠️  {len(patients) - successful_count} patients failed to process")
        return 1


if __name__ == "__main__":
    sys.exit(main())