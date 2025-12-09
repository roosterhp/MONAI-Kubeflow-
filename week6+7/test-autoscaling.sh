#!/bin/bash

# Simple load test for Kubeflow autoscaling
# This script will stress test the ml-pipeline service to trigger HPA scaling

echo "=== Kubeflow Autoscaling Test ==="
echo "Starting load test on ml-pipeline service..."
echo ""

# Get the ml-pipeline service endpoint
SERVICE_IP=$(kubectl get svc ml-pipeline-ui -n kubeflow -o jsonpath='{.spec.clusterIP}')
SERVICE_PORT=$(kubectl get svc ml-pipeline-ui -n kubeflow -o jsonpath='{.spec.ports[0].port}')

echo "Target: $SERVICE_IP:$SERVICE_PORT"
echo "Duration: 2 minutes"
echo ""

# Create a temporary pod to generate load
kubectl run load-generator \
  --image=busybox:1.35 \
  --restart=Never \
  --rm \
  -i \
  --command -- /bin/sh -c "
    echo 'Generating load for 2 minutes...'
    timeout 120 /bin/sh -c 'while true; do
      wget -q -O- http://$SERVICE_IP:$SERVICE_PORT/ > /dev/null 2>&1 &
      wget -q -O- http://$SERVICE_IP:$SERVICE_PORT/ > /dev/null 2>&1 &
      wget -q -O- http://$SERVICE_IP:$SERVICE_PORT/ > /dev/null 2>&1 &
      sleep 0.1
    done'
    echo 'Load test completed'
  " 2>/dev/null

echo ""
echo "Load test completed!"
