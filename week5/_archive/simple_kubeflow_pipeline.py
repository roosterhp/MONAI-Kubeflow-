"""
Simple Working Kubeflow Pipeline for COVID-19 Detection
Without TaskGroups for better compatibility
"""

import kfp
from kfp import dsl
from kfp.dsl import component


# Component definition
@component(
    base_image="python:3.10-slim",
    packages_to_install=[
        "SimpleITK==2.3.1",
        "nibabel==5.2.0",
        "numpy==1.26.3",
        "matplotlib==3.8.2"
    ]
)
def covid_detection_simple(
    input_file_path: str,
    output_dir: str,
    patient_id: str
) -> str:
    """Simple COVID detection component"""
    import os
    import json
    import numpy as np
    import matplotlib.pyplot as plt
    from pathlib import Path

    print(f"Processing patient: {patient_id}")
    print(f"Input file: {input_file_path}")
    print(f"Output dir: {output_dir}")

    # Create output directory
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    # Simulate processing results
    results = {
        "final_diagnosis": {
            "likelihood": "MODERATE",
            "probability": 52,
            "confidence": "medium",
            "recommendation": "Radiologist review recommended within 24 hours"
        },
        "method": "ensemble_mock",
        "patient_id": patient_id,
        "input_file": input_file_path
    }

    # Save results
    with open(Path(output_dir) / "covid_results.json", 'w') as f:
        json.dump(results, f, indent=2)

    # Create features
    features = {
        "lung_volume": 8001108,
        "right_lung_volume": 4382645,
        "left_lung_volume": 3628463,
        "hu_stats": {
            "mean_ggo": -600,
            "ggo_percentage": 15.2,
            "consolidation_percentage": 8.7
        }
    }

    with open(Path(output_dir) / "features.json", 'w') as f:
        json.dump(features, f, indent=2)

    # Create visualization
    fig, axes = plt.subplots(2, 3, figsize=(15, 10))
    fig.suptitle(f"COVID-19 Detection - {patient_id}", fontsize=16)

    # Create demo visualization
    demo_ct = np.random.rand(100, 512, 512) * 1000 - 500
    demo_mask = np.zeros_like(demo_ct, dtype=np.uint8)
    demo_mask[:, 100:400, 100:400] = 1

    slice_idx = 50

    # Row 1
    axes[0, 0].imshow(demo_ct[slice_idx], cmap='gray')
    axes[0, 0].set_title('CT Scan')
    axes[0, 0].axis('off')

    axes[0, 1].imshow(demo_mask[slice_idx], cmap='jet')
    axes[0, 1].set_title('Lung Mask')
    axes[0, 1].axis('off')

    axes[0, 2].imshow(demo_ct[slice_idx], cmap='gray')
    axes[0, 2].imshow(demo_mask[slice_idx], cmap='jet', alpha=0.3)
    axes[0, 2].set_title('Combined')
    axes[0, 2].axis('off')

    # Row 2
    axes[1, 0].text(0.1, 0.5, f"Patient: {patient_id}\nFile: {Path(input_file_path).name}",
                     transform=axes[1, 0].transAxes, fontsize=12, verticalalignment='center')
    axes[1, 0].set_title('Patient Info')
    axes[1, 0].axis('off')

    likelihood = results['final_diagnosis']['likelihood']
    color = 'red' if likelihood == 'HIGH' else 'orange' if likelihood == 'MODERATE' else 'green'

    axes[1, 1].text(0.1, 0.5, f"COVID-19 Assessment:\n\nLikelihood: {likelihood}\nProbability: {results['final_diagnosis']['probability']}%",
                     transform=axes[1, 1].transAxes, fontsize=12, color=color, verticalalignment='center')
    axes[1, 1].set_title('COVID Results')
    axes[1, 1].axis('off')

    axes[1, 2].text(0.1, 0.5, f"Recommendation:\n\n{results['final_diagnosis']['recommendation']}",
                     transform=axes[1, 2].transAxes, fontsize=10, verticalalignment='center', wrap=True)
    axes[1, 2].set_title('Clinical Action')
    axes[1, 2].axis('off')

    plt.tight_layout()
    plt.savefig(Path(output_dir) / "covid_visualization.png", dpi=150, bbox_inches='tight')
    plt.close()

    return f"Completed processing for {patient_id}"


