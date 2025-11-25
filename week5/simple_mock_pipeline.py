"""
Simple Mock Pipeline for Week5
Just a minimal runnable pipeline for demonstration purposes
"""

import time
from datetime import datetime
from pathlib import Path


def mock_data_loading():
    """Mock data loading step"""
    print("\n[Step 1/4] Loading data...")
    time.sleep(0.5)
    print("Data loaded successfully (mock)")
    return {"status": "success", "samples": 4}


def mock_preprocessing():
    """Mock preprocessing step"""
    print("\n[Step 2/4] Preprocessing...")
    time.sleep(0.5)
    print("Preprocessing completed (mock)")
    return {"status": "success", "processed": 4}


def mock_model_inference():
    """Mock model inference step"""
    print("\n[Step 3/4] Running model inference...")
    time.sleep(0.5)
    print("Inference completed (mock)")
    return {"status": "success", "predictions": [0.85, 0.23, 0.67, 0.91]}


def mock_results_generation():
    """Mock results generation step"""
    print("\n[Step 4/4] Generating results...")
    time.sleep(0.5)
    print("Results generated (mock)")
    return {"status": "success", "report": "pipeline_report.json"}


def run_pipeline():
    """Run the simple mock pipeline"""
    print("=" * 60)
    print("SIMPLE MOCK PIPELINE - WEEK5")
    print("=" * 60)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    start_time = time.time()

    try:
        # Run pipeline steps
        data_result = mock_data_loading()
        preprocess_result = mock_preprocessing()
        inference_result = mock_model_inference()
        results = mock_results_generation()

        # Calculate execution time
        elapsed_time = time.time() - start_time

        # Print summary
        print("\n" + "=" * 60)
        print("PIPELINE SUMMARY")
        print("=" * 60)
        print(f"Total samples processed: {data_result['samples']}")
        print(f"Predictions: {inference_result['predictions']}")
        print(f"Execution time: {elapsed_time:.2f}s")
        print(f"Status: SUCCESS")
        print("=" * 60)

        return 0

    except Exception as e:
        print(f"\nPipeline failed: {e}")
        return 1


if __name__ == "__main__":
    exit(run_pipeline())
