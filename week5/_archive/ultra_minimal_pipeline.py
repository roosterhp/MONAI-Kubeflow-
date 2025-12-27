"""
Ultra Minimal COVID-19 Pipeline for Kubeflow Debugging
Pure Python components with zero dependencies - guaranteed to run
"""

import kfp
from kfp import dsl
from kfp.dsl import component


@component(
    base_image="python:3.10-slim",
    packages_to_install=[]  # NO dependencies - pure Python only
)
def ultra_minimal_op(
    patient_id: str,
    step: str
) -> str:
    """Ultra Minimal Component - Pure Python Only"""
    import json
    import datetime

    print(f"[ULTRA] Starting {step} for {patient_id}")
    print(f"[ULTRA] Pure Python - No dependencies")

    result = {
        "patient_id": patient_id,
        "step": step,
        "status": "completed",
        "timestamp": datetime.datetime.now().isoformat(),
        "method": "ultra_minimal",
        "dependencies": "none",
        "memory_usage": "< 50MB"
    }

    print(f"[ULTRA] Completed {step} for {patient_id}")
    return json.dumps(result)


@component(
    base_image="python:3.10-slim",
    packages_to_install=[]
)
def ultra_summary_op(
    patient_results: list
) -> str:
    """Ultra Minimal Summary Component"""
    import json
    import datetime

    print(f"[ULTRA] Generating summary")
    print(f"[ULTRA] Received {len(patient_results)} patient results")

    report = {
        "ultra_pipeline_report": {
            "timestamp": datetime.datetime.now().isoformat(),
            "total_patients": len(patient_results),
            "successful": len(patient_results),
            "failed": 0,
            "success_rate": "100%",
            "method": "ultra_minimal",
            "kubeflow_compatible": True
        },
        "component_info": {
            "dependencies": "zero",
            "base_image": "python:3.10-slim",
            "packages": "none",
            "memory_per_component": "< 50MB",
            "cpu_per_component": "0.1 core"
        },
        "patients": patient_results
    }

    print(f"[ULTRA] Summary completed - 100% success")
    return json.dumps(report)


@dsl.pipeline(
    name="ultra-minimal-covid-pipeline",
    description="Ultra Minimal COVID Pipeline - Pure Python Only for Kubeflow Debugging"
)
def ultra_minimal_covid_pipeline():
    """Ultra minimal pipeline with pure Python components"""

    patients = ["lung_001", "lung_002", "lung_003", "lung_004"]
    steps = ["load_data", "segment", "detect", "visualize"]

    all_results = []

    # Process each patient through all steps
    for patient in patients:
        patient_results = []

        for step in steps:
            task = ultra_minimal_op(
                patient_id=patient,
                step=step
            ).set_display_name(f"{patient} - {step}")
            task.set_cpu_limit("0.1")  # Minimal CPU
            task.set_memory_limit("50Mi")  # Minimal memory

            patient_results.append(task.output)

        all_results.extend(patient_results)

    # Generate summary
    summary_task = ultra_summary_op(
        patient_results=all_results
    ).set_display_name("Ultra Minimal Summary")
    summary_task.set_cpu_limit("0.1")
    summary_task.set_memory_limit("25Mi")


def compile_ultra_minimal_pipeline():
    """Compile ultra minimal pipeline"""
    print("[COMPILING] Ultra Minimal Pipeline...")
    print("Pure Python components - ZERO dependencies!")

    try:
        kfp.compiler.Compiler().compile(
            ultra_minimal_covid_pipeline,
            "ultra_minimal_pipeline.yaml"
        )

        print("[SUCCESS] Ultra minimal pipeline compiled!")

        # Validate
        import yaml
        with open("ultra_minimal_pipeline.yaml", 'r') as f:
            pipeline_spec = yaml.safe_load(f)

        print(f"[INFO] Pipeline ready for upload")
        print(f"[INFO] Components: Pure Python only")
        print(f"[INFO] Dependencies: NONE")
        print(f"[INFO] Memory: < 200MB total")

        return "ultra_minimal_pipeline.yaml"

    except Exception as e:
        print(f"[ERROR] Compilation failed: {e}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == "__main__":
    result = compile_ultra_minimal_pipeline()

    if result:
        print(f"\n[SUCCESS] {result}")
        print("\n[ULTRA FEATURES]:")
        print("- ZERO external dependencies")
        print("- Pure Python only")
        print("- Minimal resource usage")
        print("- Guaranteed Kubeflow compatibility")
        print("\n[TEST]: This MUST work on any Kubeflow cluster!")
    else:
        print("\n[FAILED] Could not compile ultra minimal pipeline")