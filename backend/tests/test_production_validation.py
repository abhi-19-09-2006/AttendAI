"""
Tests for production configuration validation.
"""
import pytest
from unittest.mock import patch
from app.core.production_validation import validate_production_config, ProductionValidationError


class TestProductionValidation:
    """Test production configuration validation."""

    def test_validation_skipped_in_development(self):
        """Validation should be skipped in development mode."""
        with patch("app.core.production_validation.settings") as mock_settings:
            mock_settings.is_production = False
            
            # Should not raise any errors
            validate_production_config()

    def test_validation_passes_with_valid_config(self):
        """Validation should pass with valid production config."""
        with patch("app.core.production_validation.settings") as mock_settings:
            mock_settings.is_production = True
            mock_settings.DEBUG = False
            mock_settings.SECRET_KEY = "a" * 32
            mock_settings.JWT_SECRET_KEY = "b" * 32
            mock_settings.VAPI_API_KEY = "valid-vapi-key"
            mock_settings.VAPI_WEBHOOK_SECRET = "c" * 32
            mock_settings.OPENAI_API_KEY = "valid-openai-key"
            mock_settings.ANTHROPIC_API_KEY = ""
            mock_settings.LLM_PROVIDER = "openai"
            mock_settings.CORS_ORIGINS = "https://example.com"
            mock_settings.cors_origins_list = ["https://example.com"]
            mock_settings.DATABASE_URL = "postgresql://user:strongpass@host:5432/db"
            
            # Should not raise any errors
            validate_production_config()

    def test_validation_fails_with_placeholder_secret(self):
        """Validation should fail with placeholder secrets."""
        with patch("app.core.production_validation.settings") as mock_settings:
            mock_settings.is_production = True
            mock_settings.DEBUG = False
            mock_settings.SECRET_KEY = "your-secret-key-change-in-production"
            mock_settings.JWT_SECRET_KEY = "b" * 32
            mock_settings.VAPI_API_KEY = "valid-vapi-key"
            mock_settings.VAPI_WEBHOOK_SECRET = "c" * 32
            mock_settings.OPENAI_API_KEY = "valid-openai-key"
            mock_settings.ANTHROPIC_API_KEY = ""
            mock_settings.LLM_PROVIDER = "openai"
            mock_settings.CORS_ORIGINS = "https://example.com"
            mock_settings.cors_origins_list = ["https://example.com"]
            mock_settings.DATABASE_URL = "postgresql://user:strongpass@host:5432/db"
            
            with pytest.raises(ProductionValidationError) as exc_info:
                validate_production_config()
            
            assert "SECRET_KEY" in str(exc_info.value)
            assert "unsafe placeholder" in str(exc_info.value)

    def test_validation_fails_with_short_secret(self):
        """Validation should fail with short secrets."""
        with patch("app.core.production_validation.settings") as mock_settings:
            mock_settings.is_production = True
            mock_settings.DEBUG = False
            mock_settings.SECRET_KEY = "short"
            mock_settings.JWT_SECRET_KEY = "b" * 32
            mock_settings.VAPI_API_KEY = "valid-vapi-key"
            mock_settings.VAPI_WEBHOOK_SECRET = "c" * 32
            mock_settings.OPENAI_API_KEY = "valid-openai-key"
            mock_settings.ANTHROPIC_API_KEY = ""
            mock_settings.LLM_PROVIDER = "openai"
            mock_settings.CORS_ORIGINS = "https://example.com"
            mock_settings.cors_origins_list = ["https://example.com"]
            mock_settings.DATABASE_URL = "postgresql://user:strongpass@host:5432/db"
            
            with pytest.raises(ProductionValidationError) as exc_info:
                validate_production_config()
            
            assert "SECRET_KEY" in str(exc_info.value)
            assert "at least 32 characters" in str(exc_info.value)

    def test_validation_fails_with_debug_enabled(self):
        """Validation should fail with DEBUG enabled in production."""
        with patch("app.core.production_validation.settings") as mock_settings:
            mock_settings.is_production = True
            mock_settings.DEBUG = True
            mock_settings.SECRET_KEY = "a" * 32
            mock_settings.JWT_SECRET_KEY = "b" * 32
            mock_settings.VAPI_API_KEY = "valid-vapi-key"
            mock_settings.VAPI_WEBHOOK_SECRET = "c" * 32
            mock_settings.OPENAI_API_KEY = "valid-openai-key"
            mock_settings.ANTHROPIC_API_KEY = ""
            mock_settings.LLM_PROVIDER = "openai"
            mock_settings.CORS_ORIGINS = "https://example.com"
            mock_settings.cors_origins_list = ["https://example.com"]
            mock_settings.DATABASE_URL = "postgresql://user:strongpass@host:5432/db"
            
            with pytest.raises(ProductionValidationError) as exc_info:
                validate_production_config()
            
            assert "DEBUG must be False" in str(exc_info.value)

    def test_validation_fails_with_wildcard_cors(self):
        """Validation should fail with wildcard CORS in production."""
        with patch("app.core.production_validation.settings") as mock_settings:
            mock_settings.is_production = True
            mock_settings.DEBUG = False
            mock_settings.SECRET_KEY = "a" * 32
            mock_settings.JWT_SECRET_KEY = "b" * 32
            mock_settings.VAPI_API_KEY = "valid-vapi-key"
            mock_settings.VAPI_WEBHOOK_SECRET = "c" * 32
            mock_settings.OPENAI_API_KEY = "valid-openai-key"
            mock_settings.ANTHROPIC_API_KEY = ""
            mock_settings.LLM_PROVIDER = "openai"
            mock_settings.CORS_ORIGINS = "*"
            mock_settings.cors_origins_list = ["*"]
            mock_settings.DATABASE_URL = "postgresql://user:strongpass@host:5432/db"
            
            with pytest.raises(ProductionValidationError) as exc_info:
                validate_production_config()
            
            assert "CORS_ORIGINS" in str(exc_info.value)
            assert "wildcard" in str(exc_info.value)

    def test_validation_fails_with_dev_database_password(self):
        """Validation should fail with development database password."""
        with patch("app.core.production_validation.settings") as mock_settings:
            mock_settings.is_production = True
            mock_settings.DEBUG = False
            mock_settings.SECRET_KEY = "a" * 32
            mock_settings.JWT_SECRET_KEY = "b" * 32
            mock_settings.VAPI_API_KEY = "valid-vapi-key"
            mock_settings.VAPI_WEBHOOK_SECRET = "c" * 32
            mock_settings.OPENAI_API_KEY = "valid-openai-key"
            mock_settings.ANTHROPIC_API_KEY = ""
            mock_settings.LLM_PROVIDER = "openai"
            mock_settings.CORS_ORIGINS = "https://example.com"
            mock_settings.cors_origins_list = ["https://example.com"]
            mock_settings.DATABASE_URL = "postgresql://attendai:attendai_dev_password@host:5432/db"
            
            with pytest.raises(ProductionValidationError) as exc_info:
                validate_production_config()
            
            assert "DATABASE_URL" in str(exc_info.value)
            assert "development password" in str(exc_info.value)

    def test_validation_fails_with_missing_vapi_key(self):
        """Validation should fail with missing Vapi API key."""
        with patch("app.core.production_validation.settings") as mock_settings:
            mock_settings.is_production = True
            mock_settings.DEBUG = False
            mock_settings.SECRET_KEY = "a" * 32
            mock_settings.JWT_SECRET_KEY = "b" * 32
            mock_settings.VAPI_API_KEY = ""
            mock_settings.VAPI_WEBHOOK_SECRET = "c" * 32
            mock_settings.OPENAI_API_KEY = "valid-openai-key"
            mock_settings.ANTHROPIC_API_KEY = ""
            mock_settings.LLM_PROVIDER = "openai"
            mock_settings.CORS_ORIGINS = "https://example.com"
            mock_settings.cors_origins_list = ["https://example.com"]
            mock_settings.DATABASE_URL = "postgresql://user:strongpass@host:5432/db"
            
            with pytest.raises(ProductionValidationError) as exc_info:
                validate_production_config()
            
            assert "VAPI_API_KEY" in str(exc_info.value)

    def test_validation_fails_with_missing_openai_key(self):
        """Validation should fail with missing OpenAI key when provider is openai."""
        with patch("app.core.production_validation.settings") as mock_settings:
            mock_settings.is_production = True
            mock_settings.DEBUG = False
            mock_settings.SECRET_KEY = "a" * 32
            mock_settings.JWT_SECRET_KEY = "b" * 32
            mock_settings.VAPI_API_KEY = "valid-vapi-key"
            mock_settings.VAPI_WEBHOOK_SECRET = "c" * 32
            mock_settings.OPENAI_API_KEY = ""
            mock_settings.ANTHROPIC_API_KEY = ""
            mock_settings.LLM_PROVIDER = "openai"
            mock_settings.CORS_ORIGINS = "https://example.com"
            mock_settings.cors_origins_list = ["https://example.com"]
            mock_settings.DATABASE_URL = "postgresql://user:strongpass@host:5432/db"
            
            with pytest.raises(ProductionValidationError) as exc_info:
                validate_production_config()
            
            assert "OPENAI_API_KEY" in str(exc_info.value)

    def test_validation_fails_with_localhost_cors(self):
        """Validation should fail with localhost in CORS for production."""
        with patch("app.core.production_validation.settings") as mock_settings:
            mock_settings.is_production = True
            mock_settings.DEBUG = False
            mock_settings.SECRET_KEY = "a" * 32
            mock_settings.JWT_SECRET_KEY = "b" * 32
            mock_settings.VAPI_API_KEY = "valid-vapi-key"
            mock_settings.VAPI_WEBHOOK_SECRET = "c" * 32
            mock_settings.OPENAI_API_KEY = "valid-openai-key"
            mock_settings.ANTHROPIC_API_KEY = ""
            mock_settings.LLM_PROVIDER = "openai"
            mock_settings.CORS_ORIGINS = "http://localhost:3000,https://example.com"
            mock_settings.cors_origins_list = ["http://localhost:3000", "https://example.com"]
            mock_settings.DATABASE_URL = "postgresql://user:strongpass@host:5432/db"
            
            with pytest.raises(ProductionValidationError) as exc_info:
                validate_production_config()
            
            assert "CORS_ORIGINS" in str(exc_info.value)
            assert "localhost" in str(exc_info.value)
