#!/usr/bin/env python3
"""
Upload MONAI pipeline to Kubeflow UI
"""
import kfp
from pathlib import Path

def upload_pipeline():
    """Upload pipeline YAML to Kubeflow"""

    # Configuration
    KUBEFLOW_HOST = "http://ml-pipeline-ui.kubeflow.svc.cluster.local:80"
    PIPELINE_FILE = "covid_pipeline_working.yaml"
    PIPELINE_NAME = "COVID-19 Detection MONAI"

    print(f"🚀 Uploading pipeline to Kubeflow...")
    print(f"   Pipeline file: {PIPELINE_FILE}")
    print(f"   Pipeline name: {PIPELINE_NAME}")
    print(f"   Kubeflow host: {KUBEFLOW_HOST}")
    print()

    # Check if file exists
    pipeline_path = Path(PIPELINE_FILE)
    if not pipeline_path.exists():
        print(f"❌ Error: Pipeline file not found: {PIPELINE_FILE}")
        return False

    try:
        # Create KFP client
        print("📡 Connecting to Kubeflow...")
        client = kfp.Client(host=KUBEFLOW_HOST)

        # Upload pipeline
        print("📤 Uploading pipeline...")
        pipeline = client.upload_pipeline(
            pipeline_package_path=str(pipeline_path),
            pipeline_name=PIPELINE_NAME,
            description="MONAI-based COVID-19 detection from CT scans with lung segmentation and clinical visualization"
        )

        print()
        print("✅ Pipeline uploaded successfully!")
        print(f"   Pipeline ID: {pipeline.id}")
        print(f"   Pipeline Name: {pipeline.name}")
        print()
        print("🎉 Next steps:")
        print(f"   1. Open Kubeflow UI: http://10.105.196.111:31296")
        print(f"   2. Go to 'Pipelines' section")
        print(f"   3. Find pipeline: '{PIPELINE_NAME}'")
        print(f"   4. Click '+ Create run' to start")
        print()

        return True

    except Exception as e:
        print(f"❌ Error uploading pipeline: {e}")
        print()
        print("💡 Troubleshooting:")
        print("   1. Check if Kubeflow is running: kubectl get pods -n kubeflow")
        print("   2. Try port-forward: kubectl port-forward -n kubeflow svc/ml-pipeline-ui 8080:80")
        print("   3. Then use KUBEFLOW_HOST = 'http://localhost:8080'")
        print()
        return False

if __name__ == "__main__":
    upload_pipeline()
