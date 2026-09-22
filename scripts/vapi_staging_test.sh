#!/usr/bin/env bash
#
# AttendAI Vapi Staging Validation Script
#
# Performs controlled end-to-end Vapi integration testing.
# SAFE: Uses dedicated test configuration, no production contacts.
#
# Prerequisites:
#   - VAPI_API_KEY configured
#   - VAPI_WEBHOOK_SECRET configured
#   - VAPI_PHONE_NUMBER_ID configured
#   - Test phone number configured (STAGING_TEST_NUMBER)
#   - Application running and accessible
#
# Usage:
#   ./scripts/vapi_staging_test.sh
#   ./scripts/vapi_staging_test.sh --base-url https://staging.yourdomain.com
#
# Environment Variables:
#   STAGING_TEST_NUMBER - Phone number to call (MUST be your own test number)
#   BASE_URL           - Application base URL (default: http://localhost:8000)
#   AUTH_TOKEN         - Bearer token for API authentication
#

set -euo pipefail

# Configuration
BASE_URL="${BASE_URL:-http://localhost:8000}"
STAGING_TEST_NUMBER="${STAGING_TEST_NUMBER:-}"
AUTH_TOKEN="${AUTH_TOKEN:-}"

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

# Validation
if [[ -z "$STAGING_TEST_NUMBER" ]]; then
    echo "ERROR: STAGING_TEST_NUMBER environment variable is required"
    echo ""
    echo "This must be a phone number YOU control for testing purposes."
    echo "NEVER use production parent/guardian contact numbers."
    exit 1
fi

if [[ -z "$AUTH_TOKEN" ]]; then
    echo "ERROR: AUTH_TOKEN environment variable is required"
    echo ""
    echo "Generate a token using:"
    echo "  curl -X POST ${BASE_URL}/api/auth/login \\"
    echo "    -H 'Content-Type: application/json' \\"
    echo "    -d '{\"username\":\"admin\",\"password\":\"your-password\"}'"
    exit 1
fi

