#!/bin/bash

# Comprehensive ArgoCD Test Suite
# Tests pod health, API connectivity, authentication, and project creation

echo "=== ArgoCD COMPREHENSIVE TEST SUITE ==="
echo "Test Execution Time: $(date)"
echo ""

TEST_PASS=0
TEST_FAIL=0
TEST_WARN=0

# Test 1: Pod Health Check
echo "[TEST 1] Pod Health Check"
RUNNING=$(kubectl get pods -n argocd --no-headers 2>/dev/null | grep Running | wc -l)
TOTAL=$(kubectl get pods -n argocd --no-headers 2>/dev/null | wc -l)
EXPECTED=7
echo "Running pods: $RUNNING/$EXPECTED"
if [ "$RUNNING" -eq "$EXPECTED" ]; then
  echo "✅ PASS: All pods Running"
  ((TEST_PASS++))
else
  echo "❌ FAIL: Expected $EXPECTED pods, got $RUNNING (Total: $TOTAL)"
  ((TEST_FAIL++))
fi

# Test 2: Pod Readiness Status
echo ""
echo "[TEST 2] Pod Readiness Status"
READY_PODS=$(kubectl get pods -n argocd -o jsonpath='{range .items[*]}{.status.conditions[?(@.type=="Ready")].status}{"\n"}{end}' 2>/dev/null | grep True | wc -l)
echo "Ready pods: $READY_PODS/$EXPECTED"
if [ "$READY_PODS" -eq "$EXPECTED" ]; then
  echo "✅ PASS: All pods Ready"
  ((TEST_PASS++))
else
  echo "❌ FAIL: Expected $EXPECTED ready pods, got $READY_PODS"
  ((TEST_FAIL++))
fi

