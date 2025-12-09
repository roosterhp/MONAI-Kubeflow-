#!/bin/bash

# Heavy load test for Kubeflow autoscaling
# This script will create INTENSE load to trigger aggressive HPA scaling

echo "=== Kubeflow Autoscaling Test (HEAVY LOAD) ==="
echo "WARNING: Starting HEAVY load test on ml-pipeline service..."
echo ""

# Get the ml-pipeline service endpoint
SERVICE_IP=$(kubectl get svc ml-pipeline-ui -n kubeflow -o jsonpath='{.spec.clusterIP}')
SERVICE_PORT=$(kubectl get svc ml-pipeline-ui -n kubeflow -o jsonpath='{.spec.ports[0].port}')

if [ -z "$SERVICE_IP" ]; then
    echo "ERROR: Cannot find ml-pipeline-ui service"
    exit 1
fi

echo "Target: http://$SERVICE_IP:$SERVICE_PORT"
echo "Duration: 5 minutes (300 seconds)"
echo "Load: HIGH (20 concurrent requests every 0.01s)"
echo ""
echo "Starting in 3 seconds..."
sleep 3

# Create a temporary pod to generate HEAVY load
kubectl run load-generator \
  --image=busybox:1.35 \
  --restart=Never \
  --rm \
  -i \
  -n kubeflow \
  --command -- /bin/sh -c "
    echo 'Generating HEAVY load for 5 minutes...'
    echo ''

    start_time=\$(date +%s)
    request_count=0

    timeout 300 /bin/sh -c 'while true; do
      # Launch 20 parallel requests
      i=1
      while [ \$i -le 20 ]; do
        wget -q -O- http://$SERVICE_IP:$SERVICE_PORT/ > /dev/null 2>&1 &
        i=\$((i + 1))
      done

      # Very short sleep to maintain high load
      sleep 0.01
    done'

    end_time=\$(date +%s)
    duration=\$((end_time - start_time))

    echo ''
    echo 'Load test completed!'
    echo \"Duration: \${duration} seconds\"
  " 2>/dev/null

echo ""
echo "Load test completed!"
echo ""
echo "Check results with:"
echo "   kubectl get hpa -n kubeflow"
echo "   kubectl get pods -n kubeflow | grep ml-pipeline"
