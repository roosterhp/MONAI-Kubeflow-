#!/usr/bin/env python3
"""
COVID-19 Pipeline Diagnostic Script
Pre-flight check to verify all conditions for successful pipeline execution
"""

import os
import sys
import json
import glob
import subprocess
from pathlib import Path
from datetime import datetime

class PipelineDiagnostic:
    def __init__(self, input_dir="/mnt/data/weekly_input", output_dir="/mnt/data/hospital_output"):
        self.input_dir = Path(input_dir)
        self.output_dir = Path(output_dir)
        self.patient_ids = ["lung_001", "lung_002", "lung_003", "lung_004"]
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "input_dir": str(self.input_dir),
            "output_dir": str(self.output_dir),
            "checks": {},
            "overall_status": "unknown"
        }

    def log_result(self, check_name, status, message="", details=None):
        """Log diagnostic result"""
        self.results["checks"][check_name] = {
            "status": status,
            "message": message,
            "details": details or {}
        }

        status_icon = "✅" if status == "pass" else "❌" if status == "fail" else "⚠️"
        print(f"{status_icon} {check_name}: {message}")

        if details:
            for key, value in details.items():
                print(f"    - {key}: {value}")

    def check_directory_access(self):
        """Check if input and output directories are accessible"""
        print("\n📁 Checking Directory Access...")

        # Input directory checks
        if self.input_dir.exists():
            if os.access(self.input_dir, os.R_OK):
                files = list(self.input_dir.glob("*.nii*"))
                self.log_result(
                    "Input Directory Access",
                    "pass",
                    f"Readable, found {len(files)} .nii files",
                    {"path": str(self.input_dir), "file_count": len(files)}
                )
            else:
                self.log_result(
                    "Input Directory Access",
                    "fail",
                    "Directory exists but not readable",
                    {"path": str(self.input_dir)}
                )
        else:
            self.log_result(
                "Input Directory Access",
                "fail",
                "Input directory does not exist",
                {"path": str(self.input_dir)}
            )

        # Output directory checks
        try:
            self.output_dir.mkdir(parents=True, exist_ok=True)
            if os.access(self.output_dir, os.W_OK):
                self.log_result(
                    "Output Directory Access",
                    "pass",
                    "Writable",
                    {"path": str(self.output_dir)}
                )
            else:
                self.log_result(
                    "Output Directory Access",
                    "fail",
                    "Directory exists but not writable",
                    {"path": str(self.output_dir)}
                )
        except Exception as e:
            self.log_result(
                "Output Directory Access",
                "fail",
                f"Cannot create output directory: {e}",
                {"path": str(self.output_dir)}
            )

    def check_nifti_files(self):
        """Check for required NIfTI files"""
        print("\n🫁 Checking NIfTI Files...")

        found_files = []
        missing_files = []
        invalid_files = []

        for patient_id in self.patient_ids:
            patterns = [
                f"{patient_id}.nii.gz",
                f"{patient_id}.nii",
                f"{patient_id}.*.nii.gz",
                f"*{patient_id}*.nii.gz"
            ]

            file_found = False
            for pattern in patterns:
                matches = glob.glob(str(self.input_dir / pattern))
                if matches:
                    file_path = Path(matches[0])
                    found_files.append({
                        "patient_id": patient_id,
                        "file_path": str(file_path),
                        "file_size": file_path.stat().st_size,
                        "pattern_used": pattern
                    })
                    file_found = True
                    break

            if not file_found:
                missing_files.append(patient_id)

        # Check file sizes
        for file_info in found_files:
            if file_info["file_size"] < 1024:  # Less than 1KB
                invalid_files.append({
                    "patient_id": file_info["patient_id"],
                    "file_path": file_info["file_path"],
                    "issue": "File too small (< 1KB)"
                })

        # Log results
        if found_files:
            self.log_result(
                "NIfTI File Discovery",
                "pass",
                f"Found {len(found_files)}/{len(self.patient_ids)} patient files",
                {
                    "found_files": found_files,
                    "expected_files": len(self.patient_ids)
                }
            )
        else:
            self.log_result(
                "NIfTI File Discovery",
                "fail",
                "No NIfTI files found",
                {"expected_patterns": [f"{pid}.nii.gz" for pid in self.patient_ids]}
            )

        if missing_files:
            self.log_result(
                "Missing NIfTI Files",
                "fail",
                f"Missing {len(missing_files)} patient files",
                {"missing_files": missing_files}
            )

        if invalid_files:
            self.log_result(
                "Invalid NIfTI Files",
                "fail",
                f"Found {len(invalid_files)} invalid files",
                {"invalid_files": invalid_files}
            )

    def check_file_integrity(self):
        """Check if NIfTI files can be read and are valid"""
        print("\n🔍 Checking File Integrity...")

        try:
            import nibabel as nib
        except ImportError:
            self.log_result(
                "File Integrity Check",
                "warn",
                "nibabel not available for integrity checking",
                {"suggestion": "Install nibabel: pip install nibabel"}
            )
            return

        valid_files = []
        corrupt_files = []

        for patient_id in self.patient_ids:
            patterns = [
                f"{patient_id}.nii.gz",
                f"{patient_id}.nii",
                f"{patient_id}.*.nii.gz",
                f"*{patient_id}*.nii.gz"
            ]

            file_found = False
            for pattern in patterns:
                matches = glob.glob(str(self.input_dir / pattern))
                if matches:
                    file_path = matches[0]
                    file_found = True

                    try:
                        # Try to load the NIfTI file
                        img = nib.load(file_path)
                        data = img.get_fdata()

                        file_info = {
                            "patient_id": patient_id,
                            "file_path": file_path,
                            "shape": list(data.shape),
                            "data_type": str(data.dtype),
                            "non_zero_voxels": int((data != 0).sum()),
                            "min_value": float(data.min()),
                            "max_value": float(data.max())
                        }

                        # Basic validation
                        if data.size == 0:
                            corrupt_files.append({
                                "patient_id": patient_id,
                                "file_path": file_path,
                                "issue": "Empty data"
                            })
                        elif (data == 0).all():
                            corrupt_files.append({
                                "patient_id": patient_id,
                                "file_path": file_path,
                                "issue": "All zeros"
                            })
                        else:
                            valid_files.append(file_info)

                    except Exception as e:
                        corrupt_files.append({
                            "patient_id": patient_id,
                            "file_path": file_path,
                            "issue": f"Load error: {str(e)}"
                        })

                    break

        if valid_files:
            self.log_result(
                "File Integrity Check",
                "pass",
                f"{len(valid_files)} files passed integrity check",
                {"valid_files": valid_files[:3]}  # Show first 3 for brevity
            )

        if corrupt_files:
            self.log_result(
                "Corrupt Files",
                "fail",
                f"{len(corrupt_files)} files failed integrity check",
                {"corrupt_files": corrupt_files}
            )

    def check_kubernetes_access(self):
        """Check Kubernetes cluster access"""
        print("\n☸️  Checking Kubernetes Access...")

        try:
            # Check if kubectl is available
            result = subprocess.run(['kubectl', 'version', '--client'],
                                  capture_output=True, text=True, timeout=10)

            if result.returncode == 0:
                version_info = result.stdout.strip()
                self.log_result(
                    "Kubectl Access",
                    "pass",
                    "kubectl is accessible",
                    {"version": version_info}
                )
            else:
                self.log_result(
                    "Kubectl Access",
                    "fail",
                    "kubectl command failed",
                    {"error": result.stderr}
                )

        except subprocess.TimeoutExpired:
            self.log_result(
                "Kubectl Access",
                "fail",
                "kubectl command timed out"
            )
        except FileNotFoundError:
            self.log_result(
                "Kubectl Access",
                "fail",
                "kubectl not found in PATH"
            )
        except Exception as e:
            self.log_result(
                "Kubectl Access",
                "fail",
                f"Unexpected error: {str(e)}"
            )

        # Check cluster access
        try:
            result = subprocess.run(['kubectl', 'cluster-info'],
                                  capture_output=True, text=True, timeout=10)

            if result.returncode == 0:
                self.log_result(
                    "Cluster Access",
                    "pass",
                    "Can connect to Kubernetes cluster"
                )
            else:
                self.log_result(
                    "Cluster Access",
                    "fail",
                    "Cannot connect to cluster",
                    {"error": result.stderr}
                )

        except Exception as e:
            self.log_result(
                "Cluster Access",
                "fail",
                f"Cluster connection error: {str(e)}"
            )

    def check_kubeflow_resources(self):
        """Check Kubeflow namespace and resources"""
        print("\n🚀 Checking Kubeflow Resources...")

        try:
            # Check kubeflow namespace
            result = subprocess.run(['kubectl', 'get', 'namespace', 'kubeflow'],
                                  capture_output=True, text=True, timeout=10)

            if result.returncode == 0:
                self.log_result(
                    "Kubeflow Namespace",
                    "pass",
                    "kubeflow namespace exists"
                )

                # Check Kubeflow pods
                result = subprocess.run(['kubectl', 'get', 'pods', '-n', 'kubeflow'],
                                      capture_output=True, text=True, timeout=15)

                if result.returncode == 0:
                    lines = result.stdout.strip().split('\n')
                    pod_count = len(lines) - 1  # Exclude header
                    running_pods = len([line for line in lines[1:] if 'Running' in line])

                    self.log_result(
                        "Kubeflow Pods",
                        "pass",
                        f"{running_pods}/{pod_count} pods running",
                        {
                            "total_pods": pod_count,
                            "running_pods": running_pods
                        }
                    )
                else:
                    self.log_result(
                        "Kubeflow Pods",
                        "fail",
                        "Cannot list kubeflow pods",
                        {"error": result.stderr}
                    )
            else:
                self.log_result(
                    "Kubeflow Namespace",
                    "fail",
                    "kubeflow namespace not found",
                    {"error": result.stderr}
                )

        except Exception as e:
            self.log_result(
                "Kubeflow Resources",
                "fail",
                f"Error checking Kubeflow: {str(e)}"
            )

    def check_cluster_resources(self):
        """Check cluster resource availability"""
        print("\n💾 Checking Cluster Resources...")

        try:
            # Check node resources
            result = subprocess.run(['kubectl', 'describe', 'nodes'],
                                  capture_output=True, text=True, timeout=15)

            if result.returncode == 0:
                output = result.stdout

                # Extract resource information (simplified)
                cpu_allocatable = "Unknown"
                memory_allocatable = "Unknown"

                for line in output.split('\n'):
                    if 'Allocatable:' in line and 'cpu:' in line.lower():
                        # Extract CPU info
                        continue
                    if 'Allocatable:' in line and 'memory:' in line.lower():
                        # Extract memory info
                        continue

                self.log_result(
                    "Cluster Resources",
                    "pass",
                    "Node information retrieved",
                    {
                        "note": "Detailed resource parsing requires additional processing",
                        "kubectl_command": "kubectl describe nodes"
                    }
                )
            else:
                self.log_result(
                    "Cluster Resources",
                    "fail",
                    "Cannot get node information",
                    {"error": result.stderr}
                )

        except Exception as e:
            self.log_result(
                "Cluster Resources",
                "fail",
                f"Error checking resources: {str(e)}"
            )

    def check_pipeline_file(self):
        """Check if robust pipeline file exists and is valid"""
        print("\n📄 Checking Pipeline File...")

        pipeline_file = Path("robust_sequence_parallel_pipeline.yaml")

        if pipeline_file.exists():
            size = pipeline_file.stat().st_size

            try:
                with open(pipeline_file, 'r') as f:
                    content = f.read()

                # Basic validation
                required_elements = [
                    "components:",
                    "deploymentSpec:",
                    "robust-sequence-parallel-covid-pipeline",
                    "load-patient-data-op",
                    "segment-lungs-op",
                    "detect-covid-op",
                    "create-visualization-op"
                ]

                missing_elements = []
                for element in required_elements:
                    if element not in content:
                        missing_elements.append(element)

                if not missing_elements:
                    self.log_result(
                        "Pipeline File Validation",
                        "pass",
                        f"Pipeline file is valid ({size:,} bytes)",
                        {"file_path": str(pipeline_file)}
                    )
                else:
                    self.log_result(
                        "Pipeline File Validation",
                        "fail",
                        f"Missing required elements: {missing_elements}",
                        {"file_path": str(pipeline_file)}
                    )

            except Exception as e:
                self.log_result(
                    "Pipeline File Validation",
                    "fail",
                    f"Error reading pipeline file: {str(e)}",
                    {"file_path": str(pipeline_file)}
                )
        else:
            self.log_result(
                "Pipeline File Validation",
                "fail",
                "Pipeline file not found",
                {"expected_path": str(pipeline_file)}
            )

    def generate_summary(self):
        """Generate diagnostic summary"""
        print("\n" + "="*60)
        print("DIAGNOSTIC SUMMARY")
        print("="*60)

        # Count status types
        checks = self.results["checks"]
        passed = sum(1 for check in checks.values() if check["status"] == "pass")
        failed = sum(1 for check in checks.values() if check["status"] == "fail")
        warned = sum(1 for check in checks.values() if check["status"] == "warn")
        total = len(checks)

        # Determine overall status
        if failed == 0:
            overall_status = "✅ READY - All checks passed"
            self.results["overall_status"] = "ready"
        elif failed <= 2:
            overall_status = "⚠️  WARNING - Minor issues that should be resolved"
            self.results["overall_status"] = "warning"
        else:
            overall_status = "❌ NOT READY - Major issues need to be resolved"
            self.results["overall_status"] = "not_ready"

        print(f"Overall Status: {overall_status}")
        print(f"Checks: {passed} passed, {warned} warnings, {failed} failed")

        # List failed checks
        if failed > 0:
            print("\n❌ Failed Checks:")
            for name, check in checks.items():
                if check["status"] == "fail":
                    print(f"   - {name}: {check['message']}")

        # List warnings
        if warned > 0:
            print("\n⚠️  Warnings:")
            for name, check in checks.items():
                if check["status"] == "warn":
                    print(f"   - {name}: {check['message']}")

        # Recommendations
        print("\n💡 Recommendations:")
        if failed > 0:
            print("1. Address all failed checks before running the pipeline")
            print("2. Check the troubleshooting_guide.md for detailed solutions")
        if warned > 0:
            print("3. Consider resolving warnings for optimal performance")

        if failed == 0:
            print("✅ System is ready! You can now deploy the pipeline:")
            print("   python deploy_robust_pipeline.py")

    def save_results(self):
        """Save diagnostic results to file"""
        output_file = f"pipeline_diagnostic_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

        try:
            with open(output_file, 'w') as f:
                json.dump(self.results, f, indent=2)
            print(f"\n💾 Diagnostic results saved to: {output_file}")
        except Exception as e:
            print(f"\n❌ Could not save results: {str(e)}")

    def run_all_checks(self):
        """Run all diagnostic checks"""
        print("🔬 COVID-19 PIPELINE DIAGNOSTIC")
        print("="*60)
        print(f"Timestamp: {self.results['timestamp']}")
        print(f"Input Directory: {self.input_dir}")
        print(f"Output Directory: {self.output_dir}")

        # Run all checks
        self.check_directory_access()
        self.check_nifti_files()
        self.check_file_integrity()
        self.check_pipeline_file()
        self.check_kubernetes_access()
        self.check_kubeflow_resources()
        self.check_cluster_resources()

        # Generate summary and save results
        self.generate_summary()
        self.save_results()

        return self.results["overall_status"]

def main():
    """Main function"""
    # Parse command line arguments
    input_dir = "/mnt/data/weekly_input"
    output_dir = "/mnt/data/hospital_output"

    if len(sys.argv) > 1:
        input_dir = sys.argv[1]
    if len(sys.argv) > 2:
        output_dir = sys.argv[2]

    # Run diagnostics
    diagnostic = PipelineDiagnostic(input_dir, output_dir)
    status = diagnostic.run_all_checks()

    # Exit with appropriate code
    if status == "ready":
        sys.exit(0)
    elif status == "warning":
        sys.exit(1)
    else:
        sys.exit(2)

if __name__ == "__main__":
    main()