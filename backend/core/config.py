# backend/core/config.py
from pathlib import Path
from typing import List, Optional, Dict
from dotenv import load_dotenv
from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_BASE_DIR = Path(__file__).resolve().parent.parent.parent
_ENV_PATH = _BASE_DIR / ".env"
if _ENV_PATH.exists():
    load_dotenv(_ENV_PATH, override=True)


class Settings(BaseSettings):
    """
    Centralized application configuration.
    Values are loaded strictly from environment variables and the local .env file.
    """
    model_config = SettingsConfigDict(
        env_file=str(_ENV_PATH) if _ENV_PATH.exists() else ".env",
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
    GEMINI_MODEL_1: str = "gemini-3.6-flash"
    GEMINI_MODEL_2: str = "gemini-3.7-flash"
    # Groq models (tried in order on failure)
    GROQ_MODEL_1: str = "openai/gpt-oss-120b"
    GROQ_MODEL_2: str = "openai/gpt-oss-20b"
    ONLINE_LLM_TIMEOUT_SECONDS: float = 60.0
    # LLM mode: 'offline' (Ollama/Mistral) or 'online' (Gemini->Groq fallback chain)
    LLM_MODE: str = "offline"

    # Test Database URL (isolated SQLite memory or test Postgres)
    TEST_DATABASE_URL: str = "sqlite:///:memory:"

    # CORS Configuration
    CORS_ORIGINS: List[str] = ["http://localhost:5173", "http://127.0.0.1:5173", "*"]

    # Neo4j Graph Database Configuration (Optional - Phase 2)
    NEO4J_ENABLED: bool = False
    NEO4J_URI: str = "bolt://localhost:7687"
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: str = ""
    NEO4J_CONNECTION_TIMEOUT_SECONDS: float = 5.0
    NEO4J_MAX_CONNECTION_LIFETIME_SECONDS: float = 3600.0
    NEO4J_MAX_CONNECTION_POOL_SIZE: int = 50

    # Emergency Triage Guardrail Configuration (Phase 1.2.d)
    EMERGENCY_GUARDRAIL_ENABLED: bool = False
    EMERGENCY_GUARDRAIL_CONFIG_PATH: str = "app/guardrail_config.json"
    EMERGENCY_GUARDRAIL_FAST_PATH: bool = True

    # Generation Hygiene & Evidence Configuration (Phase 01 Part B)
    EVIDENCE_FORMAT: str = "legacy"  # "legacy" | "compact"
    PROMPT_VERSION: str = "legacy"   # "legacy" | "v2"
    GEN_TEMPERATURE: Optional[float] = None
    GEN_SEED: Optional[int] = None
    OLLAMA_NUM_CTX: Optional[int] = None
    OLLAMA_NUM_PREDICT: Optional[int] = None
    # Development trace (opt-in; off by default). Text is redacted unless DEV_TRACE_INCLUDE_TEXT=true.
    DEV_TRACE_ENABLED: bool = False
    DEV_TRACE_INCLUDE_TEXT: bool = False
    DEV_TRACE_DIR: Optional[str] = None
    EVIDENCE_MAX_ITEMS_PER_CHANNEL: int = 3
    EVIDENCE_DRUG_FIELDS: str = "brand_name,generic_name,active_ingredients,indications"
    EVIDENCE_FIELD_CAPS: Dict[str, int] = {
        "indications": 700,
        "warnings": 300,
        "dosage": 300,
        "adverse_reactions": 300,
        "symptoms": 12,
    }

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

    @field_validator("EVIDENCE_FORMAT")
    @classmethod
    def validate_evidence_format(cls, v: str) -> str:
        valid = {"legacy", "compact"}
        if v.lower() not in valid:
            raise ValueError(f"EVIDENCE_FORMAT must be one of {sorted(valid)}, got '{v}'.")
        return v.lower()

    @field_validator("PROMPT_VERSION")
    @classmethod
    def validate_prompt_version(cls, v: str) -> str:
        valid = {"legacy", "v2"}
        if v.lower() not in valid:
            raise ValueError(f"PROMPT_VERSION must be one of {sorted(valid)}, got '{v}'.")
        return v.lower()

    @field_validator("EVIDENCE_FIELD_CAPS", mode="before")
    @classmethod
    def parse_evidence_field_caps(cls, v):
        import json
        if isinstance(v, str):
            try:
                return json.loads(v)
            except Exception:
                res = {}
                for part in v.split(","):
                    if "=" in part:
                        k, val = part.split("=", 1)
                        res[k.strip()] = int(val.strip())
                return res
        return v

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

    @model_validator(mode="after")
    def validate_neo4j_configuration(self):
        if self.NEO4J_ENABLED:
            if not self.NEO4J_URI or not self.NEO4J_URI.strip():
                raise ValueError("NEO4J_URI must be configured when NEO4J_ENABLED is True.")
            if not self.NEO4J_PASSWORD or not self.NEO4J_PASSWORD.strip():
                raise ValueError("NEO4J_PASSWORD must be configured when NEO4J_ENABLED is True.")
            if self.NEO4J_CONNECTION_TIMEOUT_SECONDS <= 0:
                raise ValueError("NEO4J_CONNECTION_TIMEOUT_SECONDS must be positive.")
        return self


def get_settings() -> Settings:
    """Return an up-to-date instance of Settings loaded from .env."""
    if _ENV_PATH.exists():
        load_dotenv(_ENV_PATH, override=True)
    return Settings()


settings: Settings = get_settings()
