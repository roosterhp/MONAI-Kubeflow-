"""
Week5 COVID-19 Detection Kubeflow Pipeline
Clean implementation based on hospital-mlops covid-demo
"""

import json
from pathlib import Path
from typing import List, Dict, Any

try:
    import kfp
    from kfp import dsl
    from kfp.dsl import component, InputPath, OutputPath, Artifact
    KFP_AVAILABLE = True
except ImportError:
    print("[WARNING] Kubeflow Pipelines not available, creating pipeline structure only")
    KFP_AVAILABLE = False

    # Create mock decorator for when KFP is not available
    def mock_component(*args, **kwargs):
        def decorator(func):
            return func
        return decorator

    component = mock_component


# Component definitions for KFP
if KFP_AVAILABLE:
    @component(
        base_image="python:3.10-slim",
        packages_to_install=[
            "SimpleITK==2.3.1",
            "nibabel==5.2.0",
            "lungmask@git+https://github.com/JoHof/lungmask.git",
            "numpy==1.26.3",
            "torch>=2.0.0",
            "monai==1.3.0",
            "matplotlib==3.8.2"
        ]
    )
    def lung_segmentation_op(
        input_file: str,
        output_dir: str
    ) -> Dict[str, Any]:
        """Lung segmentation using LungMask"""
        import sys
        import subprocess

        # Add components to path
        sys.path.append('/app/components')

        # Run lung segmentation
        result = subprocess.run([
            'python', '/app/components/lung_segment.py',
            input_file, output_dir
        ], capture_output=True, text=True)

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
        ]
    )
    def covid_detection_op(
        input_dir: str,
        output_dir: str
    ) -> Dict[str, Any]:
        """COVID-19 detection using rule-based + MONAI ensemble"""
        import sys
        import subprocess

        # Add components to path
        sys.path.append('/app/components')

        # Run COVID detection
        result = subprocess.run([
            'python', '/app/components/covid_detect.py',
            input_dir, output_dir
        ], capture_output=True, text=True)

        if result.returncode != 0:
            raise Exception(f"COVID detection failed: {result.stderr}")

        return {
            "status": "success",
            "output_dir": output_dir,
            "results_path": f"{output_dir}/covid_results.json"
        }

    @component(
        base_image="python:3.10-slim",
        packages_to_install=[
            "SimpleITK==2.3.1",
            "numpy==1.26.3",
            "matplotlib==3.8.2"
        ]
    )
    def visualization_op(
        input_dir: str,
        output_dir: str
    ) -> Dict[str, Any]:
        """Create clinical visualization"""
        import sys
        import subprocess

        # Add components to path
        sys.path.append('/app/components')

        # Run visualization
        result = subprocess.run([
            'python', '/app/components/visualize.py',
            input_dir, output_dir
        ], capture_output=True, text=True)

        if result.returncode != 0:
            raise Exception(f"Visualization failed: {result.stderr}")

        return {
            "status": "success",
            "output_dir": output_dir,
            "visualization_path": f"{output_dir}/covid_visualization.png"
        }


def create_pipeline(patient_list: List[str], input_base_path: str, output_base_path: str):
    """Create Kubeflow pipeline for COVID-19 detection

    Args:
        patient_list: List of patient IDs to process
        input_base_path: Base path for input CT files
        output_base_path: Base path for output results
    """
    if not KFP_AVAILABLE:
        print("KFP not available, returning None")
        return None

    @dsl.pipeline(
        name="covid-19-detection-week5",
        description="COVID-19 Detection Pipeline with Lung Segmentation and Clinical Visualization"
    )
    def covid_detection_pipeline():

        # Process patients in parallel
        for patient_id in patient_list:

            # Construct paths
            input_file = f"{input_base_path}/{patient_id}/imaging.nii.gz"
            patient_output_dir = f"{output_base_path}/{patient_id}"
            lung_segment_dir = f"{patient_output_dir}/segmentation"
            covid_detect_dir = f"{patient_output_dir}/detection"
            viz_output_dir = f"{patient_output_dir}/visualization"

            with dsl.TaskGroup(name=f"process_{patient_id}"):

                # Step 1: Lung Segmentation
                lung_segment_task = lung_segmentation_op(
                    input_file=input_file,
                    output_dir=lung_segment_dir
                ).set_display_name(f"Segment Lungs - {patient_id}")

                # Step 2: COVID Detection (depends on lung segmentation)
                covid_detect_task = covid_detection_op(
                    input_dir=lung_segment_dir,
                    output_dir=covid_detect_dir
                ).set_display_name(f"Detect COVID - {patient_id}")
                covid_detect_task.after(lung_segment_task)

                # Step 3: Visualization (depends on both)
                viz_task = visualization_op(
                    input_dir=covid_detect_dir,
                    output_dir=viz_output_dir
                ).set_display_name(f"Create Visualization - {patient_id}")
                viz_task.after(covid_detect_task)

    return covid_detection_pipeline


