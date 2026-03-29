from pathlib import Path
from typing import List

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # ─── App ─────────────────────────────────────────────
    APP_NAME: str = "Anchora"
    APP_ENV: str = "development"
    DEBUG: bool = True

    # ─── Security ────────────────────────────────────────
    SECRET_KEY: str = "CHANGE_ME_IN_PRODUCTION"
    SECRET_KEY_FILE: str | None = None
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    LOGIN_MAX_ATTEMPTS: int = 5
    LOGIN_ATTEMPT_WINDOW_MINUTES: int = 15
    LOGIN_LOCKOUT_MINUTES: int = 15

    # ─── Auth Cookies ────────────────────────────────────
    AUTH_COOKIE_ENABLED: bool = True
    AUTH_COOKIE_SECURE: bool = False
    AUTH_COOKIE_SAMESITE: str = "lax"
    AUTH_COOKIE_DOMAIN: str | None = None
    ACCESS_COOKIE_NAME: str = "anchora_access_token"
    REFRESH_COOKIE_NAME: str = "anchora_refresh_token"

    # ─── Database (Supabase PostgreSQL) ──────────────────
    DATABASE_URL: str = "postgresql+asyncpg://user:password@host:5432/anchora"

    # ─── Supabase ─────────────────────────────────────────
    SUPABASE_URL: str = ""
    SUPABASE_SERVICE_KEY: str = ""
    SUPABASE_SERVICE_KEY_FILE: str | None = None
    SUPABASE_STORAGE_BUCKET: str = "anchora-documents"

    # ─── Gemini AI ────────────────────────────────────────
    GEMINI_API_KEY: str = ""
    GEMINI_API_KEY_FILE: str | None = None
    GEMINI_MODEL: str = "gemini-1.5-pro"
    GEMINI_MODEL_VERSION: str = "1.5-pro-001"
    PROMPT_VERSION: str = "v1.0.0"
    AI_GROUNDING_GATE_ENABLED: bool = True
    AI_GROUNDING_MIN_SCORE: float = 0.30
    AI_GROUNDING_REQUIRE_CITATION: bool = True
    RETRIEVAL_BENCHMARK_MIN_PRECISION: float = 0.50

    # ─── CORS ─────────────────────────────────────────────
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:3000",
        "https://anchora.vercel.app",
    ]

    # ─── pgvector ─────────────────────────────────────────
    EMBEDDING_DIMENSIONS: int = 768   # Gemini text-embedding-004
    RETRIEVAL_TOP_K_DOCUMENTS: int = 10
    RETRIEVAL_TOP_K_CHUNKS: int = 30
    RETRIEVAL_KEYWORD_WEIGHT: float = 0.35
    KNOWLEDGE_CHUNK_SIZE_CHARS: int = 1200
    KNOWLEDGE_CHUNK_OVERLAP_CHARS: int = 200
    KNOWLEDGE_MAX_CHUNKS_PER_DOCUMENT: int = 64

    # ─── SLO / Monitoring Baseline ──────────────────────
    SLO_ERROR_RATE_TARGET: float = 0.05
    SLO_P95_LATENCY_MS_TARGET: int = 1200

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True)

    @staticmethod
    def _read_secret_file(path_value: str | None) -> str | None:
        if not path_value:
            return None
        try:
            return Path(path_value).read_text(encoding="utf-8").strip()
        except OSError:
            return None

    @staticmethod
    def _is_placeholder(value: str) -> bool:
        lowered = value.lower()
        return (
            not value
            or "change_me" in lowered
            or "your-" in lowered
            or "[password]" in lowered
            or "user:password@host" in lowered
        )

    @model_validator(mode="after")
    def apply_security_guards(self) -> "Settings":
        # Allow mounting secrets from files (Kubernetes, Docker secrets, etc.)
        secret_key = self._read_secret_file(self.SECRET_KEY_FILE)
        if secret_key:
            self.SECRET_KEY = secret_key

        supabase_key = self._read_secret_file(self.SUPABASE_SERVICE_KEY_FILE)
        if supabase_key:
            self.SUPABASE_SERVICE_KEY = supabase_key

        gemini_key = self._read_secret_file(self.GEMINI_API_KEY_FILE)
        if gemini_key:
            self.GEMINI_API_KEY = gemini_key

        app_env = self.APP_ENV.lower()
        if app_env in {"prod", "production"}:
            if self.DEBUG:
                raise ValueError("DEBUG must be false in production.")
            if self._is_placeholder(self.SECRET_KEY) or len(self.SECRET_KEY) < 32:
                raise ValueError("SECRET_KEY must be set to a strong production value.")
            if self.AUTH_COOKIE_ENABLED and not self.AUTH_COOKIE_SECURE:
                raise ValueError("AUTH_COOKIE_SECURE must be true when APP_ENV is production.")
            if self._is_placeholder(self.DATABASE_URL):
                raise ValueError("DATABASE_URL must be configured for production.")
            if not self.SUPABASE_URL.strip():
                raise ValueError("SUPABASE_URL must be set in production.")
            if self._is_placeholder(self.SUPABASE_SERVICE_KEY):
                raise ValueError("SUPABASE_SERVICE_KEY must be set in production.")
            if self._is_placeholder(self.GEMINI_API_KEY):
                raise ValueError("GEMINI_API_KEY must be set in production.")

        return self


settings = Settings()
