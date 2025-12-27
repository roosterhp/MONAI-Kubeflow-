"""
Debug Parallel COVID-19 Detection Pipeline
Fixed version with enhanced error handling and debugging
"""

import kfp
from kfp import dsl
from kfp.dsl import component


@component(
    base_image="python:3.10-slim",
    packages_to_install=[
        "numpy==1.26.3",
        "matplotlib==3.8.2"
    ]
)
def debug_load_patient_data_op(
    input_dir: str,
    patient_id: str
) -> str:
    """Debug Load Data Component - Enhanced Error Handling"""
    import json
    import os
    from pathlib import Path

    print(f"[DEBUG-LOAD] Starting for patient: {patient_id}")
    print(f"[DEBUG-LOAD] Input directory: {input_dir}")

    try:
        # Enhanced validation
        input_path = Path(input_dir)
        if not input_path.exists():
            print(f"[WARNING] Input directory {input_dir} does not exist")
            # Create dummy input for testing
            input_path.mkdir(parents=True, exist_ok=True)

        metadata = {
            "component": "debug_load_data",
            "patient_id": patient_id,
            "input_dir": input_dir,
            "status": "completed",
            "timestamp": "2025-11-17T20:00:00Z",
            "debug_info": {
                "input_exists": input_path.exists(),
                "input_is_dir": input_path.is_dir() if input_path.exists() else False
            }
        }

        result = json.dumps(metadata, indent=2)
        print(f"[DEBUG-LOAD] Success for {patient_id}")
        print(f"[DEBUG-LOAD] Result length: {len(result)} characters")

        return result

    except Exception as e:
        print(f"[ERROR-LOAD] Failed for {patient_id}: {str(e)}")
        error_result = {
            "component": "debug_load_data",
            "patient_id": patient_id,
            "status": "failed",
            "error": str(e),
            "timestamp": "2025-11-17T20:00:00Z"
        }
        return json.dumps(error_result, indent=2)


@component(
    base_image="python:3.10-slim",
    packages_to_install=[
        "numpy==1.26.3",
        "matplotlib==3.8.2"
    ]
)
def debug_segment_lungs_op(
    load_result: str,
    patient_id: str
) -> str:
    """Debug Lung Segmentation Component - Enhanced Error Handling"""
    import json
    import numpy as np

    print(f"[DEBUG-SEGMENT] Starting for patient: {patient_id}")
    print(f"[DEBUG-SEGMENT] Load result length: {len(load_result)} characters")

    try:
        # Parse load result
        try:
            load_data = json.loads(load_result)
            print(f"[DEBUG-SEGMENT] Parsed load data successfully")
            print(f"[DEBUG-SEGMENT] Load status: {load_data.get('status', 'unknown')}")
        except json.JSONDecodeError as e:
            print(f"[ERROR-SEGMENT] Failed to parse load result: {e}")
            load_data = {"error": "Failed to parse load result"}

        # Enhanced segmentation simulation
        np.random.seed(42 + hash(patient_id) % 10)
        lung_volume = int(np.random.uniform(7000000, 9000000))

        results = {
            "component": "debug_lung_segmentation",
            "patient_id": patient_id,
            "load_status": load_data.get("status", "unknown"),
            "lung_volume": lung_volume,
            "right_lung": int(lung_volume * 0.55),
            "left_lung": int(lung_volume * 0.45),
            "debug_info": {
                "load_result_valid": json.loads(load_result).get("status") == "completed",
                "seed_used": 42 + hash(patient_id) % 10,
                "volume_range": "7M-9M voxels"
            },
            "status": "completed"
        }

        result = json.dumps(results, indent=2)
        print(f"[DEBUG-SEGMENT] Success for {patient_id}")
        print(f"[DEBUG-SEGMENT] Lung volume: {lung_volume:,} voxels")

        return result

    except Exception as e:
        print(f"[ERROR-SEGMENT] Failed for {patient_id}: {str(e)}")
        import traceback
        traceback.print_exc()

        error_result = {
            "component": "debug_lung_segmentation",
            "patient_id": patient_id,
            "status": "failed",
            "error": str(e),
            "timestamp": "2025-11-17T20:00:00Z"
        }
        return json.dumps(error_result, indent=2)


