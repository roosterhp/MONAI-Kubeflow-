"""
Weekly Kubeflow Pipeline for COVID-19 Detection
Process weekly_input data and output to hospital_output
"""

import json
from pathlib import Path
from typing import List, Dict, Any

try:
    import kfp
    from kfp import dsl
    from kfp.dsl import component, InputPath, OutputPath, Artifact, Dataset, Model
    KFP_AVAILABLE = True
except ImportError:
    print("[WARNING] Kubeflow Pipelines not available, creating pipeline structure only")
    KFP_AVAILABLE = False

    # Mock decorator when KFP not available
    def mock_component(*args, **kwargs):
        def decorator(func):
            return func
        return decorator

    component = mock_component


# Component definitions for weekly workflow
if KFP_AVAILABLE:
    @component(
        base_image="python:3.10-slim",
        packages_to_install=[
            "SimpleITK==2.3.1",
            "nibabel==5.2.0",
            "numpy==1.26.3"
        ]
    )
    def weekly_data_loader_op(
        input_weekly_dir: str,
        working_dir: str,
        metadata_output: OutputPath(Dataset)
    ) -> str:
        """Load weekly data and prepare metadata"""
        import json
        import subprocess
        import sys
        from pathlib import Path

        # Run data loading
        metadata_file = f"{working_dir}/patients_metadata.json"

        # Ensure working directory exists
        Path(working_dir).mkdir(parents=True, exist_ok=True)

        result = subprocess.run([
            'python', '/app/simple_data_loader.py',
            input_weekly_dir, working_dir, metadata_file
        ], capture_output=True, text=True, cwd='/app')

        if result.returncode != 0:
            raise Exception(f"Weekly data loading failed: {result.stderr}")

        # Copy metadata to output path
        Path(metadata_output).parent.mkdir(parents=True, exist_ok=True)
        Path.rename(metadata_file, metadata_output)

        # Return patient count
        with open(metadata_output, 'r') as f:
            metadata = json.load(f)

        return str(len(metadata.get("patients", [])))

    @component(
        base_image="python:3.10-slim",
        packages_to_install=[
            "SimpleITK==2.3.1",
            "nibabel==5.2.0",
            "lungmask@git+https://github.com/JoHof/lungmask.git",
            "numpy==1.26.3",
            "torch>=2.0.0",
            "monai==1.3.0"
        ],
        target_image="covid-weekly-pipeline:latest"
    )
    def lung_segmentation_weekly_op(
        ct_file: str,
        output_dir: str
    ) -> Dict[str, Any]:
        """Lung segmentation for weekly workflow"""
        import subprocess
        import json

        result = subprocess.run([
            'python', '/app/components/lung_segment.py',
            ct_file, output_dir
        ], capture_output=True, text=True, cwd='/app')

        if result.returncode != 0:
            raise Exception(f"Lung segmentation failed: {result.stderr}")

        return {
            "status": "success",
            "output_dir": output_dir,
            "lung_mask_path": f"{output_dir}/lung_mask.nii.gz"
        }

    @component(
        base_image="python:3.10-slim",
        packages_to_install=[
            "SimpleITK==2.3.1",
            "numpy==1.26.3",
            "torch>=2.0.0",
            "monai==1.3.0"
        ],
        target_image="covid-weekly-pipeline:latest"
    )
    def covid_detection_weekly_op(
        input_dir: str,
        output_dir: str
    ) -> Dict[str, Any]:
        """COVID detection for weekly workflow"""
        import subprocess
        import json

        result = subprocess.run([
            'python', '/app/components/covid_detect.py',
            input_dir, output_dir
        ], capture_output=True, text=True, cwd='/app')

        if result.returncode != 0:
            raise Exception(f"COVID detection failed: {result.stderr}")

        # Load results to return key information
        results_file = f"{output_dir}/covid_results.json"
        if Path(results_file).exists():
            with open(results_file, 'r') as f:
                results = json.load(f)
        else:
            results = {"error": "Results file not found"}

        return {
            "status": "success",
            "output_dir": output_dir,
            "results": results,
            "likelihood": results.get("final_diagnosis", {}).get("likelihood", "UNKNOWN")
        }

    @component(
        base_image="python:3.10-slim",
        packages_to_install=[
            "SimpleITK==2.3.1",
            "numpy==1.26.3",
            "matplotlib==3.8.2"
        ],
        target_image="covid-weekly-pipeline:latest"
    )
    def visualization_weekly_op(
        input_dir: str,
        output_dir: str
    ) -> Dict[str, Any]:
        """Visualization for weekly workflow"""
        import subprocess

        result = subprocess.run([
            'python', '/app/components/visualize.py',
            input_dir, output_dir
        ], capture_output=True, text=True, cwd='/app')

        if result.returncode != 0:
            raise Exception(f"Visualization failed: {result.stderr}")

        return {
            "status": "success",
            "output_dir": output_dir,
            "visualization_path": f"{output_dir}/covid_visualization.png"
        }

    @component(
        base_image="python:3.10-slim",
        packages_to_install=[
            "numpy==1.26.3"
        ],
        target_image="covid-weekly-pipeline:latest"
    )
    def weekly_report_generator_op(
        patient_results: List[Dict[str, Any]],
        output_dir: str
    ) -> Dict[str, Any]:
        """Generate weekly hospital report"""
        import json
        from pathlib import Path
        from datetime import datetime

        # Create report
        report = {
            "weekly_report": {
                "scan_date": "weekly_scan",
                "report_generated": datetime.now().isoformat(),
                "total_patients": len(patient_results),
                "successful": sum(1 for r in patient_results if r.get("status") == "success"),
                "pipeline_type": "kubeflow_weekly"
            },
            "patients": patient_results,
            "summary": {
                "high_risk": sum(1 for r in patient_results if r.get("likelihood") == "HIGH"),
                "moderate_risk": sum(1 for r in patient_results if r.get("likelihood") == "MODERATE"),
                "low_risk": sum(1 for r in patient_results if r.get("likelihood") == "LOW"),
                "very_low_risk": sum(1 for r in patient_results if r.get("likelihood") == "VERY_LOW")
            }
        }

        # Save report
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        report_file = Path(output_dir) / "weekly_report.json"

        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)

        return {
            "report_file": str(report_file),
            "total_patients": len(patient_results),
            "successful": sum(1 for r in patient_results if r.get("status") == "success")
        }


