"""
Local Test Script: Test pipeline components before deploying to Kubeflow
Run this to verify components work correctly
"""

import sys
import os
from pathlib import Path

# Add components to path
sys.path.insert(0, str(Path(__file__).parent / "components"))

# Import components
from load_data import load_data
from lung_segment import lung_segment
from covid_detect import covid_detect
from visualize import create_visualization


def test_pipeline(patient_id="lung_001"):
    """Test the full pipeline locally"""

    print("=" * 70)
    print("LOCAL PIPELINE TEST")
    print("=" * 70)
    print(f"\nTesting with patient: {patient_id}")
    print("\nNOTE: This requires:")
    print(f"  - Input data at: /mnt/data/test_data/Task06_Lung/imagesTr/{patient_id}.nii.gz")
    print("  - Or update paths in components to point to your local data")
    print()

    results = {}

    # Test 1: Load Data
    print("\n" + "=" * 70)
    print("TEST 1: LOAD DATA")
    print("=" * 70)
    try:
        exit_code = load_data(patient_id)
        results['load_data'] = (exit_code == 0)
        print(f"\n{'✓ PASSED' if results['load_data'] else '✗ FAILED'}")
    except Exception as e:
        print(f"\n✗ FAILED: {e}")
        results['load_data'] = False

    if not results['load_data']:
        print("\n[ERROR] Load data failed - cannot continue")
        return results

    # Test 2: Lung Segmentation
    print("\n" + "=" * 70)
    print("TEST 2: LUNG SEGMENTATION")
    print("=" * 70)
    try:
        exit_code = lung_segment(patient_id)
        results['lung_segment'] = (exit_code == 0)
        print(f"\n{'✓ PASSED' if results['lung_segment'] else '✗ FAILED'}")
    except Exception as e:
        print(f"\n✗ FAILED: {e}")
        import traceback
        traceback.print_exc()
        results['lung_segment'] = False

    if not results['lung_segment']:
        print("\n[ERROR] Lung segmentation failed - cannot continue")
        return results

    # Test 3: COVID Detection
    print("\n" + "=" * 70)
    print("TEST 3: COVID-19 DETECTION")
    print("=" * 70)
    try:
        exit_code = covid_detect(patient_id)
        results['covid_detect'] = (exit_code == 0)
        print(f"\n{'✓ PASSED' if results['covid_detect'] else '✗ FAILED'}")
    except Exception as e:
        print(f"\n✗ FAILED: {e}")
        import traceback
        traceback.print_exc()
        results['covid_detect'] = False

    if not results['covid_detect']:
        print("\n[ERROR] COVID detection failed - cannot continue")
        return results

    # Test 4: Visualization
    print("\n" + "=" * 70)
    print("TEST 4: VISUALIZATION")
    print("=" * 70)
    try:
        exit_code = create_visualization(patient_id)
        results['visualization'] = (exit_code == 0)
        print(f"\n{'✓ PASSED' if results['visualization'] else '✗ FAILED'}")
    except Exception as e:
        print(f"\n✗ FAILED: {e}")
        import traceback
        traceback.print_exc()
        results['visualization'] = False

    # Summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)

    for test_name, passed in results.items():
        status = "✓ PASSED" if passed else "✗ FAILED"
        print(f"  {test_name:20s}: {status}")

    all_passed = all(results.values())

    print("\n" + "=" * 70)
    if all_passed:
        print("✓ ALL TESTS PASSED!")
        print("=" * 70)
        print("\nOutput files:")
        print(f"  - /mnt/data/covid_outputs/week_current/{patient_id}/covid_results.json")
        print(f"  - /mnt/data/covid_outputs/week_current/{patient_id}/full_comparison_{patient_id}.png")
        print("\nReady to deploy to Kubeflow!")
    else:
        print("✗ SOME TESTS FAILED")
        print("=" * 70)
        print("\nPlease fix the failures before deploying to Kubeflow")

    return results


if __name__ == "__main__":
    if len(sys.argv) > 1:
        patient_id = sys.argv[1]
    else:
        patient_id = "lung_001"

    test_pipeline(patient_id)
