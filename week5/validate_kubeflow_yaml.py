#!/usr/bin/env python3
"""
Kubeflow YAML Validation Script
Validates pipeline YAML for Kubeflow compatibility
"""

import yaml
import sys
import os

def validate_yaml_for_kubeflow(yaml_file):
    """Validate YAML file for Kubeflow compatibility"""

    print(f"🔍 Validating {yaml_file} for Kubeflow compatibility...")
    print("=" * 60)

    try:
        # Check if file exists
        if not os.path.exists(yaml_file):
            print(f"❌ File not found: {yaml_file}")
            return False

        # Read YAML content
        with open(yaml_file, 'r', encoding='utf-8') as f:
            yaml_content = f.read()

        # Parse YAML
        content = yaml.safe_load(yaml_content)

        print("✅ YAML syntax is valid")

        # Check for Kubeflow incompatible fields
        incompatible_fields = ['depends:']
        for field in incompatible_fields:
            if field in yaml_content:
                print(f"❌ Found Kubeflow incompatible field: {field}")
                return False

        print("✅ No Kubeflow incompatible fields found")

        # Check required fields
        required_fields = ['apiVersion', 'kind', 'metadata', 'spec']
        for field in required_fields:
            if field not in content:
                print(f"❌ Missing required field: {field}")
                return False

        print("✅ All required fields present")

        # Check API version
        if content.get('apiVersion') != 'argoproj.io/v1alpha1':
            print(f"⚠️  Unexpected API version: {content.get('apiVersion')}")

        # Check kind
        if content.get('kind') != 'Workflow':
            print(f"⚠️  Unexpected kind: {content.get('kind')}")

        # Check templates
        if 'templates' not in content.get('spec', {}):
            print("❌ Missing templates in spec")
            return False

        templates = content['spec']['templates']
        print(f"✅ Found {len(templates)} templates")

        # Check template names
        template_names = [t.get('name') for t in templates if 'name' in t]
        print(f"✅ Template names: {template_names}")

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
            print(f"❌ Missing required templates: {missing_templates}")
            return False

        print("✅ All required templates present")

        # Check service account
        service_account = content.get('spec', {}).get('serviceAccountName')
        if service_account:
            print(f"✅ Service account: {service_account}")

        # Check entrypoint
        entrypoint = content.get('spec', {}).get('entrypoint')
        if entrypoint:
            print(f"✅ Entry point: {entrypoint}")

        # Check volume claim templates
        volume_claims = content.get('spec', {}).get('volumeClaimTemplates', [])
        if volume_claims:
            print(f"✅ Found {len(volume_claims)} volume claim templates")
            for claim in volume_claims:
                name = claim.get('metadata', {}).get('name', 'unnamed')
                storage = claim.get('spec', {}).get('resources', {}).get('requests', {}).get('storage', 'unspecified')
                print(f"   - {name}: {storage}")

        # Check for container definitions
        container_count = 0
        for template in templates:
            if 'container' in template:
                container_count += 1
                container = template['container']
                image = container.get('image', 'unspecified')
                resources = container.get('resources', {})
                print(f"✅ Container template: {template['name']} -> {image}")

                # Check resource limits
                requests = resources.get('requests', {})
                limits = resources.get('limits', {})
                if requests or limits:
                    print(f"   Resources: {requests} / {limits}")

        print(f"✅ Found {container_count} container templates")

        # Validate step dependencies (check for proper sequential ordering)
        step_dependencies = []
        for template in templates:
            if 'steps' in template:
                for step_group in template['steps']:
                    for step in step_group:
                        step_name = step.get('name', 'unnamed')
                        step_dependencies.append(step_name)

        if step_dependencies:
            print(f"✅ Found step dependencies: {step_dependencies}")

        print("=" * 60)
        print("🎉 YAML validation PASSED - Ready for Kubeflow!")
        print(f"📋 Pipeline: {content.get('metadata', {}).get('name', 'unnamed')}")
        print(f"📂 Namespace: {content.get('metadata', {}).get('namespace', 'default')}")
        print(f"🏷️  Version: {content.get('metadata', {}).get('labels', {}).get('version', 'unspecified')}")

        return True

    except yaml.YAMLError as e:
        print(f"❌ YAML syntax error: {e}")
        return False
    except Exception as e:
        print(f"❌ Validation error: {e}")
        return False

def main():
    """Main validation function"""

    if len(sys.argv) != 2:
        print("Usage: python validate_kubeflow_yaml.py <yaml_file>")
        print("\nExample:")
        print("  python validate_kubeflow_yaml.py hospital_covid_kubeflow_fixed.yaml")
        sys.exit(1)

    yaml_file = sys.argv[1]

    if validate_yaml_for_kubeflow(yaml_file):
        print("\n✅ Validation successful! You can upload this YAML to Kubeflow UI.")
        sys.exit(0)
    else:
        print("\n❌ Validation failed! Please fix the issues before uploading to Kubeflow.")
        sys.exit(1)

if __name__ == "__main__":
    main()