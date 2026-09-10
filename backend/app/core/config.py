"""
Central configuration. All environment-specific values live here and are
read once at startup. Nothing else in the app should call os.environ directly.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    DATABASE_URL: str = "postgresql+psycopg2://atlas:atlas@localhost:5432/atlas"

    JWT_SECRET_KEY: str = "dev-secret-change-me"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days

    LLM_PROVIDER: str = "anthropic"
    ANTHROPIC_API_KEY: str = ""

    CONTENT_EDITOR_EMAILS: str = ""

    ENVIRONMENT: str = "development"


settings = Settings()
