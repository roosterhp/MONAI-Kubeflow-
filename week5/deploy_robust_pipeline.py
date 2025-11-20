#!/usr/bin/env python3
"""
Robust COVID-19 Pipeline Deployment Script
Deploy the enhanced pipeline with proper error handling and validation
"""

import kfp
import json
import sys
from pathlib import Path
from datetime import datetime

def deploy_robust_pipeline(kfp_endpoint=None):
    """
    Deploy the robust COVID-19 detection pipeline to Kubeflow

    Args:
        kfp_endpoint: Optional KFP endpoint URL. If None, uses default.

    Returns:
        pipeline_id: ID of the uploaded pipeline
    """

    print("=" * 60)
    print("COVID-19 ROBUST PIPELINE DEPLOYMENT")
    print("=" * 60)

    try:
        # Initialize KFP client
        if kfp_endpoint:
            client = kfp.Client(host=kfp_endpoint)
            print(f"✓ Connected to KFP endpoint: {kfp_endpoint}")
        else:
            client = kfp.Client()
            print("✓ Connected to default KFP endpoint")

        # Validate pipeline file exists
        pipeline_file = Path("robust_sequence_parallel_pipeline.yaml")
        if not pipeline_file.exists():
            raise FileNotFoundError(f"Pipeline file not found: {pipeline_file}")

        print(f"✓ Pipeline file found: {pipeline_file}")
        print(f"✓ File size: {pipeline_file.stat().st_size:,} bytes")

        # Load and validate pipeline
        print("📋 Loading pipeline configuration...")
        with open(pipeline_file, 'r') as f:
            pipeline_content = f.read()

        # Basic validation
        if "robust-sequence-parallel-covid-pipeline" not in pipeline_content:
            raise ValueError("Pipeline name not found in file")

        if "components:" not in pipeline_content:
            raise ValueError("Components section not found")

        if "deploymentSpec:" not in pipeline_content:
            raise ValueError("Deployment specification not found")

        print("✓ Pipeline configuration validated")

        # Upload pipeline
        print("📤 Uploading pipeline to Kubeflow...")
        pipeline_name = "Robust COVID-19 Detection Pipeline v2.0"
        description = "Enhanced COVID-19 detection with robust error handling and validation"

        pipeline = client.upload_pipeline(
            pipeline_file=str(pipeline_file),
            pipeline_name=pipeline_name,
            description=description
        )

        print(f"✅ Pipeline uploaded successfully!")
        print(f"   Pipeline ID: {pipeline.id}")
        print(f"   Pipeline Name: {pipeline_name}")
        print(f"   Description: {description}")

        # Create experiment
        print("🧪 Creating experiment...")
        experiment_name = "Robust COVID-19 Analysis"
        experiment_description = "Enhanced COVID-19 detection experiments with robust error handling"

        try:
            experiment = client.create_experiment(
                name=experiment_name,
                description=experiment_description
            )
            print(f"✓ Experiment created: {experiment.id}")
        except Exception as e:
            # Experiment might already exist
            print(f"⚠️  Note: Experiment creation issue (may already exist): {e}")
            experiments = client.list_experiments(experiment_name=experiment_name)
            if experiments.experiments:
                experiment = experiments.experiments[0]
                print(f"✓ Using existing experiment: {experiment.id}")
            else:
                raise

        return {
            "pipeline_id": pipeline.id,
            "experiment_id": experiment.id,
            "pipeline_name": pipeline_name,
            "experiment_name": experiment_name,
            "status": "success"
        }

    except Exception as e:
        print(f"❌ Deployment failed: {str(e)}")
        return {
            "status": "failed",
            "error": str(e),
            "error_type": type(e).__name__
        }

