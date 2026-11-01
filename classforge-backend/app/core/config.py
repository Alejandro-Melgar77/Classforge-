from typing import Any, Dict, List, Optional
from urllib.parse import urlparse
import json
from pydantic import SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration settings loaded from environment variables."""

    PROJECT_NAME: str = "ClassForge"
    ENVIRONMENT: str = "development"  # "development" | "production"
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
    OLLAMA_MODEL: str = "qwen2.5:1.5b"
    OLLAMA_TIMEOUT_S: float = 12.0
    LOCAL_LLM_SECRET: Optional[SecretStr] = None
    LLM_ROUTING: str = '{"uml_command":["ollama","gemini","heuristic"],"role_chat":["gemini"],"role_review":["gemini"],"vision":["gemini"],"codegen":["gemini"],"digest":["gemini","ollama"]}'
    LOCAL_LATENCY_THRESHOLD_S: float = 15.0
    AI_LOCAL_ONLY: bool = False
    N8N_WEBHOOK_URL: Optional[str] = None

    # LLM Settings (P2 unified LLM client)
    LLM_PROVIDER: str = "gemini"  # "gemini" | "fake"
    GEMINI_API_KEY: Optional[SecretStr] = None
    GEMINI_MODELS: str = "gemini-3.8-flash,gemini-2.5-flash,gemini-2.0-flash"
    GEMINI_MODEL: str = "gemini-3.8-flash"  # Legacy single-model fallback
    LLM_TIMEOUT_SECONDS: float = 30.0
    LLM_MAX_ATTEMPTS: int = 3
    LLM_CIRCUIT_BREAKER_FAILURES: int = 5
    LLM_CIRCUIT_BREAKER_RECOVERY_SECONDS: float = 30.0
    LLM_MAX_OUTPUT_TOKENS_CHAT: int = 2048
    LLM_MAX_OUTPUT_TOKENS_TASK: int = 8192
    LLM_MAX_OUTPUT_TOKENS_CODEGEN: int = 32768
    LLM_MAX_OUTPUT_TOKENS_VISION: int = 4096

    AI_CHAT_ENABLED: bool = True
    AI_CONTEXT_BUDGET_TOKENS: int = 8000
    AI_CONTEXT_MAX_TOKENS: int = 8000  # Deprecated alias for AI_CONTEXT_BUDGET_TOKENS

    # Autonomous Team AI Worker & Triggers Settings (P5)
    AI_AUTONOMY_ENABLED: bool = True
    AI_WORKER_CONCURRENCY: int = 2
    AI_WORKER_LEASE_SECONDS: int = 120
    AI_WORKER_POLL_INTERVAL_SECONDS: float = 2.0
    AI_REVIEW_QUIET_SECONDS: int = 90
    AI_ROLE_COOLDOWN_SECONDS: int = 600
    AI_PERIODIC_HOURS: int = 24
    AI_DAILY_CALLS_PER_PROJECT: int = 100
    AI_DAILY_OUTPUT_TOKENS_PER_PROJECT: int = 200000
    AI_MAX_PROPOSALS_PER_POST: int = 5
    AI_MAX_WORDS_PER_POST: int = 1200
    AI_MAX_OPERATIONS_PER_APPLY: int = 10

    @field_validator("OLLAMA_URL")
    @classmethod
    def validate_ollama_url(cls, v: str) -> str:
        if not v or not isinstance(v, str):
            raise ValueError("OLLAMA_URL no puede estar vacío")
        clean = v.strip().rstrip("/")
        parsed = urlparse(clean)
        if parsed.scheme not in ("http", "https"):
            raise ValueError(f"OLLAMA_URL debe usar esquema http o https, recibido: '{parsed.scheme}'")
        if not parsed.hostname:
            raise ValueError("OLLAMA_URL debe contener un host válido")
        return clean

    @property
    def routing_config(self) -> Dict[str, List[str]]:
        """Returns the parsed LLM_ROUTING dictionary."""
        try:
            parsed = json.loads(self.LLM_ROUTING)
            if isinstance(parsed, dict):
                return {k: [str(x).strip().lower() for x in v] for k, v in parsed.items()}
        except Exception:
            pass
        return {
            "uml_command": ["ollama", "gemini", "heuristic"],
            "role_chat": ["gemini"],
            "role_review": ["gemini"],
            "vision": ["gemini"],
            "codegen": ["gemini"],
            "digest": ["gemini", "ollama"],
        }

    def get_routing_chain(self, purpose: str) -> List[str]:
        """Returns ordered provider list for the given purpose."""
        chain = self.routing_config.get(purpose)
        if not chain:
            chain = ["gemini"]
        return list(chain)

    @property
    def cors_origins_list(self) -> List[str]:
        """Returns the parsed list of allowed CORS origins."""
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    @property
    def gemini_models_list(self) -> List[str]:
        """Returns ordered list of Gemini models configured without duplicates."""
        configured = [m.strip() for m in self.GEMINI_MODELS.split(",") if m.strip()]
        if not configured:
            configured = ["gemini-3.8-flash"]
        if self.GEMINI_MODEL and self.GEMINI_MODEL not in configured:
            configured.append(self.GEMINI_MODEL)
        return configured

    @property
    def has_gemini_server_key(self) -> bool:
        """Returns True if the server has a valid GEMINI_API_KEY configured."""
        if not self.GEMINI_API_KEY:
            return False
        return bool(self.GEMINI_API_KEY.get_secret_value().strip())

    def get_max_output_tokens(self, purpose: str) -> int:
        """Returns configured max_output_tokens bounded by hard ceiling (65,536)."""
        ceiling = 65536
        tokens_map = {
            "chat": self.LLM_MAX_OUTPUT_TOKENS_CHAT,
            "task": self.LLM_MAX_OUTPUT_TOKENS_TASK,
            "codegen": self.LLM_MAX_OUTPUT_TOKENS_CODEGEN,
            "vision": self.LLM_MAX_OUTPUT_TOKENS_VISION,
        }
        val = tokens_map.get(purpose, self.LLM_MAX_OUTPUT_TOKENS_CHAT)
        return min(max(1, val), ceiling)

    @model_validator(mode="after")
    def validate_production_settings(self) -> "Settings":
        if self.ENVIRONMENT == "production":
            default_key = "classforge-super-secret-key-for-development-only"
            if not self.SECRET_KEY or self.SECRET_KEY == default_key:
                raise ValueError("En producción, SECRET_KEY debe estar configurado y no puede ser el valor por defecto")
            if not self.cors_origins_list:
                raise ValueError("En producción, CORS_ORIGINS no puede estar vacío")
        return self

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()

