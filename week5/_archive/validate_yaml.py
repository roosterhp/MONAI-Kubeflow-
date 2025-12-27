#!/usr/bin/env python3
import yaml
import sys

def validate_yaml_files():
    files_to_check = [
        'hospital_covid_detection_week5_fixed.yaml',
        'covid_detection_week5_fixed.yaml'
    ]

    results = []

    for filename in files_to_check:
        try:
            with open(filename, 'r') as file:
                yaml_content = yaml.safe_load(file)

            result = {
                'file': filename,
                'status': 'VALID',
                'kind': yaml_content.get('kind', 'Unknown'),
                'apiVersion': yaml_content.get('apiVersion', 'Unknown'),
                'metadata_name': yaml_content.get('metadata', {}).get('name', 'Unknown'),
                'entrypoint': yaml_content.get('spec', {}).get('entrypoint', 'Unknown'),
                'templates_count': len(yaml_content.get('spec', {}).get('templates', [])),
                'error': None
            }

            print(f"[OK] {filename}: YAML syntax is valid")
            print(f"     Kind: {result['kind']}")
            print(f"     API Version: {result['apiVersion']}")
            print(f"     Metadata name: {result['metadata_name']}")
            print(f"     Entry point: {result['entrypoint']}")
            print(f"     Templates count: {result['templates_count']}")
            print()

            results.append(result)

        except yaml.YAMLError as e:
            result = {
                'file': filename,
                'status': 'YAML_ERROR',
                'error': str(e)
            }

            print(f"[ERROR] {filename}: YAML syntax error")
            print(f"        Error: {e}")
            print()

            results.append(result)

        except Exception as e:
            result = {
                'file': filename,
                'status': 'OTHER_ERROR',
                'error': str(e)
            }

            print(f"[ERROR] {filename}: Unexpected error")
            print(f"        Error: {e}")
            print()

            results.append(result)

    return results

def analyze_argo_structure(yaml_content):
    """Analyze Argo workflow structure for compliance"""
    issues = []

    spec = yaml_content.get('spec', {})
    templates = spec.get('templates', [])

    for template in templates:
        template_name = template.get('name', 'unnamed')

        # Check steps structure
        if 'steps' in template:
            steps = template['steps']
            if not isinstance(steps, list):
                issues.append(f"Template '{template_name}': steps field must be an array")
            else:
                for i, step in enumerate(steps):
                    if not isinstance(step, list):
                        issues.append(f"Template '{template_name}': step {i} must be an array (parallel execution group)")

        # Check template references
        if 'templateRef' in template:
            issues.append(f"Template '{template_name}': templateRef is deprecated, use 'template: name' instead")

    return issues

if __name__ == "__main__":
    print("=== YAML Validation Report ===\n")

    validation_results = validate_yaml_files()

    print("=== Argo Structure Analysis ===\n")

    for result in validation_results:
        if result['status'] == 'VALID':
            try:
                with open(result['file'], 'r') as file:
                    yaml_content = yaml.safe_load(file)

                issues = analyze_argo_structure(yaml_content)

                if issues:
                    print(f"[WARN] {result['file']} has structural issues:")
                    for issue in issues:
                        print(f"        - {issue}")
                    print()
                else:
                    print(f"[OK] {result['file']}: Argo structure is compliant\n")

            except Exception as e:
                print(f"[ERROR] Could not analyze structure for {result['file']}: {e}\n")