@component(
    base_image="python:3.10-slim",
    packages_to_install=[
        "numpy==1.26.3",
        "matplotlib==3.8.2"
    ]
)
def debug_detect_covid_op(
    segmentation_result: str,
    patient_id: str
) -> str:
    """Debug COVID Detection Component - Enhanced Error Handling"""
    import json
    import numpy as np

    print(f"[DEBUG-DETECT] Starting for patient: {patient_id}")
    print(f"[DEBUG-DETECT] Segmentation result length: {len(segmentation_result)} characters")

    try:
        # Parse segmentation result
        try:
            seg_data = json.loads(segmentation_result)
            print(f"[DEBUG-DETECT] Parsed segmentation data successfully")
            print(f"[DEBUG-DETECT] Segmentation status: {seg_data.get('status', 'unknown')}")
            lung_volume = seg_data.get("lung_volume", 8000000)
            print(f"[DEBUG-DETECT] Lung volume from segmentation: {lung_volume:,}")
        except json.JSONDecodeError as e:
            print(f"[ERROR-DETECT] Failed to parse segmentation result: {e}")
            lung_volume = 8000000  # Default value
            seg_data = {"error": "Failed to parse segmentation result"}

        # Enhanced COVID detection simulation
        np.random.seed(100 + hash(patient_id) % 10)
        infection_ratio = np.random.uniform(0.05, 0.35)

        if infection_ratio > 0.25:
            likelihood = "HIGH"
            probability = int(75 + np.random.uniform(0, 20))
        elif infection_ratio > 0.15:
            likelihood = "MODERATE"
            probability = int(50 + np.random.uniform(0, 25))
        else:
            likelihood = "LOW"
            probability = int(20 + np.random.uniform(0, 30))

        recommendation_map = {
            "HIGH": "Urgent radiologist review required",
            "MODERATE": "Radiologist review within 24 hours",
            "LOW": "Consider follow-up imaging in 3-5 days"
        }

        results = {
            "component": "debug_covid_detection",
            "patient_id": patient_id,
            "seg_status": seg_data.get("status", "unknown"),
            "final_diagnosis": {
                "likelihood": likelihood,
                "probability": probability,
                "confidence": "medium",
                "recommendation": recommendation_map[likelihood]
            },
            "infection_ratio": float(infection_ratio),
            "debug_info": {
                "segmentation_valid": seg_data.get("status") == "completed",
                "lung_volume_used": lung_volume,
                "infection_ratio": float(infection_ratio),
                "seed_used": 100 + hash(patient_id) % 10
            },
            "status": "completed"
        }

        result = json.dumps(results, indent=2)
        print(f"[DEBUG-DETECT] Success for {patient_id}")
        print(f"[DEBUG-DETECT] COVID likelihood: {likelihood} ({probability}%)")

        return result

    except Exception as e:
        print(f"[ERROR-DETECT] Failed for {patient_id}: {str(e)}")
        import traceback
        traceback.print_exc()

        error_result = {
            "component": "debug_covid_detection",
            "patient_id": patient_id,
            "status": "failed",
            "error": str(e),
            "timestamp": "2025-11-17T20:00:00Z"
        }
        return json.dumps(error_result, indent=2)


