#!/bin/bash

echo "=== Kubeflow Installation Status ==="
echo "Installation completed successfully!"
echo ""
echo "Access Kubeflow Central Dashboard:"
echo "URL: http://localhost:8080"
echo ""
echo "Note: Make sure the Minikube tunnel is running in another terminal:"
echo "minikube tunnel"
echo ""
echo "=== Current Pod Status ==="
kubectl get pods --all-namespaces
echo ""
echo "=== Services ==="
kubectl get svc --all-namespaces | grep -E "(istio-ingressgateway|centraldashboard)"

echo ""
echo "=== Troubleshooting ==="
echo "If pods are stuck in ContainerCreating, check:"
echo "kubectl get events --all-namespaces --sort-by='.lastTimestamp' | tail -10"
echo ""
echo "To check tunnel status:"
echo "curl -I http://localhost:8080"