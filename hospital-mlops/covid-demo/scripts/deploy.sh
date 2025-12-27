#!/bin/bash
# Quick deploy script for COVID-19 Detection Pipeline

set -e

echo "=========================================="
echo "Deploying COVID-19 Detection Pipeline"
echo "=========================================="

# Step 1: Apply Kubernetes resources
echo "[Step 1/2] Deploying Kubernetes resources..."
kubectl apply -f kubernetes/pv.yaml
kubectl apply -f kubernetes/pvc.yaml
echo "✓ PV and PVC deployed"

# Step 2: Verify PVC is bound
echo "[Step 2/2] Verifying PVC status..."
kubectl get pvc -n kubeflow | grep covid-data-pvc
echo "✓ PVC status checked"

echo ""
echo "=========================================="
echo "Deployment complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Upload covid_pipeline.yaml to Kubeflow UI"
echo "2. Create a new experiment in Kubeflow"
echo "3. Create a run and monitor progress"
echo ""
echo "Pipeline outputs will be in:"
echo "  /mnt/data/covid_outputs/week_current/{patient_id}/"
echo "  - covid_results.json"
echo "  - features.json"
echo "  - full_comparison_{patient_id}.png"
echo ""