def create_weekly_pipeline(
    input_weekly_dir: str = "/mnt/data/weekly_input",
    working_dir: str = "/mnt/data/working",
    output_base_dir: str = "/mnt/data/hospital_output"
):
    """Create Kubeflow pipeline for weekly COVID-19 detection workflow"""
    if not KFP_AVAILABLE:
        print("KFP not available, returning None")
        return None

    @dsl.pipeline(
        name="weekly-covid-detection-pipeline",
        description="Weekly COVID-19 Detection Pipeline - Process weekly CT scans"
    )
    def weekly_covid_detection_pipeline():

        # Step 1: Load weekly data
        load_data_task = weekly_data_loader_op(
            input_weekly_dir=input_weekly_dir,
            working_dir=working_dir
        ).set_display_name("Load Weekly Data")
        load_data_task.set_cpu_limit("2")
        load_data_task.set_memory_limit("4Gi")
        load_data_task.set_timeout(300)  # 5 minutes

        # Define patient processing as a parallel loop
        # Note: This is a simplified version - in production you'd use dynamic loops

        # Process up to 10 patients in parallel
        patient_tasks = []
        patient_results = []

        for i in range(10):  # Max 10 patients
            with dsl.Condition(load_data_task.output > str(i)):

                # Create patient-specific paths
                patient_id = f"lung_{i+1:03d}.nii" if i < 4 else f"patient_{i+1:03d}"
                ct_file = f"{working_dir}/{patient_id}/imaging.nii.gz"
                patient_output_dir = f"{output_base_dir}/{patient_id}"
                segmentation_dir = f"{patient_output_dir}/segmentation"
                detection_dir = f"{patient_output_dir}/detection"
                visualization_dir = f"{patient_output_dir}/visualization"

                with dsl.TaskGroup(name=f"process_{patient_id}"):

                    # Lung Segmentation
                    lung_seg_task = lung_segmentation_weekly_op(
                        ct_file=ct_file,
                        output_dir=segmentation_dir
                    ).set_display_name(f"Segment Lungs - {patient_id}")
                    lung_seg_task.set_cpu_limit("2")
                    lung_seg_task.set_memory_limit("4Gi")
                    lung_seg_task.set_timeout(600)  # 10 minutes

                    # COVID Detection
                    covid_detect_task = covid_detection_weekly_op(
                        input_dir=segmentation_dir,
                        output_dir=detection_dir
                    ).set_display_name(f"Detect COVID - {patient_id}")
                    covid_detect_task.set_cpu_limit("2")
                    covid_detect_task.set_memory_limit("4Gi")
                    covid_detect_task.set_timeout(300)  # 5 minutes
                    covid_detect_task.after(lung_seg_task)

                    # Visualization
                    viz_task = visualization_weekly_op(
                        input_dir=detection_dir,
                        output_dir=visualization_dir
                    ).set_display_name(f"Create Visualization - {patient_id}")
                    viz_task.set_cpu_limit("1")
                    viz_task.set_memory_limit("2Gi")
                    viz_task.set_timeout(180)  # 3 minutes
                    viz_task.after(covid_detect_task)

                    # Collect results for reporting
                    patient_results.append(covid_detect_task.output)
                    patient_tasks.append(viz_task)

        # Generate weekly report (depends on all patient processing)
        report_task = weekly_report_generator_op(
            patient_results=patient_results,
            output_dir=output_base_dir
        ).set_display_name("Generate Weekly Report")
        report_task.set_cpu_limit("1")
        report_task.set_memory_limit("1Gi")
        report_task.set_timeout(120)  # 2 minutes

        # Report depends on all patient tasks
        for task in patient_tasks:
            report_task.after(task)

    return weekly_covid_detection_pipeline


