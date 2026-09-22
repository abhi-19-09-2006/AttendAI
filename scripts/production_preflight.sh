#!/usr/bin/env bash
#
# AttendAI Production Preflight Validation
#
# Validates production configuration before deployment.
# Checks all critical settings without exposing secret values.
#
# Usage:
#   ./scripts/production_preflight.sh
#   ./scripts/production_preflight.sh --env-file .env.prod
#

set -euo pipefail

# Configuration
ENV_FILE="${1:---env-file}"
if [[ "$ENV_FILE" == "--env-file" ]]; then
    ENV_FILE="${2:-.env.prod}"
fi

EXIT_CODE=0
CHECKS_PASSED=0
CHECKS_FAILED=0

echo "=========================================="
echo "AttendAI Production Preflight Validation"
echo "=========================================="
echo "Environment file: ${ENV_FILE}"
echo ""

# Helper functions
pass() {
    echo "✓ $1"
    ((CHECKS_PASSED++))
}

fail() {
    echo "✗ $1"
    ((CHECKS_FAILED++))
    EXIT_CODE=1
}

warn() {
    echo "⚠ $1"
}

check_env_var() {
    local var_name="$1"
    local var_value="${!var_name:-}"
    
    if [[ -z "$var_value" ]]; then
        fail "$var_name is not set"
        return 1
    fi
    
    # Check for unsafe placeholders
    if echo "$var_value" | grep -qi "your-\|change-in-production\|placeholder"; then
        fail "$var_name contains unsafe placeholder value"
        return 1
    fi
    
    pass "$var_name is configured"
    return 0
}

