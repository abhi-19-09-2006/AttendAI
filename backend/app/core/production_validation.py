"""
Production Configuration Validation

Validates that production deployments are properly configured and rejects
unsafe placeholder values.
"""
import sys
from typing import List
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger("production_validation")


class ProductionValidationError(Exception):
    """Raised when production configuration is invalid."""
    pass


def validate_production_config() -> None:
    """
    Validate production configuration on startup.
    
    Raises ProductionValidationError if configuration is unsafe for production.
    """
    if not settings.is_production:
        logger.debug("Skipping production validation (not in production mode)")
        return
    
    errors: List[str] = []
    
    # Check for unsafe placeholder secrets
    unsafe_secrets = [
        "your-secret-key",
        "your-jwt-secret-key",
        "your-vapi-api-key",
        "your-vapi-webhook-secret",
        "your-openai-api-key",
        "your-anthropic-api-key",
        "your-nextauth-secret",
        "change-in-production",
    ]
    
    secret_fields = {
        "SECRET_KEY": settings.SECRET_KEY,
        "JWT_SECRET_KEY": settings.JWT_SECRET_KEY,
        "VAPI_API_KEY": settings.VAPI_API_KEY,
        "VAPI_WEBHOOK_SECRET": settings.VAPI_WEBHOOK_SECRET,
        "OPENAI_API_KEY": settings.OPENAI_API_KEY,
        "ANTHROPIC_API_KEY": settings.ANTHROPIC_API_KEY,
    }
    
    for field_name, field_value in secret_fields.items():
        if not field_value:
            errors.append(f"{field_name} is not set")
            continue
        
        for unsafe in unsafe_secrets:
            if unsafe in field_value.lower():
                errors.append(f"{field_name} contains unsafe placeholder value")
                break
        
        # Check minimum length for secrets
        if field_name in ["SECRET_KEY", "JWT_SECRET_KEY"] and len(field_value) < 32:
            errors.append(f"{field_name} must be at least 32 characters")
    
    # Check DEBUG is disabled in production
    if settings.DEBUG:
        errors.append("DEBUG must be False in production")
    
    # Check CORS origins are not overly permissive
    if "*" in settings.cors_origins_list:
        errors.append("CORS_ORIGINS must not contain wildcard '*' in production")
    
    if "http://localhost" in settings.CORS_ORIGINS and settings.is_production:
        errors.append("CORS_ORIGINS should not include localhost in production")
    
    # Check database URL is not using dev credentials
    if "attendai_dev_password" in settings.DATABASE_URL:
        errors.append("DATABASE_URL must not use development password in production")
    
    # Check required Vapi configuration
    if not settings.VAPI_API_KEY:
        errors.append("VAPI_API_KEY is required for production")
    
    if not settings.VAPI_WEBHOOK_SECRET:
        errors.append("VAPI_WEBHOOK_SECRET is required for production")
    
    # Check LLM provider configuration
    if settings.LLM_PROVIDER == "openai" and not settings.OPENAI_API_KEY:
        errors.append("OPENAI_API_KEY is required when LLM_PROVIDER=openai")
    
    if settings.LLM_PROVIDER == "anthropic" and not settings.ANTHROPIC_API_KEY:
        errors.append("ANTHROPIC_API_KEY is required when LLM_PROVIDER=anthropic")
    
    # Report errors
    if errors:
        error_msg = "Production configuration validation failed:\n" + "\n".join(
            f"  - {error}" for error in errors
        )
        logger.error(error_msg)
        raise ProductionValidationError(error_msg)
    
    logger.info("Production configuration validation passed")


def validate_startup() -> None:
    """
    Validate configuration on application startup.
    
    For production: strict validation (fail on errors)
    For development: warnings only
    """
    try:
        validate_production_config()
    except ProductionValidationError as e:
        if settings.is_production:
            logger.critical(f"Production validation failed: {e}")
            sys.exit(1)
        else:
            logger.warning(f"Configuration validation warning: {e}")
