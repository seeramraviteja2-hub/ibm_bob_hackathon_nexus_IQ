"""
NexusIQ — Application Settings.
All secrets loaded from environment / .env file.
"""

from pydantic_settings import BaseSettings
from pydantic import Field, field_validator


class Settings(BaseSettings):
    # ── Database ───────────────────────────────────────────────────────────
    DATABASE_URL: str = Field(default="postgresql+asyncpg://postgres:postgres@localhost:5432/nexusiq")

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def fix_db_url(cls, v: str) -> str:
        """
        Normalize Postgres URL to use asyncpg driver.
        Handles all common formats from Neon, Supabase, Railway, and local setups.
        """
        if not v:
            raise ValueError("DATABASE_URL must be set")
        # Already correct
        if v.startswith("postgresql+asyncpg://"):
            return v
        # Standard postgres:// from Neon/Supabase copy-paste
        if v.startswith("postgres://"):
            return v.replace("postgres://", "postgresql+asyncpg://", 1)
        # postgresql:// without driver
        if v.startswith("postgresql://"):
            return v.replace("postgresql://", "postgresql+asyncpg://", 1)
        raise ValueError(
            f"Unrecognized DATABASE_URL format: {v[:30]}... "
            "Must start with postgres://, postgresql://, or postgresql+asyncpg://"
        )

    # ── Infrastructure ─────────────────────────────────────────────────────
    REDIS_URL: str = Field(default="redis://localhost:6379/0")
    QDRANT_URL: str = Field(default="http://localhost:6333")
    QDRANT_API_KEY: str = Field(default="")
    # ── Storage (Supabase - FREE, replaces MinIO) ─────────────────────────
    SUPABASE_URL: str = Field(default="")
    SUPABASE_KEY: str = Field(default="")  # use service_role key

    # Legacy MinIO constants kept for bucket-name references only
    MINIO_BUCKET: str = Field(default="nexusiq")
    # ── IBM Bob (Tier 0 — PRIMARY for setup phase) ────────────────────────
    # Used for: requirement_agent, rag_agent, course_gen_agent
    # MCP-enabled for advanced reasoning and code understanding
    ibm_bob_api_key: str = Field(default="")
    ibm_bob_base_url: str = Field(default="https://api.ibm.com/watsonx/v1")
    ibm_bob_model: str = Field(default="ibm/granite-13b-chat-v2")


    # ── LLM API Keys ───────────────────────────────────────────────────────
    # Tier 1 — Cerebras (fastest, 1M tokens/day free — primary for all agents)
    # Sign up at cloud.cerebras.ai. Each email gets a free key.
    cerebras_api_key_1: str = Field(default="")
    cerebras_api_key_2: str = Field(default="")
    cerebras_api_key_3: str = Field(default="")

    # Tier 2 — Gemini (3 keys rotated — used for long context RAG, fallback)
    gemini_api_key_1: str = Field(default="")
    gemini_api_key_2: str = Field(default="")
    gemini_api_key_3: str = Field(default="")

    # Tier 3 — Groq (emergency fallback, already in your stack)
    groq_api_key: str = Field(default="")

    @property
    def cerebras_keys(self) -> list[str]:
        return [k.strip() for k in [
            self.cerebras_api_key_1,
            self.cerebras_api_key_2,
            self.cerebras_api_key_3,
        ] if k.strip()]
    @property
    def has_bob(self) -> bool:
        """Check if IBM Bob is configured."""
        return bool(self.ibm_bob_api_key.strip())


    @property
    def gemini_keys(self) -> list[str]:
        return [k.strip() for k in [
            self.gemini_api_key_1,
            self.gemini_api_key_2,
            self.gemini_api_key_3,
        ] if k.strip()]

    # ── Observability ──────────────────────────────────────────────────────
    LANGCHAIN_API_KEY: str = Field(default="")
    LANGCHAIN_PROJECT: str = Field(default="nexusiq")

    # ── Application ────────────────────────────────────────────────────────
    ENVIRONMENT: str = Field(default="dev")
    DEBUG: bool = Field(default=True)

    # DEMO_MODE — set True for VC demos.
    # Bypasses all real LLM calls with pre-cached high-fidelity responses.
    # Zero rate-limit risk. Agents still log + show status in the UI.
    DEMO_MODE: bool = Field(default=False)

    CORS_ORIGINS: str = Field(default="https://nexus-iq-sigma.vercel.app,http://localhost:3000")
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
            return ["*"]   # wildcard — OK for initial deploy; tighten after frontend URL is known
        return [o.strip() for o in stripped.split(",") if o.strip()]
    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
        "extra": "ignore",
    }


settings = Settings()
