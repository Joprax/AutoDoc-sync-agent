"""
Centralized settings, loaded from environment variables / .env file.

Keeping all config in one Settings object (instead of scattered os.getenv calls)
means every module imports the same validated values, and misconfiguration
fails fast at startup instead of silently at runtime.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    ENVIRONMENT: str = "development"

    # Postgres
    DATABASE_URL: str = "postgresql+psycopg2://docsync:docsync@localhost:5432/docsync"

    # Redis (used as both Celery broker and result backend)
    REDIS_URL: str = "redis://localhost:6379/0"

    # GitHub
    GITHUB_WEBHOOK_SECRET: str = "changeme"
    GITHUB_APP_TOKEN: str = ""

    # LLM
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.5-flash"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
