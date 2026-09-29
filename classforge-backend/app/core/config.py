from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration settings loaded from environment variables."""

    PROJECT_NAME: str = "ClassForge"
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = "classforge-super-secret-key-for-development-only"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    MONGODB_URL: str = "mongodb://localhost:27017"
    DATABASE_NAME: str = "classforge"
    INACTIVITY_TIMEOUT_MINUTES: int = 30
    # Comma-separated origins. For dev: "http://localhost:4200"
    # Rule R03: Never use ["*"] in production — configure per environment via .env
    CORS_ORIGINS: str = "http://localhost:4200,http://localhost:4201"
    OLLAMA_URL: str = "http://localhost:11434"
    N8N_WEBHOOK_URL: Optional[str] = None
    GEMINI_API_KEY: Optional[str] = None
    GEMINI_MODEL: str = "gemini-3.8-flash"

    @property
    def cors_origins_list(self) -> List[str]:
        """Returns the parsed list of allowed CORS origins."""
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()

