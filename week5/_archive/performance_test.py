#!/usr/bin/env python3
"""
Performance Test: Measure memory usage and execution time
Tests performance metrics for all components
"""

import os
import sys
import json
import time
import psutil
import shutil
from pathlib import Path

def get_memory_usage():
    """Get current memory usage in MB"""
    process = psutil.Process(os.getpid())
    return process.memory_info().rss / 1024 / 1024

def measure_component_performance(component_func, *args, **kwargs):
    """Measure performance of a component function"""
    # Initial memory
    initial_memory = get_memory_usage()

    # Start timing
    start_time = time.time()

    # Run component
    result = component_func(*args, **kwargs)

    # End timing
    end_time = time.time()
    execution_time = end_time - start_time

    # Final memory
    final_memory = get_memory_usage()
    memory_delta = final_memory - initial_memory
    peak_memory = final_memory

    return {
        "result": result,
        "execution_time": execution_time,
        "memory_delta": memory_delta,
        "peak_memory": peak_memory,
        "initial_memory": initial_memory
    }

def run_performance_test():
    """Run performance tests on all components"""

    print("="*80)
    print("PERFORMANCE TESTS")
    print("="*80)

    # Test configuration
    test_patient = "data/hospital_working/lung_001.nii/imaging.nii.gz"
    working_dir = "data/performance_working"
    output_dir = "data/performance_output"
    metadata_file = "data/performance_metadata.json"

    # Clean up previous tests
    for dir_path in [working_dir, output_dir]:
        if Path(dir_path).exists():
            shutil.rmtree(dir_path)

    performance_results = {}

    try:
        # Test 1: Load Data Performance
        print("\n[TEST] Load Data Performance")
        print("-" * 50)

        start_memory = get_memory_usage()
        start_time = time.time()

        result = os.system(f"python components/load_data_fixed.py data/weekly_input {working_dir} {metadata_file}")

        load_data_time = time.time() - start_time
        load_data_memory = get_memory_usage() - start_memory

        performance_results["load_data"] = {
            "execution_time": load_data_time,
            "memory_usage": load_data_memory,
            "success": result == 0
        }

        print(f"  Execution time: {load_data_time:.2f}s")
        print(f"  Memory usage: {load_data_memory:.1f} MB")
        print(f"  Success: {result == 0}")

        # Test 2: Lung Segmentation Performance
        print("\n[TEST] Lung Segmentation Performance")
        print("-" * 50)

        segmentation_dir = f"{output_dir}/segmentation"

        start_memory = get_memory_usage()
        start_time = time.time()

        result = os.system(f"python components/lung_segment.py {test_patient} {segmentation_dir}")

        segmentation_time = time.time() - start_time
        segmentation_memory = get_memory_usage() - start_memory

        performance_results["lung_segmentation"] = {
            "execution_time": segmentation_time,
            "memory_usage": segmentation_memory,
            "success": result == 0
        }

        print(f"  Execution time: {segmentation_time:.2f}s")
        print(f"  Memory usage: {segmentation_memory:.1f} MB")
        print(f"  Success: {result == 0}")

        # Test 3: COVID Detection Performance
        print("\n[TEST] COVID Detection Performance")
        print("-" * 50)

        detection_dir = f"{output_dir}/detection"

        start_memory = get_memory_usage()
        start_time = time.time()

        result = os.system(f"python components/covid_detect.py {segmentation_dir} {detection_dir}")

        detection_time = time.time() - start_time
        detection_memory = get_memory_usage() - start_memory

        performance_results["covid_detection"] = {
            "execution_time": detection_time,
            "memory_usage": detection_memory,
            "success": result == 0
        }

        print(f"  Execution time: {detection_time:.2f}s")
        print(f"  Memory usage: {detection_memory:.1f} MB")
        print(f"  Success: {result == 0}")

        # Test 4: Visualization Performance
        print("\n[TEST] Visualization Performance")
        print("-" * 50)

        visualization_dir = f"{output_dir}/visualization"

        start_memory = get_memory_usage()
        start_time = time.time()

        result = os.system(f"python components/visualize.py {detection_dir} {visualization_dir}")

        visualization_time = time.time() - start_time
        visualization_memory = get_memory_usage() - start_memory

        performance_results["visualization"] = {
            "execution_time": visualization_time,
            "memory_usage": visualization_memory,
            "success": result == 0
        }

        print(f"  Execution time: {visualization_time:.2f}s")
        print(f"  Memory usage: {visualization_memory:.1f} MB")
        print(f"  Success: {result == 0}")

        # Test 5: File Size Analysis
        print("\n[TEST] File Size Analysis")
        print("-" * 50)

        file_sizes = {}
        total_size = 0

        # Check input file size
        if Path(test_patient).exists():
            input_size = Path(test_patient).stat().st_size / 1024 / 1024
            file_sizes["input_nifti"] = input_size
            total_size += input_size
            print(f"  Input NIfTI: {input_size:.1f} MB")

        # Check output files
        output_files = [
            ("lung_mask", f"{segmentation_dir}/lung_mask.nii.gz"),
            ("ct_array", f"{segmentation_dir}/ct_array.npy"),
            ("covid_results", f"{detection_dir}/covid_results.json"),
            ("features", f"{detection_dir}/features.json"),
            ("visualization", f"{visualization_dir}/covid_visualization.png")
        ]

        for name, path in output_files:
            if Path(path).exists():
                size = Path(path).stat().st_size / 1024 / 1024
                file_sizes[name] = size
                total_size += size
                print(f"  {name}: {size:.1f} MB")

        file_sizes["total_output"] = total_size
        print(f"  Total output: {total_size:.1f} MB")

        # Test 6: Throughput Analysis
        print("\n[TEST] Throughput Analysis")
        print("-" * 50)

        # Calculate throughput metrics
        total_time = sum(perf["execution_time"] for perf in performance_results.values())
        avg_time_per_patient = total_time

        # Assuming 1 patient per hour in clinical setting
        patients_per_hour = 3600 / avg_time_per_patient if avg_time_per_patient > 0 else 0

        throughput_metrics = {
            "total_pipeline_time": total_time,
            "avg_time_per_patient": avg_time_per_patient,
            "patients_per_hour": patients_per_hour,
            "memory_efficiency": file_sizes.get("total_output", 0) / 1024  # GB per patient
        }

        print(f"  Total pipeline time: {total_time:.2f}s")
        print(f"  Avg time per patient: {avg_time_per_patient:.2f}s")
        print(f"  Patients per hour: {patients_per_hour:.1f}")
        print(f"  Memory efficiency: {throughput_metrics['memory_efficiency']:.2f} GB/patient")

        # Complete performance report
        performance_report = {
            "test_timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "system_info": {
                "python_version": sys.version,
                "platform": sys.platform,
                "cpu_count": psutil.cpu_count(),
                "total_memory": psutil.virtual_memory().total / 1024 / 1024 / 1024
            },
            "component_performance": performance_results,
            "file_sizes": file_sizes,
            "throughput_metrics": throughput_metrics
        }

        # Save performance report
        report_file = Path("data/performance_report.json")
        with open(report_file, 'w') as f:
            json.dump(performance_report, f, indent=2)

        print(f"\n[OK] Performance report saved: {report_file}")

        # Summary
        print(f"\n{'='*60}")
        print("PERFORMANCE TEST SUMMARY")
        print(f"{'='*60}")

        for component, metrics in performance_results.items():
            print(f"{component.upper()}:")
            print(f"  Time: {metrics['execution_time']:.2f}s")
            print(f"  Memory: {metrics['memory_usage']:.1f} MB")
            print(f"  Status: {'SUCCESS' if metrics['success'] else 'FAILED'}")

        print(f"\nPIPELINE THROUGHPUT:")
        print(f"  Total time: {total_time:.2f}s per patient")
        print(f"  Throughput: {patients_per_hour:.1f} patients/hour")
        print(f"  Memory efficiency: {throughput_metrics['memory_efficiency']:.2f} GB/patient")

        # Performance recommendations
        print(f"\nPERFORMANCE RECOMMENDATIONS:")
        if total_time > 300:  # > 5 minutes
            print("  - Pipeline is slow, consider GPU acceleration")
        if throughput_metrics['memory_efficiency'] > 2:  # > 2 GB per patient
            print("  - High memory usage, consider data compression")
        if patients_per_hour < 10:
            print("  - Low throughput, optimize for clinical workflow")

        return 0

    except Exception as e:
        print(f"[ERROR] Performance test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(run_performance_test())