@component(
    base_image="python:3.10-slim",
    packages_to_install=[
        "numpy==1.26.3",
        "matplotlib==3.8.2"
    ]
)
def debug_create_visualization_op(
    detection_result: str,
    patient_id: str,
    output_dir: str
) -> str:
    """Debug Visualization Component - Enhanced Error Handling"""
    import json
    import numpy as np
    import matplotlib
    matplotlib.use('Agg')  # Use non-interactive backend
    import matplotlib.pyplot as plt
    from pathlib import Path

    print(f"[DEBUG-VIZ] Starting for patient: {patient_id}")
    print(f"[DEBUG-VIZ] Detection result length: {len(detection_result)} characters")
    print(f"[DEBUG-VIZ] Output directory: {output_dir}")

    try:
        # Parse detection result
        try:
            detect_data = json.loads(detection_result)
            print(f"[DEBUG-VIZ] Parsed detection data successfully")
            print(f"[DEBUG-VIZ] Detection status: {detect_data.get('status', 'unknown')}")

            diagnosis = detect_data.get('final_diagnosis', {})
            likelihood = diagnosis.get('likelihood', 'UNKNOWN')
            probability = diagnosis.get('probability', 0)

            print(f"[DEBUG-VIZ] COVID diagnosis: {likelihood} ({probability}%)")

        except json.JSONDecodeError as e:
            print(f"[ERROR-VIZ] Failed to parse detection result: {e}")
            likelihood = "UNKNOWN"
            probability = 0
            diagnosis = {"likelihood": likelihood, "probability": probability}

        # Create output directory
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        print(f"[DEBUG-VIZ] Output directory created/verified: {output_path}")

        # Create simple visualization
        fig, axes = plt.subplots(2, 2, figsize=(12, 10))
        fig.suptitle(f'Debug COVID-19 Pipeline - {patient_id}', fontsize=16, fontweight='bold')

        # Pipeline stages
        stages = [
            ("Load Data", "Data", "green", "Completed"),
            ("Segment Lungs", "Segment", "blue", "Completed"),
            ("Detect COVID", "Detect", "orange", "Completed"),
            ("Visualization", "Visual", "purple", "In Progress")
        ]

        for idx, (step, short, color, status) in enumerate(stages):
            row, col = divmod(idx, 2)
            axes[row, col].text(0.5, 0.5, f'{step}\n{status}',
                              ha='center', va='center', transform=axes[row, col].transAxes,
                              fontsize=14, fontweight='bold', color=color)
            axes[row, col].set_title(f'Component {idx+1}')
            axes[row, col].axis('off')

        # COVID results
        colors_map = {
            'HIGH': '#FF4444',
            'MODERATE': '#FFA500',
            'LOW': '#4CAF50',
            'UNKNOWN': '#666666'
        }
        color = colors_map.get(likelihood, '#666666')

        result_text = f'''COVID-19 Results - {patient_id}

Likelihood: {likelihood}
Probability: {probability}%
Recommendation: {diagnosis.get('recommendation', 'N/A')}

Debug Status: Pipeline Active
Component: debug_visualization'''

        axes[1, 1].text(0.05, 0.5, result_text,
                       transform=axes[1, 1].transAxes, fontsize=10,
                       color=color, verticalalignment='center', wrap=True)
        axes[1, 1].set_title('Diagnosis Results')
        axes[1, 1].axis('off')

        plt.tight_layout()

        # Save visualization
        viz_file = output_path / f"{patient_id}_debug_pipeline.png"
        plt.savefig(viz_file, dpi=150, bbox_inches='tight')
        plt.close()

        print(f"[DEBUG-VIZ] Visualization saved: {viz_file}")
        print(f"[DEBUG-VIZ] File size: {viz_file.stat().st_size} bytes")

        viz_results = {
            "component": "debug_visualization",
            "patient_id": patient_id,
            "detection_status": detect_data.get("status", "unknown"),
            "visualization_file": str(viz_file),
            "likelihood": likelihood,
            "pipeline_stages": 4,
            "debug_info": {
                "file_saved": True,
                "file_size_bytes": viz_file.stat().st_size,
                "matplotlib_backend": "Agg"
            },
            "status": "completed"
        }

        result = json.dumps(viz_results, indent=2)
        print(f"[DEBUG-VIZ] Success for {patient_id}")

        return result

    except Exception as e:
        print(f"[ERROR-VIZ] Failed for {patient_id}: {str(e)}")
        import traceback
        traceback.print_exc()

        error_result = {
            "component": "debug_visualization",
            "patient_id": patient_id,
            "status": "failed",
            "error": str(e),
            "timestamp": "2025-11-17T20:00:00Z"
        }
        return json.dumps(error_result, indent=2)