def create_pipeline_run(deployment_info, input_dir="/mnt/data/weekly_input", output_dir="/mnt/data/hospital_output"):
    """
    Create a pipeline run with proper parameters

    Args:
        deployment_info: Dictionary with deployment information
        input_dir: Input directory path
        output_dir: Output directory path

    Returns:
        run_info: Dictionary with run information
    """

    try:
        client = kfp.Client()

        print("\n" + "=" * 60)
        print("CREATING PIPELINE RUN")
        print("=" * 60)

        # Validate deployment info
        if deployment_info["status"] != "success":
            raise ValueError("Cannot create run - deployment failed")

        # Prepare run parameters
        run_name = f"robust-covid-run-{datetime.now().strftime('%Y%m%d-%H%M%S')}"

        parameters = {
            "input_dir": input_dir,
            "output_dir": output_dir
        }

        print(f"🚀 Starting pipeline run...")
        print(f"   Run Name: {run_name}")
        print(f"   Pipeline ID: {deployment_info['pipeline_id']}")
        print(f"   Experiment ID: {deployment_info['experiment_id']}")
        print(f"   Input Directory: {input_dir}")
        print(f"   Output Directory: {output_dir}")

        # Create run
        run = client.run_pipeline(
            experiment_id=deployment_info["experiment_id"],
            pipeline_id=deployment_info["pipeline_id"],
            job_name=run_name,
            params=parameters,
            enable_caching=True
        )

        print(f"✅ Pipeline run created successfully!")
        print(f"   Run ID: {run.id}")
        print(f"   Run Name: {run.name}")
        print(f"   Status: {run.status}")

        return {
            "run_id": run.id,
            "run_name": run.name,
            "status": run.status,
            "status_code": "success"
        }

    except Exception as e:
        print(f"❌ Failed to create pipeline run: {str(e)}")
        return {
            "status_code": "failed",
            "error": str(e),
            "error_type": type(e).__name__
        }

def print_deployment_summary(deployment_info, run_info=None):
    """Print comprehensive deployment summary"""

    print("\n" + "=" * 60)
    print("DEPLOYMENT SUMMARY")
    print("=" * 60)

    if deployment_info["status"] == "success":
        print("✅ PIPELINE DEPLOYMENT: SUCCESS")
        print(f"   Pipeline: {deployment_info['pipeline_name']}")
        print(f"   Experiment: {deployment_info['experiment_name']}")
        print(f"   Pipeline ID: {deployment_info['pipeline_id']}")
        print(f"   Experiment ID: {deployment_info['experiment_id']}")

        if run_info and run_info["status_code"] == "success":
            print("✅ PIPELINE RUN: SUCCESS")
            print(f"   Run ID: {run_info['run_id']}")
            print(f"   Run Name: {run_info['run_name']}")
            print(f"   Status: {run_info['status']}")

            print("\n📊 NEXT STEPS:")
            print("1. Open Kubeflow UI to monitor pipeline execution")
            print("2. Check individual component logs if any step fails")
            print("3. Verify output files are generated correctly")
            print("4. Review enhanced error messages for troubleshooting")

        else:
            print("❌ PIPELINE RUN: FAILED")
            if run_info:
                print(f"   Error: {run_info.get('error', 'Unknown error')}")
    else:
        print("❌ PIPELINE DEPLOYMENT: FAILED")
        print(f"   Error: {deployment_info.get('error', 'Unknown error')}")
        print(f"   Error Type: {deployment_info.get('error_type', 'Unknown')}")

        print("\n🔧 TROUBLESHOOTING:")
        print("1. Check Kubeflow connection and credentials")
        print("2. Verify pipeline file exists and is valid")
        print("3. Ensure sufficient cluster resources")
        print("4. Check network connectivity to KFP endpoint")

def main():
    """Main deployment function"""

    # Parse command line arguments
    kfp_endpoint = None
    if len(sys.argv) > 1:
        kfp_endpoint = sys.argv[1]
        print(f"Using KFP endpoint: {kfp_endpoint}")

    # Deploy pipeline
    deployment_info = deploy_robust_pipeline(kfp_endpoint)

    if deployment_info["status"] == "success":
        # Create pipeline run
        run_info = create_pipeline_run(deployment_info)

        # Print summary
        print_deployment_summary(deployment_info, run_info)

        # Save deployment info to file
        with open("deployment_info.json", "w") as f:
            json.dump({
                "deployment": deployment_info,
                "run": run_info,
                "timestamp": datetime.now().isoformat()
            }, f, indent=2)

        print(f"\n💾 Deployment info saved to: deployment_info.json")

    else:
        print_deployment_summary(deployment_info)
        sys.exit(1)

if __name__ == "__main__":
    main()