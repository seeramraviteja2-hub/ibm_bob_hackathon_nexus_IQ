"""
NexusIQ — Application Settings.
All secrets loaded from environment / .env file with automatic sanitization.
"""

from pydantic_settings import BaseSettings
from pydantic import Field, field_validator
from typing import Any


class Settings(BaseSettings):
    # ── Database ───────────────────────────────────────────────────────────
    DATABASE_URL: str = Field(default="postgresql+asyncpg://postgres:postgres@localhost:5432/nexusiq")

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def fix_db_url(cls, v: str) -> str:
        if not v:
            raise ValueError("DATABASE_URL must be set")
        
        # Strip potential whitespace/newlines first
        v = v.strip().replace("\n", "").replace("\r", "")
        
        if v.startswith("postgresql+asyncpg://"):
            return v
        if v.startswith("postgres://"):
            return v.replace("postgres://", "postgresql+asyncpg://", 1)
        if v.startswith("postgresql://"):
            return v.replace("postgresql://", "postgresql+asyncpg://", 1)
        return v

    # ── Infrastructure ─────────────────────────────────────────────────────
    REDIS_URL: str = Field(default="redis://localhost:6379/0")
    QDRANT_URL: str = Field(default="http://localhost:6333")
    QDRANT_API_KEY: str = Field(default="")
    
    # ── Storage ────────────────────────────────────────────────────────────
    SUPABASE_URL: str = Field(default="")
    SUPABASE_KEY: str = Field(default="") 

    # ── IBM Bob (Tier 0) ──────────────────────────────────────────────────
    ibm_bob_api_key: str = Field(default="")
    ibm_bob_base_url: str = Field(default="https://api.ibm.com/watsonx/v1")
    ibm_bob_model: str = Field(default="ibm/granite-13b-chat-v2")

    # ── LLM API Keys ───────────────────────────────────────────────────────
    cerebras_api_key_1: str = Field(default="")
    cerebras_api_key_2: str = Field(default="")
    cerebras_api_key_3: str = Field(default="")

    gemini_api_key_1: str = Field(default="")
    gemini_api_key_2: str = Field(default="")
    gemini_api_key_3: str = Field(default="")

    groq_api_key: str = Field(default="")

    # ── GLOBAL SANITIZER ──────────────────────────────────────────────────
    # This catches the '\n' at position 26 error automatically for all keys
    @field_validator(
        "ibm_bob_api_key", "ibm_bob_base_url", "REDIS_URL", 
        "cerebras_api_key_1", "gemini_api_key_1", "groq_api_key",
        "SUPABASE_KEY", "QDRANT_API_KEY", mode="before"
    )
    @classmethod
    def sanitize_strings(cls, v: Any) -> Any:
        if isinstance(v, str):
            # Remove quotes, newlines, and trailing/leading spaces
            return v.strip().replace('"', '').replace("'", "").replace("\n", "").replace("\r", "")
        return v

    # ── Helper Properties ─────────────────────────────────────────────────
    @property
    def cerebras_keys(self) -> list[str]:
        return [k for k in [self.cerebras_api_key_1, self.cerebras_api_key_2, self.cerebras_api_key_3] if k]

    @property
    def gemini_keys(self) -> list[str]:
        return [k for k in [self.gemini_api_key_1, self.gemini_api_key_2, self.gemini_api_key_3] if k]

    @property
    def has_bob(self) -> bool:
        return bool(self.ibm_bob_api_key)

    # ── Application ────────────────────────────────────────────────────────
    ENVIRONMENT: str = Field(default="dev")
    DEBUG: bool = Field(default=True)
    DEMO_MODE: bool = Field(default=False)
    CORS_ORIGINS: str = Field(default="https://ibm-bob-hackathon-nexus-iq.vercel.app,http://localhost:3000")
    UVICORN_WORKERS: int = Field(default=1)

    # ── Auth ───────────────────────────────────────────────────────────────
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30)
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(default=7)
    JWT_SECRET: str = Field(default="change-me-in-production")
    JWT_ALGORITHM: str = Field(default="HS256")

    @field_validator("JWT_SECRET")
    @classmethod
    def reject_default_secret(cls, v: str) -> str:
        import os
        if v == "change-me-in-production" and os.getenv("ENVIRONMENT", "dev") != "dev":
            raise ValueError("JWT_SECRET must be changed in production!")
        return v

    @property
    def cors_origins_list(self) -> list[str]:
        stripped = self.CORS_ORIGINS.strip()
        if stripped == "*":
            return ["*"]
        return [o.strip() for o in stripped.split(",") if o.strip()]

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
        "extra": "ignore",
    }

settings = Settings()