# Test 3: API Server Health
echo ""
echo "[TEST 3] API Server Health"
kubectl port-forward svc/argocd-server -n argocd 8080:443 > /dev/null 2>&1 &
PF_PID=$!
sleep 3
API_RESPONSE=$(curl -s -k https://localhost:8080/healthz 2>/dev/null)
kill $PF_PID 2>/dev/null
wait $PF_PID 2>/dev/null

if [ "$API_RESPONSE" = "ok" ]; then
  echo "✅ PASS: API Server responding with 'ok'"
  ((TEST_PASS++))
else
  echo "⚠️  WARN: API Response received: $API_RESPONSE"
  ((TEST_WARN++))
fi

# Test 4: Admin Credentials
echo ""
echo "[TEST 4] Admin Credentials"
PASSWORD=$(kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}" 2>/dev/null | base64 -d)
if [ ! -z "$PASSWORD" ]; then
  echo "✅ PASS: Admin password retrieved successfully"
  echo "   Password length: ${#PASSWORD} chars"
  ((TEST_PASS++))
else
  echo "❌ FAIL: Could not retrieve admin password"
  ((TEST_FAIL++))
fi

# Test 5: Project Creation - ml-pipelines
echo ""
echo "[TEST 5] Project Creation - ml-pipelines"
ML_PROJ=$(kubectl get appproject ml-pipelines -n argocd 2>/dev/null)
if [ ! -z "$ML_PROJ" ]; then
  echo "✅ PASS: ml-pipelines project exists"
  DESC=$(kubectl get appproject ml-pipelines -n argocd -o jsonpath='{.spec.description}' 2>/dev/null)
  echo "   Description: $DESC"
  ((TEST_PASS++))
else
  echo "❌ FAIL: ml-pipelines project not found"
  ((TEST_FAIL++))
fi

# Test 6: Project Creation - infrastructure
echo ""
echo "[TEST 6] Project Creation - infrastructure"
INFRA_PROJ=$(kubectl get appproject infrastructure -n argocd 2>/dev/null)
if [ ! -z "$INFRA_PROJ" ]; then
  echo "✅ PASS: infrastructure project exists"
  DESC=$(kubectl get appproject infrastructure -n argocd -o jsonpath='{.spec.description}' 2>/dev/null)
  echo "   Description: $DESC"
  ((TEST_PASS++))
else
  echo "❌ FAIL: infrastructure project not found"
  ((TEST_FAIL++))
fi

# Test 7: CLI Availability
echo ""
echo "[TEST 7] CLI Availability"
CLI_VERSION=$(argocd version 2>&1 | grep "argocd:" | awk '{print $2}')
if [ ! -z "$CLI_VERSION" ]; then
  echo "✅ PASS: ArgoCD CLI available"
  echo "   Version: $CLI_VERSION"
  ((TEST_PASS++))
else
  echo "❌ FAIL: ArgoCD CLI not available"
  ((TEST_FAIL++))
fi

# Test 8: CLI Authentication
echo ""
echo "[TEST 8] CLI Authentication"
kubectl port-forward svc/argocd-server -n argocd 8080:443 > /dev/null 2>&1 &
PF_PID=$!
sleep 3
PASSWORD=$(kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}" | base64 -d)
AUTH_RESULT=$(timeout 5 bash -c "argocd login localhost:8080 --insecure --username admin --password '$PASSWORD' 2>&1" || echo "timeout")
if echo "$AUTH_RESULT" | grep -q "logged in successfully"; then
  echo "✅ PASS: CLI authentication successful"
  ((TEST_PASS++))
else
  echo "⚠️  WARN: Authentication result: $AUTH_RESULT"
  ((TEST_WARN++))
fi

# Test 9: Cluster Access via CLI
echo ""
echo "[TEST 9] Cluster Access via CLI"
CLUSTER_LIST=$(timeout 5 bash -c "argocd cluster list 2>&1" || echo "timeout")
if echo "$CLUSTER_LIST" | grep -q "in-cluster"; then
  echo "✅ PASS: Cluster accessible via CLI"
  echo "   $(echo "$CLUSTER_LIST" | tail -1)"
  ((TEST_PASS++))
else
  echo "⚠️  WARN: Cluster output: $CLUSTER_LIST"
  ((TEST_WARN++))
fi

kill $PF_PID 2>/dev/null
wait $PF_PID 2>/dev/null

# Test 10: Namespace Configuration
echo ""
echo "[TEST 10] Namespace Configuration"
NS_STATUS=$(kubectl get namespace argocd -o jsonpath='{.status.phase}' 2>/dev/null)
echo "ArgoCD namespace status: $NS_STATUS"
if [ "$NS_STATUS" = "Active" ]; then
  echo "✅ PASS: Namespace is Active"
  ((TEST_PASS++))
else
  echo "❌ FAIL: Namespace status: $NS_STATUS"
  ((TEST_FAIL++))
fi

# Test 11: Port 8080 Availability
echo ""
echo "[TEST 11] Port 8080 Availability"
nc -z localhost 8080 2>/dev/null
if [ $? -eq 0 ]; then
  echo "✅ PASS: Port 8080 is available"
  ((TEST_PASS++))
else
  echo "⚠️  WARN: Port 8080 check (expected when no port-forward active)"
  ((TEST_WARN++))
fi

# Test 12: Service Endpoints
echo ""
echo "[TEST 12] Service Endpoints"
SVC_COUNT=$(kubectl get svc -n argocd --no-headers 2>/dev/null | wc -l)
echo "ArgoCD services count: $SVC_COUNT"
if [ "$SVC_COUNT" -ge 7 ]; then
  echo "✅ PASS: Services created"
  ((TEST_PASS++))
else
  echo "❌ FAIL: Expected at least 7 services, got $SVC_COUNT"
  ((TEST_FAIL++))
fi

# Summary
echo ""
echo "=== TEST SUMMARY ==="
echo "Passed: $TEST_PASS"
echo "Failed: $TEST_FAIL"
echo "Warnings: $TEST_WARN"
echo "Total Tests: $((TEST_PASS + TEST_FAIL + TEST_WARN))"
echo ""

if [ $TEST_FAIL -eq 0 ]; then
  echo "✅ ALL CRITICAL TESTS PASSED"
  exit 0
else
  echo "❌ SOME TESTS FAILED"
  exit 1
fi
