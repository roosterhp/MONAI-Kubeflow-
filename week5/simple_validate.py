#!/usr/bin/env python3
"""
Simple Kubeflow YAML Validation Script
"""

import yaml
import sys
import os

def validate_yaml_for_kubeflow(yaml_file):
    """Validate YAML file for Kubeflow compatibility"""

    print(f"Validating {yaml_file} for Kubeflow compatibility...")
    print("=" * 60)

    try:
        # Check if file exists
        if not os.path.exists(yaml_file):
            print(f"ERROR: File not found: {yaml_file}")
            return False

        # Read YAML content
        with open(yaml_file, 'r', encoding='utf-8') as f:
            yaml_content = f.read()

        # Parse YAML
        content = yaml.safe_load(yaml_content)

        print("SUCCESS: YAML syntax is valid")

        # Check for Kubeflow incompatible fields
        if 'depends:' in yaml_content:
            print("ERROR: Found Kubeflow incompatible field: depends:")
            return False

        print("SUCCESS: No Kubeflow incompatible fields found")

        # Check required fields
        required_fields = ['apiVersion', 'kind', 'metadata', 'spec']
        for field in required_fields:
            if field not in content:
                print(f"ERROR: Missing required field: {field}")
                return False

        print("SUCCESS: All required fields present")

        # Check templates
        if 'templates' not in content.get('spec', {}):
            print("ERROR: Missing templates in spec")
            return False

        templates = content['spec']['templates']
        print(f"SUCCESS: Found {len(templates)} templates")

        # Check template names
        template_names = [t.get('name') for t in templates if 'name' in t]
        print(f"SUCCESS: Template names: {template_names}")

        # Required templates for our pipeline
        required_templates = [
            'hospital-covid-pipeline',
            'load-data-template',
            'process-patient-parallel',
            'patient-processing-workflow',
            'lung-segmentation-template',
            'covid-detection-template',
            'visualization-template'
        ]

        missing_templates = [t for t in required_templates if t not in template_names]
        if missing_templates:
            print(f"ERROR: Missing required templates: {missing_templates}")
            return False

        print("SUCCESS: All required templates present")

        print("=" * 60)
        print("YAML validation PASSED - Ready for Kubeflow!")
        print(f"Pipeline: {content.get('metadata', {}).get('name', 'unnamed')}")
        print(f"Namespace: {content.get('metadata', {}).get('namespace', 'default')}")
        print(f"Version: {content.get('metadata', {}).get('labels', {}).get('version', 'unspecified')}")

        return True

    except yaml.YAMLError as e:
        print(f"ERROR: YAML syntax error: {e}")
        return False
    except Exception as e:
        print(f"ERROR: Validation error: {e}")
        return False

if __name__ == "__main__":
    yaml_file = "hospital_covid_kubeflow_fixed.yaml"
    result = validate_yaml_for_kubeflow(yaml_file)
    print(f"\nValidation result: {'PASSED' if result else 'FAILED'}")