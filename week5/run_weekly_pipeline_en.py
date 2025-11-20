#!/usr/bin/env python3
"""
Weekly Pipeline Runner for Week5 COVID-19 Detection
Process data from weekly_input and output to hospital_output
"""

import os
import sys
import time
import json
import shutil
from pathlib import Path
import subprocess
from datetime import datetime


def run_component_with_timeout(component_name: str, args: list, timeout: int = 600):
    """Run component with timeout and error handling"""
    print(f"\n{'='*60}")
    print(f"RUNNING COMPONENT: {component_name.upper()}")
    print(f"{'='*60}")
    print(f"Command: python {args}")

    start_time = time.time()

    try:
        result = subprocess.run(
            ['python'] + args,
            timeout=timeout,
            capture_output=True,
            text=True,
            cwd='E:/monai-kubeflow-demo/week5'  # Ensure running from week5 directory
        )

        elapsed_time = time.time() - start_time

        if result.returncode == 0:
            print(f"[OK] {component_name} completed in {elapsed_time:.1f}s")
            if result.stdout:
                print("Output:", result.stdout[-500:])  # Show last 500 characters
            return True
        else:
            print(f"[ERROR] {component_name} failed after {elapsed_time:.1f}s")
            print("Error:", result.stderr)
            return False

    except subprocess.TimeoutExpired:
        print(f"[ERROR] {component_name} timeout after {timeout}s")
        return False
    except Exception as e:
        print(f"[ERROR] {component_name} failed: {e}")
        return False


def process_single_patient(patient_info: dict, base_output_dir: str) -> bool:
    """
    Process 1 patient: Lung Seg -> COVID Detect -> Visualization
    """
    patient_id = patient_info["id"]
    ct_file = patient_info["prepared_ct_file"]
    working_dir = patient_info["working_dir"]

    print(f"\n{'='*60}")
    print(f"PROCESSING PATIENT: {patient_id}")
    print(f"{'='*60}")
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

    print(f"\n[SUCCESS] Patient {patient_id} processing completed!")
    return True


def generate_hospital_report(output_dir: str, metadata: dict, patient_results: dict):
    """Generate hospital summary report"""
    print(f"\n{'='*60}")
    print("GENERATING HOSPITAL REPORT")
    print(f"{'='*60}")

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
                        "error": f"Error reading results: {e}"
                    }
            else:
                report["patients"][patient_id] = {
                    "status": "completed",
                    "error": "Results file not found"
                }
        else:
            report["patients"][patient_id] = {
                "status": "failed",
                "error": "Processing failed"
            }

    # Save hospital report
    report_file = Path(output_dir) / "hospital_report.json"
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print(f"Hospital report saved to: {report_file}")

    # Print summary
    print(f"\n{'='*60}")
    print("HOSPITAL SUMMARY REPORT")
    print(f"{'='*60}")
    print(f"Scan date: {report['hospital_report']['scan_date']}")
    print(f"Total patients: {report['hospital_report']['total_patients']}")
    print(f"Successful: {report['hospital_report']['successful']}")
    print(f"Failed: {report['hospital_report']['failed']}")
    print(f"Success rate: {report['hospital_report']['success_rate']}")

    print(f"\nCOVID-19 RISK DISTRIBUTION:")
    print(f"  [HIGH] High risk: {report['summary']['high_risk']} patients")
    print(f"  [MODERATE] Moderate: {report['summary']['moderate_risk']} patients")
    print(f"  [LOW] Low risk: {report['summary']['low_risk']} patients")
    print(f"  [VERY_LOW] Very low: {report['summary']['very_low_risk']} patients")

    # Alert for high-risk patients
    if report['summary']['high_risk'] > 0:
        print(f"\n[WARNING] {report['summary']['high_risk']} high-risk patients detected!")
        print("   Recommendation: Immediate radiologist review required")

    return report


def main():
    """Main weekly pipeline runner"""
    print("COVID-19 DETECTION SYSTEM - WEEKLY SCAN")
    print("=" * 70)
    print("Automatic processing of weekly CT scan data")
    print("=" * 70)

    # Configuration
    config = {
        "input_weekly_dir": "data/weekly_input",      # Folder containing weekly data
        "working_dir": "data/working",                # Working directory
        "metadata_file": "data/working/patients_metadata.json",
        "output_dir": "data/hospital_output"          # Final results folder
    }

    # Create output directory
    Path(config["output_dir"]).mkdir(parents=True, exist_ok=True)

    print(f"\nConfiguration:")
    print(f"  Weekly input: {config['input_weekly_dir']}")
    print(f"  Working: {config['working_dir']}")
    print(f"  Output: {config['output_dir']}")

    # Step 1: Load hospital data
    print(f"\n{'='*60}")
    print("STEP 1: LOADING HOSPITAL DATA")
    print(f"{'='*60}")

    if not run_component_with_timeout(
        "load_data",
        ["simple_data_loader.py",
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
        print(f"[ERROR] Could not read metadata: {e}")
        return 1

    # Step 2: Process all patients
    print(f"\n{'='*60}")
    print("STEP 2: PROCESSING COVID-19 FOR EACH PATIENT")
    print(f"{'='*60}")

    patient_results = {}
    total_start_time = time.time()

    for i, patient_info in enumerate(patients, 1):
        print(f"\n{'='*60}")
        print(f"PATIENT {i}/{len(patients)}: {patient_info['id']}")
        print(f"{'='*60}")

        success = process_single_patient(patient_info, config["output_dir"])
        patient_results[patient_info['id']] = success

    total_elapsed_time = time.time() - total_start_time

    # Step 3: Generate hospital report
    print(f"\n{'='*60}")
    print("STEP 3: GENERATING SUMMARY REPORT")
    print(f"{'='*60}")

    hospital_report = generate_hospital_report(
        config["output_dir"],
        metadata,
        patient_results
    )

    # Final status
    print(f"\n{'='*60}")
    print("PIPELINE COMPLETED")
    print(f"{'='*60}")
    print(f"Total time: {total_elapsed_time:.1f}s")
    print(f"Average per patient: {total_elapsed_time/len(patients):.1f}s")

    successful_count = sum(1 for result in patient_results.values() if result)
    if successful_count == len(patients):
        print("[SUCCESS] All patients processed successfully!")
        print(f"\n[INFO] Results saved in: {config['output_dir']}")
        print("   - Each patient has separate folder with visualization")
        print("   - Summary report: hospital_report.json")
        return 0
    else:
        print(f"[WARNING] {len(patients) - successful_count} patients failed to process")
        return 1


if __name__ == "__main__":
    sys.exit(main())