check_secret_length() {
    local var_name="$1"
    local min_length="${2:-32}"
    local var_value="${!var_name:-}"
    
    if [[ ${#var_value} -lt $min_length ]]; then
        fail "$var_name must be at least $min_length characters (current: ${#var_value})"
        return 1
    fi
    
    pass "$var_name meets minimum length requirement"
    return 0
}

# Load environment file
if [[ ! -f "$ENV_FILE" ]]; then
    fail "Environment file not found: $ENV_FILE"
    exit 1
fi

echo "Loading environment from: $ENV_FILE"
set -a
source "$ENV_FILE"
set +a
echo ""

# 1. Application Mode
echo "1. Application Mode"
if [[ "${APP_ENV:-}" == "production" ]]; then
    pass "APP_ENV is production"
else
    fail "APP_ENV must be 'production' (current: ${APP_ENV:-unset})"
fi

if [[ "${DEBUG:-}" == "false" ]]; then
    pass "DEBUG is disabled"
else
    fail "DEBUG must be 'false' in production (current: ${DEBUG:-unset})"
fi
echo ""

# 2. Security Secrets
echo "2. Security Secrets"
check_env_var "SECRET_KEY"
check_secret_length "SECRET_KEY" 32

check_env_var "JWT_SECRET_KEY"
check_secret_length "JWT_SECRET_KEY" 32
echo ""

# 3. Database Configuration
echo "3. Database Configuration"
check_env_var "DATABASE_URL"

if echo "${DATABASE_URL:-}" | grep -q "attendai_dev_password"; then
    fail "DATABASE_URL contains development password"
elif echo "${DATABASE_URL:-}" | grep -q "localhost"; then
    warn "DATABASE_URL uses localhost (ensure this is intentional for production)"
    pass "DATABASE_URL is configured"
else
    pass "DATABASE_URL is configured"
fi

if echo "${DATABASE_URL:-}" | grep -q "postgresql://"; then
    pass "DATABASE_URL uses PostgreSQL"
else
    fail "DATABASE_URL must use PostgreSQL"
fi
echo ""

# 4. Redis Configuration
echo "4. Redis Configuration"
check_env_var "REDIS_URL"

if echo "${REDIS_URL:-}" | grep -q "redis://"; then
    pass "REDIS_URL uses Redis protocol"
else
    fail "REDIS_URL must use Redis protocol"
fi
echo ""

# 5. CORS Configuration
echo "5. CORS Configuration"
check_env_var "CORS_ORIGINS"

if echo "${CORS_ORIGINS:-}" | grep -q "\*"; then
    fail "CORS_ORIGINS must not contain wildcard '*' in production"
elif echo "${CORS_ORIGINS:-}" | grep -q "localhost"; then
    fail "CORS_ORIGINS must not contain 'localhost' in production"
else
    pass "CORS_ORIGINS is production-safe"
fi
echo ""

# 6. Vapi Configuration
echo "6. Vapi Configuration"
check_env_var "VAPI_API_KEY"
check_env_var "VAPI_WEBHOOK_SECRET"
check_secret_length "VAPI_WEBHOOK_SECRET" 32
check_env_var "VAPI_PHONE_NUMBER_ID"
check_env_var "VAPI_BASE_URL"

if [[ "${VAPI_BASE_URL:-}" == "https://api.vapi.ai" ]]; then
    pass "VAPI_BASE_URL is production Vapi API"
else
    warn "VAPI_BASE_URL is not standard production URL: ${VAPI_BASE_URL:-unset}"
fi
echo ""

# 7. LLM Provider Configuration
echo "7. LLM Provider Configuration"
LLM_PROVIDER="${LLM_PROVIDER:-openai}"

if [[ "$LLM_PROVIDER" == "openai" ]]; then
    pass "LLM_PROVIDER is openai"
    check_env_var "OPENAI_API_KEY"
    if [[ -n "${ANTHROPIC_API_KEY:-}" ]]; then
        warn "ANTHROPIC_API_KEY is set but not used (LLM_PROVIDER=openai)"
    fi
elif [[ "$LLM_PROVIDER" == "anthropic" ]]; then
    pass "LLM_PROVIDER is anthropic"
    check_env_var "ANTHROPIC_API_KEY"
    if [[ -n "${OPENAI_API_KEY:-}" ]]; then
        warn "OPENAI_API_KEY is set but not used (LLM_PROVIDER=anthropic)"
    fi
else
    fail "LLM_PROVIDER must be 'openai' or 'anthropic' (current: $LLM_PROVIDER)"
fi
echo ""

# 8. Frontend Configuration
echo "8. Frontend Configuration"
check_env_var "NEXT_PUBLIC_API_URL"

if echo "${NEXT_PUBLIC_API_URL:-}" | grep -q "localhost"; then
    fail "NEXT_PUBLIC_API_URL must not use localhost in production"
else
    pass "NEXT_PUBLIC_API_URL is production-safe"
fi

check_env_var "NEXT_PUBLIC_APP_NAME"
echo ""

# 9. Retention & Security Settings
echo "9. Retention & Security Settings"
if [[ -n "${TRANSCRIPT_RETENTION_DAYS:-}" ]]; then
    pass "TRANSCRIPT_RETENTION_DAYS is configured (${TRANSCRIPT_RETENTION_DAYS} days)"
else
    warn "TRANSCRIPT_RETENTION_DAYS not set (using default)"
fi

if [[ -n "${RECORDING_RETENTION_DAYS:-}" ]]; then
    pass "RECORDING_RETENTION_DAYS is configured (${RECORDING_RETENTION_DAYS} days)"
else
    warn "RECORDING_RETENTION_DAYS not set (using default)"
fi

if [[ -n "${AUDIT_LOG_RETENTION_DAYS:-}" ]]; then
    pass "AUDIT_LOG_RETENTION_DAYS is configured (${AUDIT_LOG_RETENTION_DAYS} days)"
else
    warn "AUDIT_LOG_RETENTION_DAYS not set (using default)"
fi
echo ""

# 10. Rate Limiting
echo "10. Rate Limiting"
if [[ -n "${RATE_LIMIT_PER_MINUTE:-}" ]]; then
    pass "RATE_LIMIT_PER_MINUTE is configured (${RATE_LIMIT_PER_MINUTE}/min)"
else
    warn "RATE_LIMIT_PER_MINUTE not set (using default)"
fi

if [[ -n "${CALL_RATE_LIMIT_PER_HOUR:-}" ]]; then
    pass "CALL_RATE_LIMIT_PER_HOUR is configured (${CALL_RATE_LIMIT_PER_HOUR}/hour)"
else
    warn "CALL_RATE_LIMIT_PER_HOUR not set (using default)"
fi
echo ""

# Summary
echo "=========================================="
echo "Production Preflight Summary"
echo "=========================================="
echo "Checks Passed: ${CHECKS_PASSED}"
echo "Checks Failed: ${CHECKS_FAILED}"
echo ""

if [[ $EXIT_CODE -eq 0 ]]; then
    echo "✓ All production preflight checks passed"
    echo ""
    echo "Next steps:"
    echo "  1. Review deployment order in RELEASE_CHECKLIST.md"
    echo "  2. Backup production database"
    echo "  3. Apply database migrations"
    echo "  4. Deploy backend, worker, frontend"
    echo "  5. Run production smoke tests"
    echo "  6. Monitor post-release health"
else
    echo "✗ Some production preflight checks failed"
    echo ""
    echo "Fix the issues above before deploying to production."
fi

exit $EXIT_CODE