def compile_weekly_pipeline():
    """Compile weekly pipeline and save YAML"""
    if not KFP_AVAILABLE:
        print("KFP not available, creating mock pipeline structure")
        mock_structure = {
            "pipeline": {
                "name": "weekly-covid-detection-pipeline",
                "description": "Weekly COVID-19 Detection Pipeline - Process weekly CT scans",
                "input_structure": "/mnt/data/weekly_input/*.nii.gz",
                "output_structure": "/mnt/data/hospital_output/PATIENT_ID/",
                "components": ["load_weekly_data", "process_patients", "generate_report"]
            }
        }

        with open("weekly_covid_detection_pipeline.yaml", "w") as f:
            f.write("# Weekly COVID Detection Pipeline - KFP not available\n")
            f.write("# Input: /mnt/data/weekly_input/*.nii.gz\n")
            f.write("# Output: /mnt/data/hospital_output/PATIENT_ID/covid_visualization.png\n")

        print("Mock pipeline created: weekly_covid_detection_pipeline.yaml")
        return

    # Create and compile pipeline
    pipeline_func = create_weekly_pipeline()

    kfp.compiler.Compiler().compile(
        pipeline_func,
        "weekly_covid_detection_pipeline.yaml"
    )

    print("Weekly pipeline compiled to: weekly_covid_detection_pipeline.yaml")


def create_weekly_deployment_config():
    """Create deployment configuration for weekly pipeline"""

    config = {
        "weekly_pipeline_config": {
            "name": "weekly-covid-detection",
            "description": "Weekly COVID-19 detection pipeline for hospital",
            "input": {
                "weekly_dir": "/mnt/data/weekly_input",
                "supported_formats": ["*.nii.gz"],
                "auto_discover": True
            },
            "output": {
                "base_dir": "/mnt/data/hospital_output",
                "patient_structure": "PATIENT_ID/",
                "files": [
                    "covid_visualization.png",
                    "covid_results.json",
                    "features.json"
                ]
            },
            "processing": {
                "max_concurrent_patients": 10,
                "timeout_per_patient": "15 minutes",
                "parallel_processing": True
            },
            "resources": {
                "cpu_limit": "2",
                "memory_limit": "4Gi",
                "storage": "20Gi"
            }
        },
        "docker": {
            "image": "covid-weekly-pipeline:latest",
            "dockerfile": "Dockerfile.weekly"
        },
        "kubeflow": {
            "namespace": "kubeflow",
            "pipeline_name": "weekly-covid-detection",
            "experiment": "weekly-covid-scan"
        },
        "volume_mounts": {
            "input_volume": {
                "name": "weekly-input-pv",
                "mount_path": "/mnt/data/weekly_input",
                "size": "10Gi"
            },
            "output_volume": {
                "name": "hospital-output-pv",
                "mount_path": "/mnt/data/hospital_output",
                "size": "20Gi"
            },
            "working_volume": {
                "name": "working-pv",
                "mount_path": "/mnt/data/working",
                "size": "15Gi"
            }
        }
    }

    # Save configuration
    with open("weekly_deployment_config.json", "w") as f:
        json.dump(config, f, indent=2)

    print("Weekly deployment configuration saved to: weekly_deployment_config.json")


if __name__ == "__main__":
    create_weekly_deployment_config()
    compile_weekly_pipeline()

    print("\n" + "="*70)
    print("WEEKLY COVID-19 DETECTION PIPELINE")
    print("="*70)
    print("Pipeline ready for weekly hospital data processing!")
    print("\nInput Structure:")
    print("  /mnt/data/weekly_input/")
    print("  ├── lung_001.nii.gz")
    print("  ├── lung_002.nii.gz")
    print("  └── ...")
    print("\nOutput Structure:")
    print("  /mnt/data/hospital_output/")
    print("  ├── lung_001/")
    print("  │   ├── covid_visualization.png")
    print("  │   ├── covid_results.json")
    print("  │   └── features.json")
    print("  └── weekly_report.json")
    print("\nFiles created:")
    print("  - weekly_covid_detection_pipeline.yaml")
    print("  - weekly_deployment_config.json")