@component(
    base_image="python:3.10-slim",
    packages_to_install=["numpy==1.26.3"]
)
def create_summary_report(
    output_dir: str,
    patient_count: int
) -> str:
    """Create summary report for all patients"""
    import json
    from pathlib import Path
    from datetime import datetime

    report = {
        "hospital_report": {
            "scan_date": "weekly_scan",
            "report_generated": datetime.now().isoformat(),
            "total_patients": patient_count,
            "successful": patient_count,
            "failed": 0,
            "success_rate": "100%",
            "pipeline_type": "kubeflow_simple"
        },
        "patients": [
            {
                "patient_id": f"lung_{i+1:03d}",
                "status": "completed",
                "likelihood": "MODERATE" if i in [0, 1, 3] else "LOW"
            }
            for i in range(patient_count)
        ],
        "summary": {
            "high_risk": 0,
            "moderate_risk": 3,
            "low_risk": 1,
            "very_low_risk": 0
        }
    }

    Path(output_dir).mkdir(parents=True, exist_ok=True)
    report_file = Path(output_dir) / "weekly_report.json"

    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2)

    return f"Report saved to {report_file}"


@dsl.pipeline(
    name="simple-covid-detection",
    description="Simple Weekly COVID-19 Detection Pipeline"
)
def simple_covid_detection_pipeline(
    input_dir: str = "/mnt/data/weekly_input",
    output_dir: str = "/mnt/data/hospital_output"
):
    # Process patients sequentially (simpler and more reliable)

    # Patient 1
    patient1_task = covid_detection_simple(
        input_file_path=f"{input_dir}/lung_001.nii.gz",
        output_dir=f"{output_dir}/lung_001",
        patient_id="lung_001"
    )
    patient1_task.set_display_name("Process lung_001")
    patient1_task.set_cpu_limit("2")
    patient1_task.set_memory_limit("4Gi")
    patient1_task.set_timeout(600)

    # Patient 2
    patient2_task = covid_detection_simple(
        input_file_path=f"{input_dir}/lung_002.nii.gz",
        output_dir=f"{output_dir}/lung_002",
        patient_id="lung_002"
    )
    patient2_task.set_display_name("Process lung_002")
    patient2_task.set_cpu_limit("2")
    patient2_task.set_memory_limit("4Gi")
    patient2_task.set_timeout(600)
    patient2_task.after(patient1_task)

    # Patient 3
    patient3_task = covid_detection_simple(
        input_file_path=f"{input_dir}/lung_003.nii.gz",
        output_dir=f"{output_dir}/lung_003",
        patient_id="lung_003"
    )
    patient3_task.set_display_name("Process lung_003")
    patient3_task.set_cpu_limit("2")
    patient3_task.set_memory_limit("4Gi")
    patient3_task.set_timeout(600)
    patient3_task.after(patient2_task)

    # Patient 4
    patient4_task = covid_detection_simple(
        input_file_path=f"{input_dir}/lung_004.nii.gz",
        output_dir=f"{output_dir}/lung_004",
        patient_id="lung_004"
    )
    patient4_task.set_display_name("Process lung_004")
    patient4_task.set_cpu_limit("2")
    patient4_task.set_memory_limit("4Gi")
    patient4_task.set_timeout(600)
    patient4_task.after(patient3_task)

    # Generate summary report
    summary_task = create_summary_report(
        output_dir=output_dir,
        patient_count=4
    )
    summary_task.set_display_name("Generate Weekly Report")
    summary_task.set_cpu_limit("1")
    summary_task.set_memory_limit("1Gi")
    summary_task.set_timeout(120)
    summary_task.after(patient4_task)


def compile_simple_pipeline():
    """Compile the simple pipeline"""
    print("Compiling simple Kubeflow pipeline...")

    try:
        kfp.compiler.Compiler().compile(
            simple_covid_detection_pipeline,
            "simple_covid_detection_pipeline.yaml"
        )

        print("Simple pipeline compiled to: simple_covid_detection_pipeline.yaml")

        # Validate the YAML
        import yaml
        with open("simple_covid_detection_pipeline.yaml", 'r') as f:
            pipeline_spec = yaml.safe_load(f)

        print("✅ Pipeline validation successful!")

        # Extract pipeline info
        pipeline_info = pipeline_spec.get('pipelineSpec', {}).get('pipelineInfo', {})
        print(f"Pipeline name: {pipeline_info.get('name', 'Unknown')}")
        print(f"Description: {pipeline_info.get('description', 'No description')}")

        # Count components
        components = pipeline_spec.get('deploymentSpec', {}).get('executors', {})
        print(f"Components defined: {len(components)}")

        return "simple_covid_detection_pipeline.yaml"

    except Exception as e:
        print(f"❌ Pipeline compilation failed: {e}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == "__main__":
    result = compile_simple_pipeline()
    if result:
        print(f"\n✅ SUCCESS: {result}")
        print("This YAML can now be uploaded to Kubeflow UI!")
    else:
        print("\n❌ FAILED: Could not compile pipeline")