def compile_pipeline():
    """Compile pipeline and save to YAML"""
    if not KFP_AVAILABLE:
        print("KFP not available, creating mock pipeline structure")
        # Create mock YAML structure
        mock_pipeline = {
            "pipeline": {
                "name": "covid-19-detection-week5",
                "description": "COVID-19 Detection Pipeline with Lung Segmentation and Clinical Visualization",
                "components": ["lung_segmentation", "covid_detection", "visualization"]
            }
        }
        with open("covid_detection_week5.yaml", "w") as f:
            f.write("# Mock pipeline YAML - KFP not available\n")
        print("Mock pipeline structure created: covid_detection_week5.yaml")
        return None

    # Example patient list
    patient_list = ["lung_001", "lung_002", "lung_003", "lung_004"]

    # Create pipeline
    pipeline_func = create_pipeline(
        patient_list=patient_list,
        input_base_path="/mnt/data/covid_inputs/week_current",
        output_base_path="/mnt/data/covid_outputs/week_current"
    )

    # Compile pipeline
    kfp.compiler.Compiler().compile(
        pipeline_func,
        "covid_detection_week5.yaml"
    )

    print("Pipeline compiled to: covid_detection_week5.yaml")


if __name__ == "__main__":
    # Create components directory structure for container build
    Path("components").mkdir(exist_ok=True)

    # Generate pipeline YAML
    compile_pipeline()

    # Create deployment configuration
    deployment_config = {
        "pipeline_name": "covid-19-detection-week5",
        "description": "Week5 COVID-19 Detection Pipeline with clean implementation",
        "components": [
            {
                "name": "lung_segmentation",
                "image": "covid-pipeline-week5:latest",
                "command": ["python", "/app/components/lung_segment.py"],
                "args": ["{{inputs.input_file}}", "{{inputs.output_dir}}"]
            },
            {
                "name": "covid_detection",
                "image": "covid-pipeline-week5:latest",
                "command": ["python", "/app/components/covid_detect.py"],
                "args": ["{{inputs.input_dir}}", "{{inputs.output_dir}}"]
            },
            {
                "name": "visualization",
                "image": "covid-pipeline-week5:latest",
                "command": ["python", "/app/components/visualize.py"],
                "args": ["{{inputs.input_dir}}", "{{inputs.output_dir}}"]
            }
        ],
        "patients": ["lung_001", "lung_002", "lung_003", "lung_004"],
        "input_path": "/mnt/data/covid_inputs/week_current",
        "output_path": "/mnt/data/covid_outputs/week_current"
    }

    # Save deployment config
    with open("deployment_config.json", "w") as f:
        json.dump(deployment_config, f, indent=2)

    print("Deployment configuration saved to: deployment_config.json")
    print("\nWeek5 COVID-19 Detection Pipeline created successfully!")
    print("\nNext steps:")
    print("1. Build container image: docker build -t covid-pipeline-week5:latest -f config/Dockerfile .")
    print("2. Upload to registry")
    print("3. Deploy to Kubeflow: kfp.Client().upload_pipeline(pipeline_file='covid_detection_week5.yaml')")