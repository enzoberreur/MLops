#!/bin/bash
# Comprehensive MLOps Project Test Script
# This script tests all components of the MLOps stack

echo "======================================"
echo "MLOps Project Deployment Test Script"
echo "======================================"
echo ""

# Color codes for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test results counter
PASSED=0
FAILED=0

# Function to test a service
test_service() {
    local name=$1
    local url=$2
    local expected=$3
    
    echo -n "Testing $name... "
    response=$(curl -s -o /dev/null -w "%{http_code}" "$url" 2>&1)
    
    if [ "$response" == "$expected" ]; then
        echo -e "${GREEN}✓ PASSED${NC} (HTTP $response)"
        PASSED=$((PASSED + 1))
    else
        echo -e "${RED}✗ FAILED${NC} (Expected: $expected, Got: $response)"
        FAILED=$((FAILED + 1))
    fi
}

# Function to check if a service is accessible
check_service() {
    local name=$1
    local url=$2
    
    echo -n "Checking $name... "
    if curl -s "$url" > /dev/null 2>&1; then
        echo -e "${GREEN}✓ ACCESSIBLE${NC}"
        PASSED=$((PASSED + 1))
    else
        echo -e "${RED}✗ NOT ACCESSIBLE${NC}"
        FAILED=$((FAILED + 1))
    fi
}

echo "1. Testing Core Services"
echo "------------------------"

# Test MinIO
check_service "MinIO (S3 Storage)" "http://localhost:9000/minio/health/live"

# Test MLflow
test_service "MLflow Tracking Server" "http://localhost:5500/health" "200"

# Test FastAPI
test_service "FastAPI Health Endpoint" "http://localhost:8000/health" "200"

# Test Prometheus
test_service "Prometheus Metrics" "http://localhost:9090/-/healthy" "200"

# Test Grafana
test_service "Grafana Dashboard" "http://localhost:3000/api/health" "200"

# Test StatSD Exporter
check_service "StatSD Exporter" "http://localhost:9102/metrics"

echo ""
echo "2. Testing Airflow"
echo "------------------"

# Wait a bit for Airflow to be fully ready
echo "Waiting for Airflow to be ready (this may take a minute)..."
for i in {1..30}; do
    if curl -s -u admin:admin http://localhost:8080/health > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Airflow is ready${NC}"
        PASSED=$((PASSED + 1))
        break
    fi
    echo -n "."
    sleep 2
done

echo ""
echo "3. Testing Web Interfaces"
echo "-------------------------"

# Test Streamlit
check_service "Streamlit Web App" "http://localhost:8501"

echo ""
echo "4. Checking Docker Containers"
echo "-----------------------------"

running_containers=$(docker compose ps --filter "status=running" --format "{{.Service}}" | wc -l)
total_expected=10

echo "Running containers: $running_containers/$total_expected"
if [ "$running_containers" -ge 8 ]; then
    echo -e "${GREEN}✓ Most services are running${NC}"
    PASSED=$((PASSED + 1))
else
    echo -e "${YELLOW}⚠ Some services might not be running${NC}"
fi

echo ""
echo "======================================"
echo "Test Summary"
echo "======================================"
echo -e "Passed: ${GREEN}$PASSED${NC}"
echo -e "Failed: ${RED}$FAILED${NC}"
echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}✓ All tests passed! Your MLOps stack is ready.${NC}"
    echo ""
    echo "Access URLs:"
    echo "  - Airflow UI:    http://localhost:8080 (admin/admin)"
    echo "  - MLflow UI:     http://localhost:5500"
    echo "  - MinIO Console: http://localhost:9001 (minioadmin/minioadmin)"
    echo "  - FastAPI Docs:  http://localhost:8000/docs"
    echo "  - Streamlit App: http://localhost:8501"
    echo "  - Prometheus:    http://localhost:9090"
    echo "  - Grafana:       http://localhost:3000 (admin/admin)"
else
    echo -e "${YELLOW}⚠ Some tests failed. Check the output above.${NC}"
    exit 1
fi