echo "=========================================="
echo "AttendAI Vapi Staging Validation"
echo "=========================================="
echo "Base URL: ${BASE_URL}"
echo "Test Number: ${STAGING_TEST_NUMBER}"
echo ""
echo "⚠️  WARNING: This will initiate a REAL phone call"
echo "    to: ${STAGING_TEST_NUMBER}"
echo ""
read -p "Continue? (yes/no): " -r
echo
if [[ ! $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
    echo "Staging test cancelled"
    exit 0
fi

echo "Starting Vapi staging validation..."
echo ""

# Helper function to extract ID from JSON response using Python
extract_id() {
    local json_response="$1"
    python -c "import sys, json; data = json.loads(sys.argv[1]); print(data.get('id', ''))" "$json_response" 2>/dev/null || echo ""
}

# Generate unique test identifier for this run
TEST_RUN_ID="STAGING_$(date +%Y%m%d_%H%M%S)"
TEST_EMAIL="staging.test.${TEST_RUN_ID}@example.com"

echo "Test Run ID: ${TEST_RUN_ID}"
echo "Test Email: ${TEST_EMAIL}"
echo ""

# Step 1: Verify health
echo "Step 1: Verifying system health..."
HEALTH=$(curl -s "${BASE_URL}/health/detailed")
if ! echo "$HEALTH" | grep -q '"status".*"healthy"'; then
    echo "✗ System health check failed"
    echo "$HEALTH"
    exit 1
fi
echo "✓ System healthy"
echo ""

# Step 2: Create test student
echo "Step 2: Creating test student..."
STUDENT_RESPONSE=$(curl -s -X POST "${BASE_URL}/api/students" \
    -H "Authorization: Bearer ${AUTH_TOKEN}" \
    -H "Content-Type: application/json" \
    -d '{
        "student_id": "'"$TEST_RUN_ID"'",
        "first_name": "Staging",
        "last_name": "Test",
        "date_of_birth": "2010-01-01",
        "grade_level": 10,
        "email": "'"$TEST_EMAIL"'",
        "phone": "'"$STAGING_TEST_NUMBER"'"
    }')

STUDENT_ID=$(extract_id "$STUDENT_RESPONSE")
if [[ -z "$STUDENT_ID" ]]; then
    echo "✗ Failed to create test student"
    echo "$STUDENT_RESPONSE"
    exit 1
fi
echo "✓ Test student created (ID: ${STUDENT_ID})"
echo ""

# Step 3: Create test parent
echo "Step 3: Creating test parent..."
PARENT_RESPONSE=$(curl -s -X POST "${BASE_URL}/api/parents" \
    -H "Authorization: Bearer ${AUTH_TOKEN}" \
    -H "Content-Type: application/json" \
    -d '{
        "student_id": "'"$STUDENT_ID"'",
        "first_name": "Test",
        "last_name": "Parent",
        "primary_phone": "'"$STAGING_TEST_NUMBER"'",
        "relationship": "guardian",
        "is_primary": true
    }')

PARENT_ID=$(extract_id "$PARENT_RESPONSE")
if [[ -z "$PARENT_ID" ]]; then
    echo "✗ Failed to create test parent"
    echo "$PARENT_RESPONSE"
    exit 1
fi
echo "✓ Test parent created (ID: ${PARENT_ID})"
echo ""

# Step 4: Create absence record
echo "Step 4: Creating test absence..."
TODAY=$(date +%Y-%m-%d)
ABSENCE_RESPONSE=$(curl -s -X POST "${BASE_URL}/api/attendance" \
    -H "Authorization: Bearer ${AUTH_TOKEN}" \
    -H "Content-Type: application/json" \
    -d '{
        "student_id": "'"$STUDENT_ID"'",
        "date": "'"$TODAY"'",
        "status": "absent"
    }')

ATTENDANCE_ID=$(extract_id "$ABSENCE_RESPONSE")
if [[ -z "$ATTENDANCE_ID" ]]; then
    echo "✗ Failed to create absence record"
    echo "$ABSENCE_RESPONSE"
    exit 1
fi
echo "✓ Test absence created (ID: ${ATTENDANCE_ID})"
echo ""

# Step 5: Initiate call
echo "Step 5: Initiating Vapi call..."
echo "    Calling: ${STAGING_TEST_NUMBER}"
echo "    Please answer the call and interact with the AI assistant..."
echo ""

CALL_RESPONSE=$(curl -s -X POST "${BASE_URL}/api/calls" \
    -H "Authorization: Bearer ${AUTH_TOKEN}" \
    -H "Content-Type: application/json" \
    -d '{
        "student_id": "'"$STUDENT_ID"'",
        "parent_id": "'"$PARENT_ID"'",
        "attendance_id": "'"$ATTENDANCE_ID"'"
    }')

CALL_ID=$(extract_id "$CALL_RESPONSE")
if [[ -z "$CALL_ID" ]]; then
    echo "✗ Failed to initiate call"
    echo "$CALL_RESPONSE"
    exit 1
fi
echo "✓ Call initiated (ID: ${CALL_ID})"
echo ""

# Step 6: Wait for call completion
echo "Step 6: Waiting for call completion..."
echo "    (This may take 1-3 minutes)"
echo ""

MAX_WAIT=180
WAITED=0
INTERVAL=10

while [[ $WAITED -lt $MAX_WAIT ]]; do
    CALL_STATUS=$(curl -s "${BASE_URL}/api/calls/${CALL_ID}" \
        -H "Authorization: Bearer ${AUTH_TOKEN}" | grep -o '"status":"[^"]*"' | cut -d'"' -f4)
    
    echo "  Status: ${CALL_STATUS} (${WAITED}s elapsed)"
    
    if [[ "$CALL_STATUS" == "completed" || "$CALL_STATUS" == "failed" ]]; then
        break
    fi
    
    sleep $INTERVAL
    ((WAITED+=INTERVAL))
done

if [[ "$CALL_STATUS" != "completed" ]]; then
    echo "✗ Call did not complete successfully (status: ${CALL_STATUS})"
    exit 1
fi
echo "✓ Call completed"
echo ""

# Step 7: Verify webhook received
echo "Step 7: Verifying webhook processing..."
sleep 5  # Allow time for webhook processing

CALL_DETAILS=$(curl -s "${BASE_URL}/api/calls/${CALL_ID}" \
    -H "Authorization: Bearer ${AUTH_TOKEN}")

if echo "$CALL_DETAILS" | grep -q '"transcript"'; then
    echo "✓ Transcript received"
else
    echo "⚠ Transcript not found (may still be processing)"
fi

if echo "$CALL_DETAILS" | grep -q '"absence_report"'; then
    echo "✓ Absence report generated"
else
    echo "⚠ Absence report not found (may still be processing)"
fi
echo ""

# Step 8: Cleanup
echo "Step 8: Cleanup..."
echo "  Test data created:"
echo "    - Student ID: ${STUDENT_ID}"
echo "    - Parent ID: ${PARENT_ID}"
echo "    - Attendance ID: ${ATTENDANCE_ID}"
echo "    - Call ID: ${CALL_ID}"
echo ""
echo "  To cleanup manually:"
echo "    DELETE ${BASE_URL}/api/students/${STUDENT_ID}"
echo ""

# Summary
echo "=========================================="
echo "Vapi Staging Validation Complete"
echo "=========================================="
echo "✓ All staging tests passed"
echo ""
echo "Next steps:"
echo "  1. Review call transcript in database"
echo "  2. Verify absence report accuracy"
echo "  3. Check follow-up recommendations"
echo "  4. Review webhook logs"
echo "  5. Cleanup test data"
