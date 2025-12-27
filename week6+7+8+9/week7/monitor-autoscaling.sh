#!/bin/bash

# Monitor Kubeflow autoscaling behavior
# Run this script in a separate terminal while running the stress test

echo "=== Kubeflow Autoscaling Monitor ==="
echo "Monitoring HPA and Pods..."
echo "Press Ctrl+C to stop"
echo ""

# Color codes
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

while true; do
    clear
    echo -e "${GREEN}=== Kubeflow Autoscaling Monitor ===${NC}"
    echo "Time: $(date '+%Y-%m-%d %H:%M:%S')"
    echo ""

    echo -e "${YELLOW}--- HPA Status ---${NC}"
    kubectl get hpa -n kubeflow 2>/dev/null || echo "No HPA found"
    echo ""

    echo -e "${YELLOW}--- Pod Count by Deployment ---${NC}"
    kubectl get deployments -n kubeflow -o custom-columns=\
NAME:.metadata.name,\
READY:.status.readyReplicas,\
DESIRED:.spec.replicas,\
AVAILABLE:.status.availableReplicas 2>/dev/null
    echo ""

    echo -e "${YELLOW}--- Pods Status ---${NC}"
    kubectl get pods -n kubeflow --no-headers 2>/dev/null | \
        awk '{print $3}' | sort | uniq -c | \
        awk '{printf "%-15s: %s\n", $2, $1}'
    echo ""

    echo -e "${YELLOW}--- ML Pipeline Pods (Target for Load Test) ---${NC}"
    kubectl get pods -n kubeflow -l app=ml-pipeline 2>/dev/null || echo "No ml-pipeline pods"
    echo ""

    echo -e "${YELLOW}--- Resource Usage (Top Pods) ---${NC}"
    kubectl top pods -n kubeflow --sort-by=cpu 2>/dev/null | head -n 6 || \
        echo "metrics-server not available"

    sleep 5
done
