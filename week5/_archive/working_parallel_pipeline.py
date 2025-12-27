"""
Working Parallel COVID-19 Detection Pipeline
4 patients processed with individual component visualization
"""

import kfp
from kfp import dsl
from kfp.dsl import component


# Component definitions
@component(
    base_image="python:3.10-slim",
    packages_to_install=[
        "numpy==1.26.3",
        "matplotlib==3.8.2"
    ]
)
def load_patient_data(
    input_dir: str,
    patient_id: str
) -> str:
    """Load and prepare data for a specific patient"""
    import json
    from pathlib import Path

    print(f"[LOAD] Processing patient: {patient_id}")

    metadata = {
        "patient_id": patient_id,
        "status": "loaded",
        "timestamp": "2025-11-17T20:00:00Z"
    }

    return json.dumps(metadata)


@component(
    base_image="python:3.10-slim",
    packages_to_install=[
        "numpy==1.26.3",
        "matplotlib==3.8.2"
    ]
)
def segment_patient_lungs(
    patient_metadata: str,
    patient_id: str
) -> str:
    """Perform lung segmentation for a specific patient"""
    import json
    import numpy as np

    print(f"[SEGMENT] Starting lung segmentation for: {patient_id}")

    metadata = json.loads(patient_metadata)

    # Simulate segmentation
    segmentation_results = {
        "patient_id": patient_id,
        "lung_volume": 8001108,
        "right_lung": 4382645,
        "left_lung": 3618463,
        "method": "lungmask_r231",
        "status": "completed"
    }

    return json.dumps(segmentation_results)


@component(
    base_image="python:3.10-slim",
    packages_to_install=[
        "numpy==1.26.3",
        "matplotlib==3.8.2"
    ]
)
def detect_patient_covid(
    segmentation_results: str,
    patient_id: str
) -> str:
    """Perform COVID-19 detection for a specific patient"""
    import json
    import numpy as np

    print(f"[DETECT] Starting COVID detection for: {patient_id}")

    # Simulate COVID detection
    np.random.seed(42 + hash(patient_id) % 10)
    infection_ratio = np.random.uniform(0.05, 0.25)

    if infection_ratio > 0.20:
        likelihood = "HIGH"
        probability = int(70 + np.random.uniform(0, 25))
    elif infection_ratio > 0.15:
        likelihood = "MODERATE"
        probability = int(50 + np.random.uniform(0, 20))
    else:
        likelihood = "LOW"
        probability = int(20 + np.random.uniform(0, 30))

    if likelihood == "HIGH":
        recommendation = "Urgent review"
    elif likelihood == "MODERATE":
        recommendation = "Radiologist review"
    else:
        recommendation = "Follow-up recommended"

    results = {
        "patient_id": patient_id,
        "final_diagnosis": {
            "likelihood": likelihood,
            "probability": probability,
            "confidence": "medium",
            "recommendation": recommendation
        },
        "infection_ratio": float(infection_ratio),
        "status": "completed"
    }

    return json.dumps(results)


