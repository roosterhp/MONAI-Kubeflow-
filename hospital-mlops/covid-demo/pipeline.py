"""
Kubeflow Pipeline: COVID-19 Detection with Fine-tuning
Process patients through: load_data -> lung_segment -> covid_detect -> visualize -> finetune
"""

from kfp import dsl
from kfp import compiler
from kubernetes.client import V1Volume, V1PersistentVolumeClaimVolumeSource

# Base image (to be built from Dockerfile)
BASE_IMAGE = "covid-pipeline:v1"

# Patient IDs to process
PATIENTS = ["lung_001", "lung_002", "lung_003", "lung_004"]

# Batch ID for fine-tuning
BATCH_ID = "week_current"


@dsl.container_component
def load_data_component(patient_id: str):
    """Load CT scan from test dataset"""
    return dsl.ContainerSpec(
        image=BASE_IMAGE,
        command=["python", "/app/components/load_data.py"],
        args=[patient_id]
    )


@dsl.container_component
def lung_segment_component(patient_id: str):
    """Segment lungs using LungMask"""
    return dsl.ContainerSpec(
        image=BASE_IMAGE,
        command=["python", "/app/components/lung_segment.py"],
        args=[patient_id]
    )


@dsl.container_component
def covid_detect_component(patient_id: str):
    """Detect COVID-19 using enhanced MONAI + rule-based ensemble"""
    return dsl.ContainerSpec(
        image=BASE_IMAGE,
        command=["python", "/app/components/covid_detect_enhanced.py"],
        args=[patient_id]
    )


@dsl.container_component
def visualize_component(patient_id: str):
    """Create COVID-19 detection visualization"""
    return dsl.ContainerSpec(
        image=BASE_IMAGE,
        command=["python", "/app/components/visualize.py"],
        args=[patient_id]
    )


@dsl.container_component
def finetune_component(batch_id: str, patient_list: str):
    """Fine-tune COVID model on processed patients"""
    return dsl.ContainerSpec(
        image=BASE_IMAGE,
        command=["python", "/app/components/finetune.py"],
        args=[batch_id] + patient_list.split(',')
    )


@dsl.pipeline(
    name="Enhanced COVID-19 Detection Pipeline",
    description="Enhanced COVID-19 CT detection with MONAI + Rule-based Ensemble: load_data -> lung_segment -> covid_detect_enhanced -> visualize -> finetune"
)
def covid_pipeline():
    """Main pipeline: Process all patients in PARALLEL, then fine-tune"""

    # Define PVC volume
    data_volume = V1Volume(
        name='data-volume',
        persistent_volume_claim=V1PersistentVolumeClaimVolumeSource(
            claim_name='covid-data-pvc'
        )
    )

    viz_tasks = []  # Track visualization tasks for fine-tuning dependency

    # Process all patients in parallel
    for patient_id in PATIENTS:
        print(f"Setting up pipeline for {patient_id}")

        # Step 1: Load Data
        load_task = load_data_component(patient_id=patient_id)
        load_task.set_caching_options(False)
        load_task.add_pvolumes({'/mnt/data': data_volume})

        # Step 2: Lung Segmentation (depends on load_data)
        segment_task = lung_segment_component(patient_id=patient_id)
        segment_task.after(load_task)
        segment_task.set_caching_options(False)
        segment_task.add_pvolumes({'/mnt/data': data_volume})

        # Step 3: COVID Detection (depends on lung_segment)
        detect_task = covid_detect_component(patient_id=patient_id)
        detect_task.after(segment_task)
        detect_task.set_caching_options(False)
        detect_task.add_pvolumes({'/mnt/data': data_volume})

        # Step 4: Visualization (depends on covid_detect)
        viz_task = visualize_component(patient_id=patient_id)
        viz_task.after(detect_task)
        viz_task.set_caching_options(False)
        viz_task.add_pvolumes({'/mnt/data': data_volume})

        viz_tasks.append(viz_task)

    # Step 5: Fine-tune model (depends on ALL visualizations complete)
    patient_list_str = ','.join(PATIENTS)
    finetune_task = finetune_component(
        batch_id=BATCH_ID,
        patient_list=patient_list_str
    )

    # Fine-tuning depends on all viz tasks
    for viz_task in viz_tasks:
        finetune_task.after(viz_task)

    finetune_task.set_caching_options(False)
    finetune_task.add_pvolumes({'/mnt/data': data_volume})


if __name__ == "__main__":
    # Compile pipeline to YAML
    compiler.Compiler().compile(
        pipeline_func=covid_pipeline,
        package_path="covid_pipeline.yaml"
    )

    print("=" * 60)
    print("Pipeline compiled successfully!")
    print("Output: covid_pipeline.yaml")
    print("=" * 60)
    print("\nPipeline structure:")
    print("  1. Process patients in parallel:")
    print(f"     - {len(PATIENTS)} patients: {', '.join(PATIENTS)}")
    print("     - Each: load_data -> lung_segment -> covid_detect -> visualize")
    print("  2. Fine-tune model after all patients processed")
    print("\nNext steps:")
    print("1. Build Docker image:")
    print("   eval $(minikube docker-env)")
    print("   docker build -t covid-pipeline:v1 .")
    print("\n2. Deploy PersistentVolume:")
    print("   kubectl apply -f kubernetes/pv.yaml")
    print("   kubectl apply -f kubernetes/pvc.yaml")
    print("\n3. Upload covid_pipeline.yaml to Kubeflow UI")
    print("\nOutputs:")
    print("  - Per patient: /mnt/data/covid_outputs/week_current/{patient_id}/")
    print("    - covid_results.json")
    print("    - full_comparison_{patient_id}.png")
    print("  - Fine-tuned model: /mnt/data/covid_outputs/finetuned_models/")
    print("    - finetuned_model_week_current.pth")
    print("=" * 60)
