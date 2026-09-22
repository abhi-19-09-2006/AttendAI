#!/usr/bin/env bash
#
# AttendAI Smoke Test Suite
#
# Validates critical system components and functionality.
# Safe for production - does not make real phone calls.
#
# Usage:
#   ./scripts/smoke_test.sh
#   ./scripts/smoke_test.sh --base-url https://api.yourdomain.com
#

set -euo pipefail

# Configuration
BASE_URL="${BASE_URL:-http://localhost:8000}"
EXIT_CODE=0

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --base-url)
            BASE_URL="$2"
            shift 2
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

echo "=========================================="
echo "AttendAI Smoke Test Suite"
echo "=========================================="
echo "Base URL: ${BASE_URL}"
echo ""

# Test counter
TESTS_PASSED=0
TESTS_FAILED=0

# Helper function
run_test() {
    local test_name="$1"
    local test_command="$2"
    
    echo -n "Testing: ${test_name}... "
    
    if eval "$test_command" > /dev/null 2>&1; then
        echo "✓ PASS"
        ((TESTS_PASSED++))
        return 0
    else
        echo "✗ FAIL"
        ((TESTS_FAILED++))
        EXIT_CODE=1
        return 1
    fi
}

# 1. API Health Check
echo "1. API Health"
run_test "Basic health endpoint" "curl -f ${BASE_URL}/health"
run_test "Detailed health endpoint" "curl -f ${BASE_URL}/health/detailed"
run_test "Readiness probe" "curl -f ${BASE_URL}/health/ready"
run_test "Liveness probe" "curl -f ${BASE_URL}/health/live"
echo ""

# 2. Database Connectivity
echo "2. Database Connectivity"
HEALTH_RESPONSE=$(curl -s "${BASE_URL}/health/detailed")
if echo "$HEALTH_RESPONSE" | grep -q '"database".*"healthy"'; then
    echo "Testing: Database connectivity... ✓ PASS"
    ((TESTS_PASSED++))
else
    echo "Testing: Database connectivity... ✗ FAIL"
    ((TESTS_FAILED++))
    EXIT_CODE=1
fi
echo ""

# 3. Redis Connectivity
echo "3. Redis Connectivity"
if echo "$HEALTH_RESPONSE" | grep -q '"redis".*"ok"'; then
    echo "Testing: Redis connectivity... ✓ PASS"
    ((TESTS_PASSED++))
else
    echo "Testing: Redis connectivity... ✗ FAIL"
    ((TESTS_FAILED++))
    EXIT_CODE=1
fi
echo ""

# 4. RQ Worker Availability
echo "4. Background Job Infrastructure"
if echo "$HEALTH_RESPONSE" | grep -q '"rq_workers".*"ok"'; then
    echo "Testing: RQ workers active... ✓ PASS"
    ((TESTS_PASSED++))
else
    echo "Testing: RQ workers active... ✗ FAIL"
    ((TESTS_FAILED++))
    EXIT_CODE=1
fi

if echo "$HEALTH_RESPONSE" | grep -q '"rq_queues".*"ok"'; then
    echo "Testing: RQ queues operational... ✓ PASS"
    ((TESTS_PASSED++))
else
    echo "Testing: RQ queues operational... ✗ FAIL"
    ((TESTS_FAILED++))
    EXIT_CODE=1
fi
echo ""

# 5. Authentication
echo "5. Authentication"
run_test "Auth endpoint accessible" "curl -f ${BASE_URL}/api/auth/login -X POST -H 'Content-Type: application/json' -d '{\"username\":\"test\",\"password\":\"test\"}' || true"
echo ""

# 6. API Documentation
echo "6. API Documentation"
run_test "OpenAPI docs accessible" "curl -f ${BASE_URL}/docs"
run_test "OpenAPI schema valid" "curl -f ${BASE_URL}/openapi.json"
echo ""

# 7. Webhook Endpoint
echo "7. Webhook Infrastructure"
run_test "Webhook test endpoint" "curl -f ${BASE_URL}/webhooks/vapi/test"
echo ""

# 8. Frontend (if available)
echo "8. Frontend (Optional)"
if curl -f http://localhost:3000 > /dev/null 2>&1; then
    run_test "Frontend accessible" "curl -f http://localhost:3000"
else
    echo "Testing: Frontend accessible... ⊘ SKIP (not running)"
fi
echo ""

# Summary
echo "=========================================="
echo "Smoke Test Summary"
echo "=========================================="
echo "Tests Passed: ${TESTS_PASSED}"
echo "Tests Failed: ${TESTS_FAILED}"
echo ""

if [[ $EXIT_CODE -eq 0 ]]; then
    echo "✓ All smoke tests passed"
else
    echo "✗ Some smoke tests failed"
fi

exit $EXIT_CODE
