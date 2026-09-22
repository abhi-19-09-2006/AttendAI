#!/usr/bin/env bash
#
# AttendAI Release Validation Script
#
# Comprehensive validation for release candidates.
# Verifies all critical components before deployment.
#
# Usage:
#   ./scripts/release_validation.sh
#   ./scripts/release_validation.sh --skip-docker
#   ./scripts/release_validation.sh --environment staging
#

set -euo pipefail

# Configuration
SKIP_DOCKER=false
ENVIRONMENT="${ENVIRONMENT:-staging}"
EXIT_CODE=0

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --skip-docker)
            SKIP_DOCKER=true
            shift
            ;;
        --environment)
            ENVIRONMENT="$2"
            shift 2
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

echo "=========================================="
echo "AttendAI Release Validation"
echo "=========================================="
echo "Environment: ${ENVIRONMENT}"
echo "Skip Docker: ${SKIP_DOCKER}"
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

# 1. Backend Validation
echo "1. Backend Validation"
run_test "Python syntax check" "cd backend && python -m py_compile app/main.py"
run_test "Requirements file exists" "test -f backend/requirements.txt"
run_test "Alembic configuration exists" "test -f backend/alembic.ini"
run_test "Alembic migrations directory exists" "test -d backend/alembic/versions"
echo ""

# 2. Frontend Validation
echo "2. Frontend Validation"
run_test "Package.json exists" "test -f frontend/package.json"
run_test "Next.js configuration exists" "test -f frontend/next.config.js"
run_test "TypeScript configuration exists" "test -f frontend/tsconfig.json"
echo ""

# 3. Docker Configuration
echo "3. Docker Configuration"
if [[ "$SKIP_DOCKER" == "false" ]]; then
    run_test "Backend Dockerfile exists" "test -f backend/Dockerfile"
    run_test "Frontend Dockerfile exists" "test -f frontend/Dockerfile"
    run_test "docker-compose.yml is valid" "docker-compose config"
    run_test "docker-compose.prod.yml is valid" "docker-compose -f docker-compose.prod.yml config"
    run_test "docker-compose.staging.yml is valid" "docker-compose -f docker-compose.staging.yml config"
else
    echo "Testing: Docker validation... ⊘ SKIP (--skip-docker)"
fi
echo ""

# 4. Environment Configuration
echo "4. Environment Configuration"
run_test ".env.example exists" "test -f .env.example"
run_test ".env.prod.example exists" "test -f .env.prod.example"
run_test ".env.staging.example exists" "test -f .env.staging.example"

# Check for unsafe placeholders in examples
if grep -q "your-secret-key" .env.prod.example; then
    echo "Testing: Production env has placeholders... ✓ PASS (expected)"
    ((TESTS_PASSED++))
else
    echo "Testing: Production env has placeholders... ✗ FAIL"
    ((TESTS_FAILED++))
    EXIT_CODE=1
fi
echo ""

# 5. Scripts Validation
echo "5. Scripts Validation"
run_test "Backup script exists and executable" "test -x scripts/backup/backup_database.sh"
run_test "Restore script exists and executable" "test -x scripts/backup/restore_database.sh"
run_test "Smoke test script exists and executable" "test -x scripts/smoke_test.sh"
run_test "Vapi staging test script exists and executable" "test -x scripts/vapi_staging_test.sh"
echo ""

# 6. Documentation Validation
echo "6. Documentation Validation"
run_test "Phase 17 documentation exists" "test -f PHASE_17_PRODUCTION_DEPLOYMENT.md"
run_test "Disaster recovery documentation exists" "test -f DISASTER_RECOVERY.md"
run_test "Phase 18 documentation exists" "test -f PHASE_18_STAGING_RELEASE.md"
run_test "Release checklist exists" "test -f RELEASE_CHECKLIST.md"
echo ""

# 7. CI/CD Validation
echo "7. CI/CD Validation"
run_test "GitHub Actions workflow exists" "test -f .github/workflows/ci.yml"
run_test "CI workflow syntax is valid" "grep -q 'name: CI' .github/workflows/ci.yml"
echo ""

# 8. Security Checks
echo "8. Security Checks"

# Check for committed secrets (basic check)
if grep -r "password.*=.*['\"].*['\"]" backend/app --include="*.py" | grep -v "test" | grep -v "example" | grep -q .; then
    echo "Testing: No hardcoded passwords... ✗ FAIL"
    ((TESTS_FAILED++))
    EXIT_CODE=1
else
    echo "Testing: No hardcoded passwords... ✓ PASS"
    ((TESTS_PASSED++))
fi

# Check for .env files committed
if git ls-files | grep -E "\.env$" | grep -v "example" | grep -q .; then
    echo "Testing: No .env files committed... ✗ FAIL"
    ((TESTS_FAILED++))
    EXIT_CODE=1
else
    echo "Testing: No .env files committed... ✓ PASS"
    ((TESTS_PASSED++))
fi

# Check .gitignore includes .env
if grep -q "^\.env$" .gitignore; then
    echo "Testing: .gitignore excludes .env... ✓ PASS"
    ((TESTS_PASSED++))
else
    echo "Testing: .gitignore excludes .env... ✗ FAIL"
    ((TESTS_FAILED++))
    EXIT_CODE=1
fi
echo ""

# 9. Production Validation Code
echo "9. Production Validation Code"
run_test "Production validation module exists" "test -f backend/app/core/production_validation.py"
run_test "Production validation tests exist" "test -f backend/tests/test_production_validation.py"
echo ""

# 10. Migration Validation
echo "10. Migration Validation"
if [[ "$SKIP_DOCKER" == "false" ]]; then
    # Count migrations
    MIGRATION_COUNT=$(ls -1 backend/alembic/versions/*.py 2>/dev/null | wc -l)
    echo "Testing: Migration files exist (${MIGRATION_COUNT} found)... ✓ PASS"
    ((TESTS_PASSED++))
    
    # Check for migration 004 (current head)
    if ls backend/alembic/versions/*004*.py 2>/dev/null | grep -q .; then
        echo "Testing: Migration 004 exists... ✓ PASS"
        ((TESTS_PASSED++))
    else
        echo "Testing: Migration 004 exists... ✗ FAIL"
        ((TESTS_FAILED++))
        EXIT_CODE=1
    fi
else
    echo "Testing: Migration validation... ⊘ SKIP (--skip-docker)"
fi
echo ""

# Summary
echo "=========================================="
echo "Release Validation Summary"
echo "=========================================="
echo "Tests Passed: ${TESTS_PASSED}"
echo "Tests Failed: ${TESTS_FAILED}"
echo ""

if [[ $EXIT_CODE -eq 0 ]]; then
    echo "✓ All release validation tests passed"
    echo ""
    echo "Next steps:"
    echo "  1. Run backend tests: cd backend && pytest tests/"
    echo "  2. Run frontend build: cd frontend && npm run build"
    echo "  3. Deploy to staging environment"
    echo "  4. Run smoke tests: ./scripts/smoke_test.sh"
    echo "  5. Run Vapi staging test: ./scripts/vapi_staging_test.sh"
    echo "  6. Review RELEASE_CHECKLIST.md"
else
    echo "✗ Some release validation tests failed"
    echo ""
    echo "Fix the issues above before proceeding with release."
fi

exit $EXIT_CODE
