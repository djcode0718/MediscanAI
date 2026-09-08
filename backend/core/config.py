# backend/core/config.py
from functools import lru_cache
from typing import List
from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Centralized application configuration.
    Values are loaded strictly from environment variables and the local .env file.
    """
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # Application Meta
    APP_NAME: str = "MediScanAI"
    APP_ENV: str = "development"
    DEBUG: bool = False

    # Database Configuration
    DATABASE_URL: str = "postgresql+psycopg2://localhost:5432/mediscanai"
    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 10
    DB_POOL_TIMEOUT: int = 30
    DB_POOL_PRE_PING: bool = True

    # JWT Authentication Configuration
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # Upload & Request Bounds Configuration
    MAX_IMAGE_SIZE_BYTES: int = 10 * 1024 * 1024  # 10 MB
    MAX_AUDIO_SIZE_BYTES: int = 25 * 1024 * 1024  # 25 MB
    MAX_TEXT_LENGTH: int = 4000
    MAX_AUDIO_CLIPS_COUNT: int = 5
    ALLOWED_IMAGE_EXTENSIONS: List[str] = [".jpg", ".jpeg", ".png", ".webp"]
    ALLOWED_AUDIO_EXTENSIONS: List[str] = [".wav", ".mp3", ".webm", ".ogg", ".m4a"]

    # Rate Limiting Configuration
    RATE_LIMIT_ANALYZE_PER_MINUTE: int = 10
    RATE_LIMIT_AUTH_PER_MINUTE: int = 20

    # Concurrency & Resource Protection
    MAX_CONCURRENT_ANALYSES: int = 2

    # Ollama & Model Service Configuration
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_CONNECT_TIMEOUT_SECONDS: float = 5.0
    OLLAMA_READ_TIMEOUT_SECONDS: float = 60.0
    OLLAMA_MODEL: str = "mistral"

    # Online LLM Provider Configuration (optional — leave empty to disable online mode)
    # Fallback chain: Gemini-1 -> Gemini-2 -> Groq-1 -> Groq-2
    GEMINI_API_KEY: str = ""
    GROQ_API_KEY: str = ""
    # Gemini models (tried in order on failure)
    GEMINI_MODEL_1: str = "gemini-2.0-flash"
    GEMINI_MODEL_2: str = "gemini-1.5-flash"
    # Groq models (tried in order on failure)
    GROQ_MODEL_1: str = "llama-3.3-70b-versatile"
    GROQ_MODEL_2: str = "llama-3.1-8b-instant"
    ONLINE_LLM_TIMEOUT_SECONDS: float = 60.0
    # LLM mode: 'offline' (Ollama/Mistral) or 'online' (Gemini->Groq fallback chain)
    LLM_MODE: str = "offline"

    # Test Database URL (isolated SQLite memory or test Postgres)
    TEST_DATABASE_URL: str = "sqlite:///:memory:"

    # CORS Configuration
    CORS_ORIGINS: List[str] = ["http://localhost:5173", "http://127.0.0.1:5173", "*"]

    @field_validator("JWT_SECRET_KEY")
    @classmethod
    def validate_jwt_secret(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("JWT_SECRET_KEY must be configured in environment or .env file.")
        return v.strip()

    @field_validator("LLM_MODE")
    @classmethod
    def validate_llm_mode(cls, v: str) -> str:
        valid = {"offline", "online"}
        if v.lower() not in valid:
            raise ValueError(f"LLM_MODE must be one of {sorted(valid)}, got '{v}'.")
        return v.lower()

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v):
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",") if i.strip()]
        return v

    @model_validator(mode="after")
    def validate_production_cors(self):
        if self.APP_ENV.lower() in ("production", "prod"):
            if "*" in self.CORS_ORIGINS or any(origin == "*" for origin in self.CORS_ORIGINS):
                raise ValueError(
                    "CORS wildcard '*' is not permitted when APP_ENV is 'production'. "
                    "Explicit origins must be specified."
                )
            if not self.CORS_ORIGINS:
                raise ValueError("CORS_ORIGINS cannot be empty in production.")
        return self


@lru_cache()
def get_settings() -> Settings:
    """Return a cached singleton instance of Settings."""
    return Settings()


settings: Settings = get_settings()