@component(
    base_image="python:3.10-slim",
    packages_to_install=["numpy==1.26.3"]
)
def debug_generate_summary_op(
    patient_1_viz: str,
    patient_2_viz: str,
    patient_3_viz: str,
    patient_4_viz: str,
    output_dir: str
) -> str:
    """Debug Summary Component - Enhanced Error Handling"""
    import json
    from datetime import datetime
    from pathlib import Path

    print(f"[DEBUG-SUMMARY] Starting parallel processing summary")

    try:
        viz_results = []
        patient_ids = ["lung_001", "lung_002", "lung_003", "lung_004"]
        patient_viz_results = [patient_1_viz, patient_2_viz, patient_3_viz, patient_4_viz]

        for i, (patient_id, viz_str) in enumerate(zip(patient_ids, patient_viz_results)):
            print(f"[DEBUG-SUMMARY] Processing {patient_id} viz result ({len(viz_str)} chars)")

            try:
                viz_data = json.loads(viz_str)
                viz_results.append({
                    "patient_id": patient_id,
                    "component": viz_data.get("component", "unknown"),
                    "likelihood": viz_data.get("likelihood", "UNKNOWN"),
                    "status": viz_data.get("status", "unknown")
                })
                print(f"[DEBUG-SUMMARY] {patient_id}: status={viz_data.get('status')}, likelihood={viz_data.get('likelihood')}")
            except json.JSONDecodeError as e:
                print(f"[ERROR-SUMMARY] Failed to parse {patient_id} result: {e}")
                viz_results.append({
                    "patient_id": patient_id,
                    "component": "visualization",
                    "likelihood": "UNKNOWN",
                    "status": "parse_error"
                })

        # Count risk levels
        risk_counts = {
            "HIGH": sum(1 for v in viz_results if v.get("likelihood") == "HIGH"),
            "MODERATE": sum(1 for v in viz_results if v.get("likelihood") == "MODERATE"),
            "LOW": sum(1 for v in viz_results if v.get("likelihood") == "LOW"),
            "UNKNOWN": sum(1 for v in viz_results if v.get("likelihood") == "UNKNOWN")
        }

        successful_count = sum(1 for v in viz_results if v.get("status") == "completed")

        report = {
            "debug_parallel_processing_report": {
                "timestamp": datetime.now().isoformat(),
                "total_patients": len(viz_results),
                "successful": successful_count,
                "failed": len(viz_results) - successful_count,
                "processing_mode": "debug_parallel_visual",
                "pipeline_architecture": "debug_individual_components_per_patient"
            },
            "workflow_visualization": {
                "description": "4 Patients with Debug Individual Component Tracking",
                "pipeline_per_patient": [
                    "1. Load Data (debug_load_patient_data_op)",
                    "2. Lung Segmentation (debug_segment_lungs_op)",
                    "3. COVID Detection (debug_detect_covid_op)",
                    "4. Visualization (debug_create_visualization_op)"
                ],
                "total_components": 16,
                "component_separation": True
            },
            "patients": viz_results,
            "risk_distribution": risk_counts,
            "debug_info": {
                "all_viz_results_processed": len(viz_results) == 4,
                "success_rate": f"{(successful_count/len(viz_results)*100):.1f}%",
                "component_statuses": [v.get("status") for v in viz_results]
            },
            "kubeflow_ui_display": {
                "total_components": 16,
                "component_types": 4,
                "patients_processed": len(viz_results),
                "clear_separation": "Each component type shows as separate task with debugging"
            }
        }

        # Save report
        output_path = Path(output_dir) / "debug_parallel_summary_report.json"
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w') as f:
            json.dump(report, f, indent=2)

        print(f"[DEBUG-SUMMARY] Report saved to: {output_path}")
        print(f"[DEBUG-SUMMARY] Success rate: {(successful_count/len(viz_results)*100):.1f}%")

        return json.dumps({"status": "completed", "report_file": str(output_path), "success_rate": successful_count})

    except Exception as e:
        print(f"[ERROR-SUMMARY] Failed to generate summary: {str(e)}")
        import traceback
        traceback.print_exc()

        return json.dumps({"status": "failed", "error": str(e)})