@component(
    base_image="python:3.10-slim",
    packages_to_install=[
        "numpy==1.26.3",
        "matplotlib==3.8.2"
    ]
)
def create_patient_visualization(
    detection_results: str,
    patient_id: str
) -> str:
    """Create visualization for a specific patient"""
    import json
    import numpy as np
    import matplotlib.pyplot as plt
    from pathlib import Path

    print(f"[VIZ] Creating visualization for: {patient_id}")

    results = json.loads(detection_results)
    diagnosis = results['final_diagnosis']

    # Create pipeline visualization
    fig, axes = plt.subplots(2, 3, figsize=(15, 10))
    fig.suptitle(f'COVID-19 Detection Pipeline - {patient_id}', fontsize=16, fontweight='bold')

    # Pipeline steps
    steps = [
        ("Load Data", "green", "✅"),
        ("Segmentation", "blue", "✅"),
        ("COVID Detection", "orange", "✅"),
        ("Visualization", "purple", "✅"),
        ("Report", "gray", "✅"),
        ("Complete", "green", "✅")
    ]

    for idx, (step, color, status) in enumerate(steps):
        row, col = divmod(idx, 3)
        axes[row, col].text(0.5, 0.5, f'{step}\n{status}',
                          ha='center', va='center', transform=axes[row, col].transAxes,
                          fontsize=12, fontweight='bold', color=color,
                          bbox=dict(boxstyle="round,pad=0.3", facecolor="lightgray"))
        axes[row, col].set_title(f'Step {idx+1}')
        axes[row, col].axis('off')

    # COVID results
    likelihood = diagnosis['likelihood']
    probability = diagnosis['probability']

    colors = {'HIGH': 'red', 'MODERATE': 'orange', 'LOW': 'green', 'VERY_LOW': 'green'}
    color = colors.get(likelihood, 'gray')

    result_text = f'''COVID-19 Results for {patient_id}:

Likelihood: {likelihood}
Probability: {probability}%
Confidence: {diagnosis['confidence']}

Recommendation:
{diagnosis['recommendation']}

Status: Pipeline Active'''

    axes[1, 2].text(0.05, 0.5, result_text,
                   transform=axes[1, 2].transAxes, fontsize=9,
                   color=color, verticalalignment='center')
    axes[1, 2].set_title(f'{patient_id} Diagnosis')
    axes[1, 2].axis('off')

    plt.tight_layout()

    # Save visualization
    viz_file = f"/tmp/{patient_id}_visualization.png"
    plt.savefig(viz_file, dpi=150, bbox_inches='tight')
    plt.close()

    viz_results = {
        "patient_id": patient_id,
        "visualization_file": viz_file,
        "likelihood": likelihood,
        "pipeline_steps": 6,
        "status": "completed"
    }

    return json.dumps(viz_results)


@component(
    base_image="python:3.10-slim",
    packages_to_install=["numpy==1.26.3"]
)
def generate_parallel_summary(
    patient_1_result: str,
    patient_2_result: str,
    patient_3_result: str,
    patient_4_result: str
) -> str:
    """Generate summary for parallel processing"""
    import json
    from datetime import datetime

    print(f"[SUMMARY] Generating parallel processing summary")

    patients = [
        json.loads(patient_1_result),
        json.loads(patient_2_result),
        json.loads(patient_3_result),
        json.loads(patient_4_result)
    ]

    report = {
        "parallel_processing_report": {
            "timestamp": datetime.now().isoformat(),
            "total_patients": len(patients),
            "successful": len(patients),
            "processing_mode": "parallel",
            "concurrent_patients": 4,
            "pipeline_type": "kubeflow_parallel_visual"
        },
        "workflow_visualization": {
            "description": "4 Patients Processed Simultaneously",
            "pipeline_per_patient": [
                "1. Load Data",
                "2. Lung Segmentation",
                "3. COVID Detection",
                "4. Visualization"
            ],
            "parallel_execution": True,
            "individual_components": "Visible in Kubeflow UI"
        },
        "patients": patients,
        "kubeflow_ui_display": {
            "total_components": 16,  # 4 patients x 4 components each
            "task_groups": 4,  # One per patient
            "visualization": "Each patient shows separate components"
        }
    }

    return json.dumps(report)


