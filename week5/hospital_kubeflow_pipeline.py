"""
Hospital Kubeflow Pipeline - COVID-19 Detection
Tự động xử lý dữ liệu tuần của bệnh viện với Kubeflow
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
    print("[WARNING] Kubeflow Pipelines không có sẵn, tạo cấu trúc pipeline chỉ")
    KFP_AVAILABLE = False

    # Tạo mock decorator khi KFP không có sẵn
    def mock_component(*args, **kwargs):
        def decorator(func):
            return func
        return decorator

    component = mock_component


# Component definitions cho hospital workflow
if KFP_AVAILABLE:
    @component(
        base_image="python:3.10-slim",
        packages_to_install=[
            "SimpleITK==2.3.1",
            "nibabel==5.2.0",
            "numpy==1.26.3"
        ]
    )
    def hospital_data_loader_op(
        input_weekly_dir: str,
        working_dir: str
    ) -> Dict[str, Any]:
        """Tự động tải dữ liệu bệnh viện"""
        import subprocess
        import json

        # Chạy load_data component
        metadata_file = f"{working_dir}/patients_metadata.json"
        result = subprocess.run([
            'python', '/app/components/load_data.py',
            input_weekly_dir, working_dir, metadata_file
        ], capture_output=True, text=True)

        if result.returncode != 0:
            raise Exception(f"Hospital data loading failed: {result.stderr}")

        # Return metadata
        with open(metadata_file, 'r') as f:
            metadata = json.load(f)

        return metadata

    @component(
        base_image="python:3.10-slim",
        packages_to_install=[
            "SimpleITK==2.3.1",
            "nibabel==5.2.0",
            "lungmask@git+https://github.com/JoHof/lungmask.git",
            "numpy==1.26.3",
            "torch>=2.0.0",
            "monai==1.3.0"
        ]
    )
    def lung_segmentation_hospital_op(
        ct_file: str,
        output_dir: str
    ) -> Dict[str, Any]:
        """Lung segmentation cho workflow bệnh viện"""
        import subprocess

        result = subprocess.run([
            'python', '/app/components/lung_segment.py',
            ct_file, output_dir
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
    def covid_detection_hospital_op(
        input_dir: str,
        output_dir: str
    ) -> Dict[str, Any]:
        """COVID detection cho workflow bệnh viện"""
        import subprocess

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
    def visualization_hospital_op(
        input_dir: str,
        output_dir: str
    ) -> Dict[str, Any]:
        """Visualization cho workflow bệnh viện"""
        import subprocess

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

    @component(
        base_image="python:3.10-slim",
        packages_to_install=[
            "numpy==1.26.3"
        ]
    )
    def hospital_report_generator_op(
        patient_results: List[Dict[str, Any]],
        output_dir: str
    ) -> Dict[str, Any]:
        """Tạo báo cáo tổng kết bệnh viện"""
        import json
        from pathlib import Path
        from datetime import datetime

        # Tạo báo cáo
        report = {
            "hospital_report": {
                "scan_date": "weekly_scan",
                "report_generated": datetime.now().isoformat(),
                "total_patients": len(patient_results),
                "successful": sum(1 for r in patient_results if r.get("success", False)),
                "pipeline_type": "kubeflow_hospital"
            },
            "patients": patient_results
        }

        # Lưu báo cáo
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        report_file = Path(output_dir) / "hospital_report.json"

        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)

        return {
            "report_file": str(report_file),
            "total_patients": len(patient_results),
            "successful": sum(1 for r in patient_results if r.get("success", False))
        }


def create_hospital_pipeline(
    input_weekly_dir: str = "/mnt/data/hospital_input/weekly_scan",
    output_base_dir: str = "/mnt/data/hospital_output"
):
    """Tạo Kubeflow pipeline cho workflow bệnh viện

    Args:
        input_weekly_dir: Đường dẫn đến folder input chứa dữ liệu tuần
        output_base_dir: Đường dẫn base cho output
    """
    if not KFP_AVAILABLE:
        print("KFP không có sẵn, trả về None")
        return None

    @dsl.pipeline(
        name="hospital-covid-detection-pipeline",
        description="Hospital COVID-19 Detection Pipeline - Weekly Scan Processing"
    )
    def hospital_covid_detection_pipeline():

        # Step 1: Tự động tải dữ liệu bệnh viện
        load_data_task = hospital_data_loader_op(
            input_weekly_dir=input_weekly_dir,
            working_dir="/mnt/data/hospital_working"
        ).set_display_name("Load Hospital Data")

        # Extract patient list from metadata
        with dsl.Condition(load_data_task.outputs['patients'] != '[]'):
            # Process mỗi bệnh nhân (sẽ được Kubeflow xử lý parallel)
            # Đây là pseudo-code cho demonstration
            for i in range(10):  # Max 10 patients parallel
                with dsl.Condition(i < dsl.Length(load_data_task.outputs['patients'])):
                    patient_data = dsl.GetIndex(load_data_task.outputs['patients'], i)

                    # Create working directories for this patient
                    patient_id = patient_data['id']
                    ct_file = patient_data['prepared_ct_file']

                    patient_output_dir = f"{output_base_dir}/{patient_id}"
                    segmentation_dir = f"{patient_output_dir}/segmentation"
                    detection_dir = f"{patient_output_dir}/detection"
                    visualization_dir = f"{patient_output_dir}/visualization"

                    with dsl.TaskGroup(name=f"process_{patient_id}"):

                        # Lung Segmentation
                        lung_segment_task = lung_segmentation_hospital_op(
                            ct_file=ct_file,
                            output_dir=segmentation_dir
                        ).set_display_name(f"Segment Lungs - {patient_id}")

                        # COVID Detection
                        covid_detect_task = covid_detection_hospital_op(
                            input_dir=segmentation_dir,
                            output_dir=detection_dir
                        ).set_display_name(f"Detect COVID - {patient_id}")
                        covid_detect_task.after(lung_segment_task)

                        # Visualization
                        viz_task = visualization_hospital_op(
                            input_dir=detection_dir,
                            output_dir=visualization_dir
                        ).set_display_name(f"Create Visualization - {patient_id}")
                        viz_task.after(covid_detect_task)

            # Generate hospital report
            report_task = hospital_report_generator_op(
                patient_results=load_data_task.outputs['patients'],
                output_dir=output_base_dir
            ).set_display_name("Generate Hospital Report")

            # Report depends on all patient processing
            # Note: In real implementation, you'd collect results properly

    return hospital_covid_detection_pipeline


def compile_hospital_pipeline():
    """Compile hospital pipeline và lưu YAML"""
    if not KFP_AVAILABLE:
        print("KFP không có sẵn, tạo mock pipeline structure")
        mock_hospital_pipeline = {
            "pipeline": {
                "name": "hospital-covid-detection-pipeline",
                "description": "Hospital COVID-19 Detection Pipeline - Weekly Scan Processing",
                "workflow": [
                    "load_hospital_data",
                    "process_patients_parallel",
                    "generate_hospital_report"
                ],
                "input_structure": "hospital_input/weekly_scan/PATIENT_ID/*.nii.gz",
                "output_structure": "hospital_output/PATIENT_ID/covid_visualization.png"
            }
        }

        with open("hospital_covid_detection_weekly.yaml", "w") as f:
            f.write("# Hospital Pipeline YAML - KFP not available\n")
            f.write("# Mock structure for demonstration\n")

        print("Mock hospital pipeline created: hospital_covid_detection_weekly.yaml")
        return

    # Create pipeline
    pipeline_func = create_hospital_pipeline()

    # Compile pipeline
    kfp.compiler.Compiler().compile(
        pipeline_func,
        "hospital_covid_detection_weekly.yaml"
    )

    print("Hospital pipeline compiled to: hospital_covid_detection_weekly.yaml")


def create_hospital_deployment_config():
    """Tạo cấu hình deployment cho bệnh viện"""

    deployment_config = {
        "hospital_pipeline_config": {
            "name": "hospital-covid-detection-weekly",
            "description": "Weekly COVID-19 detection pipeline for hospital",
            "input_structure": {
                "weekly_scan_folder": "/mnt/data/hospital_input/weekly_scan",
                "supported_formats": [
                    "weekly_scan/PATIENT001/imaging.nii.gz",
                    "weekly_scan/PATIENT001/CT_001.nii.gz",
                    "weekly_scan/*.nii.gz"
                ]
            },
            "output_structure": {
                "base_folder": "/mnt/data/hospital_output",
                "patient_folders": "hospital_output/PATIENT_ID/",
                "visualization": "hospital_output/PATIENT_ID/covid_visualization.png",
                "results": "hospital_output/PATIENT_ID/covid_results.json",
                "hospital_report": "hospital_output/hospital_report.json"
            },
            "workflow": {
                "auto_discover_patients": True,
                "parallel_processing": True,
                "max_concurrent_patients": 10,
                "timeout_per_patient": "10 minutes"
            },
            "components": [
                {
                    "name": "load_data",
                    "description": "Tự động phát hiện và tải dữ liệu bệnh nhân",
                    "container": "covid-hospital-pipeline:latest"
                },
                {
                    "name": "lung_segmentation",
                    "description": "Phân đoạn phổi với LungMask R231",
                    "container": "covid-hospital-pipeline:latest"
                },
                {
                    "name": "covid_detection",
                    "description": "Phát hiện COVID với rule-based + MONAI",
                    "container": "covid-hospital-pipeline:latest"
                },
                {
                    "name": "visualization",
                    "description": "Tạo visualize y khoa 2x3 grid",
                    "container": "covid-hospital-pipeline:latest"
                },
                {
                    "name": "hospital_report",
                    "description": "Tạo báo cáo tổng kết bệnh viện",
                    "container": "covid-hospital-pipeline:latest"
                }
            ]
        },
        "docker_build": {
            "image_name": "covid-hospital-pipeline",
            "dockerfile": "config/Dockerfile",
            "context": "."
        },
        "kubeflow_deployment": {
            "namespace": "hospital-covid",
            "pipeline_name": "hospital-covid-weekly",
            "schedule": "weekly",  # Có thể chạy hàng tuần
            "resources": {
                "cpu_limit": "2",
                "memory_limit": "4Gi",
                "gpu_limit": "0"  # CPU-only cho reliability
            }
        }
    }

    # Save deployment config
    with open("hospital_deployment_config.json", "w") as f:
        json.dump(deployment_config, f, indent=2)

    print("Hospital deployment configuration saved to: hospital_deployment_config.json")


if __name__ == "__main__":
    # Create hospital deployment configuration
    create_hospital_deployment_config()

    # Compile hospital pipeline
    compile_hospital_pipeline()

    print("\n" + "="*70)
    print("HOSPITAL COVID-19 DETECTION PIPELINE - WEEKLY SCAN")
    print("="*70)
    print("Pipeline đã được tạo cho môi trường bệnh viện!")
    print("\nCấu trúc Input:")
    print("  hospital_input/weekly_scan/")
    print("  ├── PATIENT001/imaging.nii.gz")
    print("  ├── PATIENT002/imaging.nii.gz")
    print("  └── ...")
    print("\nCấu trúc Output:")
    print("  hospital_output/")
    print("  ├── PATIENT001/covid_visualization.png")
    print("  ├── PATIENT002/covid_visualization.png")
    print("  └── hospital_report.json")
    print("\nFiles tạo ra:")
    print("  - hospital_covid_detection_weekly.yaml")
    print("  - hospital_deployment_config.json")
    print("\nNext steps:")
    print("  1. docker build -t covid-hospital-pipeline:latest -f config/Dockerfile .")
    print("  2. Upload to container registry")
    print("  3. Deploy to Kubeflow cluster")
    print("  4. Bác sĩ chạy pipeline hàng tuần")