@dsl.pipeline(
    name="debug-parallel-covid-pipeline",
    description="Debug Parallel COVID-19 Detection Pipeline - Enhanced Error Handling and Diagnostics"
)
def debug_parallel_covid_pipeline(
    input_dir: str = "/mnt/data/weekly_input",
    output_dir: str = "/mnt/data/hospital_output"
):
    """Debug parallel pipeline with enhanced error handling"""

    patients = ["lung_001", "lung_002", "lung_003", "lung_004"]

    # Process Patient 1 with debugging
    p1_load = debug_load_patient_data_op(
        input_dir=input_dir,
        patient_id=patients[0]
    ).set_display_name("DEBUG - Patient 1 - Load Data")
    p1_load.set_cpu_limit("1")
    p1_load.set_memory_limit("2Gi")

    p1_seg = debug_segment_lungs_op(
        load_result=p1_load.output,
        patient_id=patients[0]
    ).set_display_name("DEBUG - Patient 1 - Segment Lungs")
    p1_seg.set_cpu_limit("2")
    p1_seg.set_memory_limit("4Gi")
    p1_seg.after(p1_load)

    p1_detect = debug_detect_covid_op(
        segmentation_result=p1_seg.output,
        patient_id=patients[0]
    ).set_display_name("DEBUG - Patient 1 - Detect COVID")
    p1_detect.set_cpu_limit("2")
    p1_detect.set_memory_limit("4Gi")
    p1_detect.after(p1_seg)

    p1_viz = debug_create_visualization_op(
        detection_result=p1_detect.output,
        patient_id=patients[0],
        output_dir=output_dir
    ).set_display_name("DEBUG - Patient 1 - Create Viz")
    p1_viz.set_cpu_limit("1")
    p1_viz.set_memory_limit("2Gi")
    p1_viz.after(p1_detect)

    # Process Patient 2 with debugging
    p2_load = debug_load_patient_data_op(
        input_dir=input_dir,
        patient_id=patients[1]
    ).set_display_name("DEBUG - Patient 2 - Load Data")
    p2_load.set_cpu_limit("1")
    p2_load.set_memory_limit("2Gi")

    p2_seg = debug_segment_lungs_op(
        load_result=p2_load.output,
        patient_id=patients[1]
    ).set_display_name("DEBUG - Patient 2 - Segment Lungs")
    p2_seg.set_cpu_limit("2")
    p2_seg.set_memory_limit("4Gi")
    p2_seg.after(p2_load)

    p2_detect = debug_detect_covid_op(
        segmentation_result=p2_seg.output,
        patient_id=patients[1]
    ).set_display_name("DEBUG - Patient 2 - Detect COVID")
    p2_detect.set_cpu_limit("2")
    p2_detect.set_memory_limit("4Gi")
    p2_detect.after(p2_seg)

    p2_viz = debug_create_visualization_op(
        detection_result=p2_detect.output,
        patient_id=patients[1],
        output_dir=output_dir
    ).set_display_name("DEBUG - Patient 2 - Create Viz")
    p2_viz.set_cpu_limit("1")
    p2_viz.set_memory_limit("2Gi")
    p2_viz.after(p2_detect)

    # Process Patient 3 with debugging
    p3_load = debug_load_patient_data_op(
        input_dir=input_dir,
        patient_id=patients[2]
    ).set_display_name("DEBUG - Patient 3 - Load Data")
    p3_load.set_cpu_limit("1")
    p3_load.set_memory_limit("2Gi")

    p3_seg = debug_segment_lungs_op(
        load_result=p3_load.output,
        patient_id=patients[2]
    ).set_display_name("DEBUG - Patient 3 - Segment Lungs")
    p3_seg.set_cpu_limit("2")
    p3_seg.set_memory_limit("4Gi")
    p3_seg.after(p3_load)

    p3_detect = debug_detect_covid_op(
        segmentation_result=p3_seg.output,
        patient_id=patients[2]
    ).set_display_name("DEBUG - Patient 3 - Detect COVID")
    p3_detect.set_cpu_limit("2")
    p3_detect.set_memory_limit("4Gi")
    p3_detect.after(p3_seg)

    p3_viz = debug_create_visualization_op(
        detection_result=p3_detect.output,
        patient_id=patients[2],
        output_dir=output_dir
    ).set_display_name("DEBUG - Patient 3 - Create Viz")
    p3_viz.set_cpu_limit("1")
    p3_viz.set_memory_limit("2Gi")
    p3_viz.after(p3_detect)

    # Process Patient 4 with debugging
    p4_load = debug_load_patient_data_op(
        input_dir=input_dir,
        patient_id=patients[3]
    ).set_display_name("DEBUG - Patient 4 - Load Data")
    p4_load.set_cpu_limit("1")
    p4_load.set_memory_limit("2Gi")

    p4_seg = debug_segment_lungs_op(
        load_result=p4_load.output,
        patient_id=patients[3]
    ).set_display_name("DEBUG - Patient 4 - Segment Lungs")
    p4_seg.set_cpu_limit("2")
    p4_seg.set_memory_limit("4Gi")
    p4_seg.after(p4_load)

    p4_detect = debug_detect_covid_op(
        segmentation_result=p4_seg.output,
        patient_id=patients[3]
    ).set_display_name("DEBUG - Patient 4 - Detect COVID")
    p4_detect.set_cpu_limit("2")
    p4_detect.set_memory_limit("4Gi")
    p4_detect.after(p4_seg)

    p4_viz = debug_create_visualization_op(
        detection_result=p4_detect.output,
        patient_id=patients[3],
        output_dir=output_dir
    ).set_display_name("DEBUG - Patient 4 - Create Viz")
    p4_viz.set_cpu_limit("1")
    p4_viz.set_memory_limit("2Gi")
    p4_viz.after(p4_detect)

    # Generate Debug Summary
    summary_task = debug_generate_summary_op(
        patient_1_viz=p1_viz.output,
        patient_2_viz=p2_viz.output,
        patient_3_viz=p3_viz.output,
        patient_4_viz=p4_viz.output,
        output_dir=output_dir
    ).set_display_name("DEBUG - Generate Summary")
    summary_task.set_cpu_limit("1")
    summary_task.set_memory_limit("1Gi")

    # Set dependencies
    summary_task.after(p1_viz)
    summary_task.after(p2_viz)
    summary_task.after(p3_viz)
    summary_task.after(p4_viz)


