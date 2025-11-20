#!/usr/bin/env python3
"""
Test script for Week5 COVID-19 Detection Pipeline Components
Tests imports, basic functionality, and pipeline structure
"""

import sys
import os
import tempfile
import numpy as np
from pathlib import Path

def test_basic_imports():
    """Test that all required modules can be imported"""
    print("Testing basic imports...")

    try:
        import numpy as np
        import SimpleITK as sitk
        import nibabel as nib
        import matplotlib.pyplot as plt
        print("✓ Basic medical imaging imports successful")
    except ImportError as e:
        print(f"✗ Basic import failed: {e}")
        return False

    try:
        import torch
        import monai
        from monai.transforms import ScaleIntensityRanged
        print("✓ MONAI imports successful")
    except ImportError as e:
        print(f"✗ MONAI import failed: {e}")
        return False

    try:
        from lungmask import LMInferer
        print("✓ LungMask import successful")
    except ImportError as e:
        print(f"✗ LungMask import failed: {e}")
        return False

    return True

def test_component_imports():
    """Test that all components can be imported"""
    print("\nTesting component imports...")

    components = ['lung_segment', 'covid_detect', 'visualize']

    for component in components:
        try:
            sys.path.insert(0, 'components')
            module = __import__(component)
            print(f"✓ {component} import successful")
            sys.path.pop(0)
        except ImportError as e:
            print(f"✗ {component} import failed: {e}")
            return False

    return True

def test_pipeline_structure():
    """Test pipeline structure without KFP"""
    print("\nTesting pipeline structure...")

    try:
        # Check if pipeline file exists and is syntactically correct
        with open('pipeline.py', 'r') as f:
            content = f.read()

        # Check for key pipeline elements
        required_elements = [
            'def lung_segmentation_op',
            'def covid_detection_op',
            'def create_pipeline',
            '@component',
            '@dsl.pipeline'
        ]

        for element in required_elements:
            if element in content:
                print(f"✓ Pipeline structure contains {element}")
            else:
                print(f"✗ Pipeline structure missing {element}")
                return False

    except Exception as e:
        print(f"✗ Pipeline structure test failed: {e}")
        return False

    return True

def test_dockerfile_structure():
    """Test Dockerfile structure"""
    print("\nTesting Dockerfile structure...")

    try:
        with open('config/Dockerfile', 'r') as f:
            content = f.read()

        # Check for key Dockerfile elements
        required_elements = [
            'FROM python:3.10-slim',
            'WORKDIR /app',
            'COPY config/requirements.txt',
            'RUN pip install',
            'lungmask',
            'COPY components/'
        ]

        for element in required_elements:
            if element in content:
                print(f"✓ Dockerfile contains {element}")
            else:
                print(f"✗ Dockerfile missing {element}")
                return False

    except Exception as e:
        print(f"✗ Dockerfile test failed: {e}")
        return False

    return True

def test_requirements():
    """Test requirements.txt structure"""
    print("\nTesting requirements.txt...")

    try:
        with open('config/requirements.txt', 'r') as f:
            lines = f.readlines()

        # Check for key dependencies
        required_deps = ['torch', 'monai', 'SimpleITK', 'nibabel', 'matplotlib', 'numpy']

        content = ''.join(lines)
        for dep in required_deps:
            if dep in content:
                print(f"✓ requirements.txt contains {dep}")
            else:
                print(f"✗ requirements.txt missing {dep}")
                return False

    except Exception as e:
        print(f"✗ requirements.txt test failed: {e}")
        return False

    return True

def create_test_data():
    """Create minimal test data for component testing"""
    print("\nCreating test data...")

    try:
        # Create temporary directory structure
        test_dir = Path("test_data")
        test_dir.mkdir(exist_ok=True)

        # Create a simple test numpy array (simulating CT data)
        ct_data = np.random.randint(-1000, 1000, (50, 50, 30), dtype=np.int16)
        np.save(test_dir / "ct_array.npy", ct_data)

        # Create a simple lung mask
        lung_mask = np.zeros((50, 50, 30), dtype=np.uint8)
        lung_mask[10:40, 10:40, 5:25] = 1  # Simple rectangular mask
        np.save(test_dir / "lung_mask.npy", lung_mask)

        print("✓ Test data created successfully")
        return test_dir

    except Exception as e:
        print(f"✗ Test data creation failed: {e}")
        return None

def test_component_functions():
    """Test that component functions can be called"""
    print("\nTesting component functions...")

    # Add components to path
    sys.path.insert(0, 'components')

    try:
        # Test lung_segment functions
        import lung_segment
        print("✓ lung_segment module functions available")

        # Test covid_detect functions
        import covid_detect
        if hasattr(covid_detect, 'extract_features'):
            print("✓ covid_detect extract_features function available")
        if hasattr(covid_detect, 'covid_detect'):
            print("✓ covid_detect main function available")

        # Test visualize functions
        import visualize
        if hasattr(visualize, 'create_visualization'):
            print("✓ visualize create_visualization function available")

    except Exception as e:
        print(f"✗ Component function test failed: {e}")
        return False
    finally:
        sys.path.pop(0)

    return True

def main():
    """Run all tests"""
    print("Week5 COVID-19 Detection Pipeline - Component Testing")
    print("=" * 60)

    tests = [
        ("Basic Imports", test_basic_imports),
        ("Component Imports", test_component_imports),
        ("Pipeline Structure", test_pipeline_structure),
        ("Dockerfile Structure", test_dockerfile_structure),
        ("Requirements", test_requirements),
        ("Component Functions", test_component_functions),
    ]

    results = []

    for test_name, test_func in tests:
        print(f"\n{'='*20} {test_name} {'='*20}")
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"✗ {test_name} failed with exception: {e}")
            results.append((test_name, False))

    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)

    passed = 0
    total = len(results)

    for test_name, result in results:
        status = "PASS" if result else "FAIL"
        print(f"{test_name:.<30} {status}")
        if result:
            passed += 1

    print(f"\nOverall: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 All tests passed! Pipeline components are ready.")
        return 0
    else:
        print("⚠️  Some tests failed. Please check the issues above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())