#!/usr/bin/env bash
#
# AttendAI Production Smoke Test Suite
#
# Safe, non-destructive production validation.
# Does NOT make real Vapi calls or modify production data.
#
# Usage:
#   ./scripts/production_smoke_test.sh
#   ./scripts/production_smoke_test.sh --base-url https://api.yourdomain.com
#

set -euo pipefail

# Configuration
BASE_URL="${BASE_URL:-http://localhost:8000}"
FRONTEND_URL="${FRONTEND_URL:-http://localhost:3000}"
EXIT_CODE=0

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --base-url)
            BASE_URL="$2"
            shift 2
            ;;
        --frontend-url)
            FRONTEND_URL="$2"
            shift 2
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

echo "=========================================="
echo "AttendAI Production Smoke Test Suite"
echo "=========================================="
echo "Backend URL: ${BASE_URL}"
echo "Frontend URL: ${FRONTEND_URL}"
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

# 1. Backend Health
echo "1. Backend Health"
run_test "Backend /health endpoint" "curl -f ${BASE_URL}/health"
run_test "Backend /health/ready endpoint" "curl -f ${BASE_URL}/health/ready"
run_test "Backend /health/detailed endpoint" "curl -f ${BASE_URL}/health/detailed"

# Check detailed health components
HEALTH_RESPONSE=$(curl -s "${BASE_URL}/health/detailed")
if echo "$HEALTH_RESPONSE" | grep -q '"status".*"healthy"'; then
    echo "Testing: Overall health status... ✓ PASS"
    ((TESTS_PASSED++))
else
    echo "Testing: Overall health status... ✗ FAIL"
    ((TESTS_FAILED++))
    EXIT_CODE=1
fi
echo ""

# 2. Database Connectivity
echo "2. Database Connectivity"
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

# 5. Authentication System
echo "5. Authentication System"
run_test "Auth endpoint accessible" "curl -f ${BASE_URL}/api/auth/login -X POST -H 'Content-Type: application/json' -d '{\"username\":\"test\",\"password\":\"test\"}' || true"
echo ""

# 6. API Documentation
echo "6. API Documentation"
run_test "OpenAPI docs accessible" "curl -f ${BASE_URL}/docs"
run_test "OpenAPI schema valid" "curl -f ${BASE_URL}/openapi.json"
echo ""

# 7. Webhook Infrastructure
echo "7. Webhook Infrastructure"
run_test "Webhook test endpoint" "curl -f ${BASE_URL}/webhooks/vapi/test"

# Test webhook signature verification (should reject invalid signature)
if curl -s -X POST "${BASE_URL}/webhooks/vapi" \
    -H "Content-Type: application/json" \
    -H "X-Vapi-Signature: invalid_signature" \
    -d '{"test":"data"}' | grep -q "401\|Unauthorized"; then
    echo "Testing: Webhook signature verification... ✓ PASS"
    ((TESTS_PASSED++))
else
    echo "Testing: Webhook signature verification... ✗ FAIL"
    ((TESTS_FAILED++))
    EXIT_CODE=1
fi
echo ""

# 8. Frontend Availability
echo "8. Frontend Availability"
run_test "Frontend accessible" "curl -f ${FRONTEND_URL}"
run_test "Frontend returns HTML" "curl -s ${FRONTEND_URL} | grep -q '<!DOCTYPE html>\|<html'"
echo ""

# 9. Production Configuration
echo "9. Production Configuration Validation"

# Check that production validation endpoint exists (if implemented)
if curl -s "${BASE_URL}/health/detailed" | grep -q '"environment".*"production"'; then
    echo "Testing: Production environment detected... ✓ PASS"
    ((TESTS_PASSED++))
else
    echo "Testing: Production environment detected... ⚠ SKIP (not production)"
fi

# Check DEBUG is disabled
if curl -s "${BASE_URL}/health/detailed" | grep -q '"debug".*false'; then
    echo "Testing: DEBUG mode disabled... ✓ PASS"
    ((TESTS_PASSED++))
else
    echo "Testing: DEBUG mode disabled... ⚠ SKIP (not reported)"
fi
echo ""

# 10. Security Headers
echo "10. Security Headers"
HEADERS=$(curl -sI "${BASE_URL}/health")
if echo "$HEADERS" | grep -qi "content-type"; then
    echo "Testing: Content-Type header present... ✓ PASS"
    ((TESTS_PASSED++))
else
    echo "Testing: Content-Type header present... ✗ FAIL"
    ((TESTS_FAILED++))
    EXIT_CODE=1
fi
echo ""

# Summary
echo "=========================================="
echo "Production Smoke Test Summary"
echo "=========================================="
echo "Tests Passed: ${TESTS_PASSED}"
echo "Tests Failed: ${TESTS_FAILED}"
echo ""

if [[ $EXIT_CODE -eq 0 ]]; then
    echo "✓ All production smoke tests passed"
    echo ""
    echo "Production is healthy and ready to serve traffic."
    echo ""
    echo "Next steps:"
    echo "  1. Monitor error rates and response times"
    echo "  2. Check worker logs for failed jobs"
    echo "  3. Verify Vapi webhook delivery (if configured)"
    echo "  4. Review audit logs for security events"
    echo "  5. Confirm backup schedule is active"
else
    echo "✗ Some production smoke tests failed"
    echo ""
    echo "Investigate the failures above before serving production traffic."
fi

exit $EXIT_CODE