def compile_debug_pipeline():
    """Compile the debug parallel pipeline"""
    print("[COMPILING] Debug parallel COVID-19 detection pipeline...")
    print("Enhanced with error handling and detailed logging!")

    try:
        # Compile pipeline
        kfp.compiler.Compiler().compile(
            debug_parallel_covid_pipeline,
            "debug_parallel_pipeline.yaml"
        )

        print("[SUCCESS] Debug parallel pipeline compiled successfully!")
        print("[OUTPUT] debug_parallel_pipeline.yaml")

        # Validate the YAML
        import yaml
        with open("debug_parallel_pipeline.yaml", 'r') as f:
            pipeline_spec = yaml.safe_load(f)

        # Extract pipeline info
        pipeline_info = pipeline_spec.get('pipelineSpec', {}).get('pipelineInfo', {})

        print("\n" + "="*80)
        print("DEBUG PARALLEL PIPELINE - ENHANCED ERROR HANDLING")
        print("="*80)
        print(f"[INFO] Pipeline Name: {pipeline_info.get('name', 'Unknown')}")
        print(f"[INFO] Description: {pipeline_info.get('description', 'No description')}")

        # Count components
        executors = pipeline_spec.get('deploymentSpec', {}).get('executors', {})
        print(f"[INFO] Total Components: {len(executors)}")

        print("\n[DEBUG FEATURES]:")
        print("- Enhanced error handling in all components")
        print("- Detailed logging and debugging information")
        print("- JSON parsing validation")
        print("- File I/O error handling")
        print("- Matplotlib backend configuration")
        print("- Component status tracking")

        print("\n[DEPLOYMENT]:")
        print("1. Upload debug_parallel_pipeline.yaml to Kubeflow")
        print("2. Check component logs for detailed debugging")
        print("3. Each component shows detailed error information")
        print("4. Summary includes success/failure statistics")

        print("\n" + "="*80)
        print("DEBUG PARALLEL PIPELINE READY!")
        print("="*80)

        return "debug_parallel_pipeline.yaml"

    except Exception as e:
        print(f"[ERROR] Pipeline compilation failed: {e}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == "__main__":
    result = compile_debug_pipeline()

    if result:
        print(f"\n[SUCCESS] {result}")
        print("\n[DEBUG FEATURES]:")
        print("- Enhanced error handling and logging")
        print("- Component-by-component debugging")
        print("- Detailed error messages")
        print("- Success/failure tracking")
        print("- Kubeflow UI compatible debugging")
        print("\n[USAGE]: Deploy this debug version to identify the exact issue!")
    else:
        print("\n[FAILED] Could not compile debug pipeline")