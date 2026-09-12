"""
Application Configuration
"""
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True
    )

    # Application
    APP_ENV: str = "development"
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000
    DEBUG: bool = True
    LOG_LEVEL: str = "INFO"

    # Database
    DATABASE_URL: str = "postgresql://attendai:attendai_dev_password@localhost:5432/attendai_db"
    DATABASE_ECHO: bool = False

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # Security
    SECRET_KEY: str = "your-secret-key-change-in-production"
    JWT_SECRET_KEY: str = "your-jwt-secret-key-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # CORS
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:8000"

    @property
    def cors_origins_list(self) -> List[str]:
        """Parse CORS origins from comma-separated string."""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]

    # Vapi Configuration
    VAPI_API_KEY: str = ""
    VAPI_WEBHOOK_SECRET: str = ""
    VAPI_PHONE_NUMBER_ID: str = ""
    VAPI_BASE_URL: str = "https://api.vapi.ai"

    # LLM Provider
    LLM_PROVIDER: str = "openai"  # openai or anthropic
    OPENAI_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""

    # LLM Models
    LLM_EXTRACTION_MODEL: str = "gpt-4o"
    LLM_VOICE_MODEL: str = "gpt-4o"
    LLM_TEMPERATURE: float = 0.1
    LLM_MAX_TOKENS: int = 1000

    # Call Configuration
    MAX_CALL_DURATION_SECONDS: int = 300
    MAX_CALL_RETRIES: int = 3
    RETRY_DELAY_MINUTES: int = 30
    NO_ANSWER_RETRY_DELAY_MINUTES: int = 120

    # Confidence Thresholds
    LOW_CONFIDENCE_THRESHOLD: float = 0.7
    REQUIRE_REVIEW_THRESHOLD: float = 0.85

    # Data Retention (days)
    TRANSCRIPT_RETENTION_DAYS: int = 90
    RECORDING_RETENTION_DAYS: int = 30
    AUDIT_LOG_RETENTION_DAYS: int = 365

    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 60
    CALL_RATE_LIMIT_PER_HOUR: int = 100

    # Worker Configuration
    WORKER_CONCURRENCY: int = 4
    ENABLE_SCHEDULED_CALLS: bool = True

    # Health Check
    HEALTH_CHECK_INTERVAL_SECONDS: int = 30

    # Timezone
    TZ: str = "UTC"

    @property
    def is_production(self) -> bool:
        """Check if running in production."""
        return self.APP_ENV == "production"

    @property
    def is_development(self) -> bool:
        """Check if running in development."""
        return self.APP_ENV == "development"


settings = Settings()
