#!/bin/bash

# Test database load with multiple concurrent app pods
# This script will scale the app and monitor database connections

echo "=== Database Load Test ==="
echo "Testing MySQL StatefulSet with concurrent connections"
echo ""

# Check if MySQL StatefulSet is running
echo "Checking MySQL StatefulSet status..."
MYSQL_READY=$(kubectl get statefulset mysql-statefulset -n kubeflow -o jsonpath='{.status.readyReplicas}' 2>/dev/null || echo "0")

if [ "$MYSQL_READY" != "1" ]; then
    echo "ERROR: MySQL StatefulSet is not ready"
    echo "Please deploy MySQL first: kubectl apply -f mysql-statefulset.yaml"
    exit 1
fi

echo "MySQL StatefulSet: READY"
echo ""

# Function to get MySQL connection count
get_connection_count() {
    kubectl exec -n kubeflow mysql-statefulset-0 -- \
        mysql -uroot -p$(kubectl get secret mysql-secret -n kubeflow -o jsonpath='{.data.root-password}' | base64 -d) \
        -e "SELECT COUNT(*) as connections FROM information_schema.processlist;" \
        2>/dev/null | tail -1
}

# Function to show connection details
show_connections() {
    echo "=== Database Connection Stats ==="
    kubectl exec -n kubeflow mysql-statefulset-0 -- \
        mysql -uroot -p$(kubectl get secret mysql-secret -n kubeflow -o jsonpath='{.data.root-password}' | base64 -d) \
        -e "
        SELECT
            COUNT(*) as total_connections,
            SUM(IF(command='Sleep', 1, 0)) as idle_connections,
            SUM(IF(command!='Sleep', 1, 0)) as active_connections,
            SUM(IF(user='kubeflow', 1, 0)) as app_connections
        FROM information_schema.processlist;
        " 2>/dev/null
}

# Scale test
echo "Current app pod count:"
kubectl get deployment mysql-test-app -n kubeflow 2>/dev/null || echo "  App not deployed yet"
echo ""

read -p "Scale app to how many pods? (default: 10): " REPLICAS
REPLICAS=${REPLICAS:-10}

echo ""
echo "Scaling mysql-test-app to $REPLICAS replicas..."
kubectl scale deployment mysql-test-app -n kubeflow --replicas=$REPLICAS

echo "Waiting for pods to be ready..."
kubectl wait --for=condition=ready pod -l app=mysql-test-app -n kubeflow --timeout=180s

echo ""
echo "=== Current Status ==="
kubectl get pods -n kubeflow -l app=mysql-test-app
echo ""

# Monitor connections
echo "=== Monitoring Database Connections ==="
echo "Press Ctrl+C to stop monitoring"
echo ""

while true; do
    clear
    echo "=== Database Load Test Monitor ==="
    echo "Time: $(date '+%Y-%m-%d %H:%M:%S')"
    echo ""

    echo "--- App Pods ---"
    kubectl get pods -n kubeflow -l app=mysql-test-app --no-headers 2>/dev/null | \
        awk '{print $3}' | sort | uniq -c | \
        awk '{printf "%-15s: %s\n", $2, $1}'
    echo ""

    echo "--- MySQL Pod ---"
    kubectl get pod mysql-statefulset-0 -n kubeflow --no-headers 2>/dev/null | \
        awk '{printf "Status: %s | Restarts: %s | Age: %s\n", $3, $4, $5}'
    echo ""

    show_connections
    echo ""

    echo "--- MySQL Resource Usage ---"
    kubectl top pod mysql-statefulset-0 -n kubeflow 2>/dev/null || echo "  metrics-server not available"
    echo ""

    echo "--- Connection Pool Info ---"
    echo "Expected connections: $REPLICAS pods × 10 pool_size = $((REPLICAS * 10)) connections"
    echo "Max possible: $REPLICAS pods × (10 + 5 overflow) = $((REPLICAS * 15)) connections"
    echo ""

    sleep 5
done
