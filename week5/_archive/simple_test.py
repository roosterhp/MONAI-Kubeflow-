#!/usr/bin/env python3
"""
Simple test script for Week5 COVID-19 Detection Pipeline Components
"""

import sys
import os

def test_imports():
    """Test basic imports"""
    print("Testing imports...")

    try:
        import numpy as np
        import SimpleITK as sitk
        import nibabel as nib
        import matplotlib.pyplot as plt
        print("[OK] Basic medical imaging imports")
    except ImportError as e:
        print(f"[FAIL] Basic imports: {e}")
        return False

    try:
        import torch
        import monai
        from monai.transforms import ScaleIntensityRanged
        print("[OK] MONAI imports")
    except ImportError as e:
        print(f"[FAIL] MONAI imports: {e}")
        return False

    try:
        from lungmask import LMInferer
        print("[OK] LungMask import")
    except ImportError as e:
        print(f"[FAIL] LungMask import: {e}")
        return False

    return True

def test_components():
    """Test component imports"""
    print("\nTesting components...")

    sys.path.insert(0, 'components')

    try:
        import lung_segment
        print("[OK] lung_segment import")
    except ImportError as e:
        print(f"[FAIL] lung_segment import: {e}")
        return False

    try:
        import covid_detect
        print("[OK] covid_detect import")
    except ImportError as e:
        print(f"[FAIL] covid_detect import: {e}")
        return False

    try:
        import visualize
        print("[OK] visualize import")
    except ImportError as e:
        print(f"[FAIL] visualize import: {e}")
        return False

    sys.path.pop(0)
    return True

def test_files():
    """Test file structure"""
    print("\nTesting file structure...")

    required_files = [
        'components/lung_segment.py',
        'components/covid_detect.py',
        'components/visualize.py',
        'pipeline.py',
        'run_pipeline_simple.py',
        'config/requirements.txt',
        'config/Dockerfile'
    ]

    for file_path in required_files:
        if os.path.exists(file_path):
            print(f"[OK] {file_path}")
        else:
            print(f"[FAIL] {file_path} missing")
            return False

    return True

def main():
    print("Week5 COVID-19 Pipeline Test")
    print("=" * 40)

    tests = [
        ("Basic Imports", test_imports),
        ("Components", test_components),
        ("File Structure", test_files)
    ]

    passed = 0
    for name, test_func in tests:
        print(f"\n{name}:")
        try:
            if test_func():
                print(f"[PASS] {name}")
                passed += 1
            else:
                print(f"[FAIL] {name}")
        except Exception as e:
            print(f"[ERROR] {name}: {e}")

    print(f"\nSummary: {passed}/{len(tests)} tests passed")
    return 0 if passed == len(tests) else 1

if __name__ == "__main__":
    sys.exit(main())