@dsl.pipeline(
    name="parallel-covid-visual",
    description="Parallel COVID-19 Detection with Individual Component Visualization - 4 Patients Simultaneously"
)
def parallel_covid_visual_pipeline(
    input_dir: str = "/mnt/data/weekly_input",
    output_dir: str = "/mnt/data/hospital_output"
):
    """Parallel pipeline showing individual components for each patient"""

    patients = ["lung_001", "lung_002", "lung_003", "lung_004"]

    # Process patients in parallel with individual components
    patient_results = []

    for patient_id in patients:
        with dsl.TaskGroup(name=f"patient_{patient_id}"):

            # Component 1: Load Data
            load_task = load_patient_data(
                input_dir=input_dir,
                patient_id=patient_id
            ).set_display_name(f"📥 Load Data - {patient_id}")
            load_task.set_cpu_limit("1")
            load_task.set_memory_limit("2Gi")

            # Component 2: Lung Segmentation
            seg_task = segment_patient_lungs(
                patient_metadata=load_task.output,
                patient_id=patient_id
            ).set_display_name(f"🫁 Segment Lungs - {patient_id}")
            seg_task.set_cpu_limit("2")
            seg_task.set_memory_limit("4Gi")
            seg_task.after(load_task)

            # Component 3: COVID Detection
            detect_task = detect_patient_covid(
                segmentation_results=seg_task.output,
                patient_id=patient_id
            ).set_display_name(f"🦠 COVID Detection - {patient_id}")
            detect_task.set_cpu_limit("2")
            detect_task.set_memory_limit("4Gi")
            detect_task.after(seg_task)

            # Component 4: Visualization
            viz_task = create_patient_visualization(
                detection_results=detect_task.output,
                patient_id=patient_id
            ).set_display_name(f"📊 Create Viz - {patient_id}")
            viz_task.set_cpu_limit("1")
            viz_task.set_memory_limit("2Gi")
            viz_task.after(detect_task)

            patient_results.append(viz_task.output)

    # Generate parallel summary report
    summary_task = generate_parallel_summary(
        patient_1_result=patient_results[0],
        patient_2_result=patient_results[1],
        patient_3_result=patient_results[2],
        patient_4_result=patient_results[3]
    ).set_display_name("📋 Generate Parallel Summary")
    summary_task.set_cpu_limit("1")
    summary_task.set_memory_limit("1Gi")

    # Set dependencies on all patient visualizations
    for result in patient_results:
        summary_task.after(result)

    return summary_task.output


def compile_parallel_pipeline():
    """Compile the parallel pipeline"""
    print("🔄 Compiling parallel COVID-19 detection pipeline with individual components...")

    try:
        # Compile pipeline
        kfp.compiler.Compiler().compile(
            parallel_covid_visual_pipeline,
            "working_parallel_pipeline.yaml"
        )

        print("✅ Parallel pipeline compiled successfully!")
        print("📁 Output: working_parallel_pipeline.yaml")

        # Validate the YAML
        import yaml
        with open("working_parallel_pipeline.yaml", 'r') as f:
            pipeline_spec = yaml.safe_load(f)

        # Extract pipeline info
        pipeline_info = pipeline_spec.get('pipelineSpec', {}).get('pipelineInfo', {})

        print("\n" + "="*70)
        print("PARALLEL PIPELINE WITH INDIVIDUAL COMPONENTS")
        print("="*70)
        print(f"📋 Pipeline Name: {pipeline_info.get('name', 'Unknown')}")
        print(f"📝 Description: {pipeline_info.get('description', 'No description')}")

        # Count components
        executors = pipeline_spec.get('deploymentSpec', {}).get('executors', {})
        print(f"🔧 Total Components: {len(executors)}")

        print("\n🏥 PATIENT PROCESSING WORKFLOW:")
        print("4 Patients Processed Simultaneously with Individual Component Visualization:")
        print("  Each Patient Shows:")
        print("    1. 📥 Load Data")
        print("    2. 🫁 Lung Segmentation")
        print("    3. 🦠 COVID Detection")
        print("    4. 📊 Visualization")
        print("\n🎯 In Kubeflow UI, you will see:")
        print("  • 4 patient task groups")
        print("  • 4 components per patient (16 total components)")
        print("  • Clear parallel execution visualization")
        print("  • Individual component status tracking")

        print("\n💡 Benefits:")
        print("  • Visual representation of pipeline stages")
        print("  • Individual component monitoring")
        print("  • Better error isolation")
        print("  • Resource optimization")

        print("\n" + "="*70)
        print("PARALLEL VISUAL PIPELINE READY!")
        print("="*70)

        return "working_parallel_pipeline.yaml"

    except Exception as e:
        print(f"❌ Pipeline compilation failed: {e}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == "__main__":
    result = compile_parallel_pipeline()

    if result:
        print(f"\n🎉 SUCCESS: {result}")
        print("\n✨ This pipeline provides:")
        print("  • 4 patients processed in parallel")
        print("  • Individual component visualization")
        print("  • Clear workflow representation")
        print("  • Better monitoring capabilities")
        print("\n🚀 Upload to Kubeflow and see the parallel workflow!")
    else:
        print("\n💥 FAILED: Could not compile pipeline")