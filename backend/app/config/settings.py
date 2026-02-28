from pydantic_settings import BaseSettings
from typing import List
import os


class Settings(BaseSettings):
    # ─── App ─────────────────────────────────────────────
    APP_NAME: str = "Anchora"
    APP_ENV: str = "development"
    DEBUG: bool = True

    # ─── Security ────────────────────────────────────────
    SECRET_KEY: str = "CHANGE_ME_IN_PRODUCTION"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # ─── Database (Supabase PostgreSQL) ──────────────────
    DATABASE_URL: str = "postgresql+asyncpg://user:password@host:5432/anchora"

    # ─── Supabase ─────────────────────────────────────────
    SUPABASE_URL: str = ""
    SUPABASE_SERVICE_KEY: str = ""
    SUPABASE_STORAGE_BUCKET: str = "anchora-documents"

    # ─── Gemini AI ────────────────────────────────────────
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-1.5-pro"
    GEMINI_MODEL_VERSION: str = "1.5-pro-001"
    PROMPT_VERSION: str = "v1.0.0"

    # ─── CORS ─────────────────────────────────────────────
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:3000",
        "https://anchora.vercel.app",
    ]

    # ─── pgvector ─────────────────────────────────────────
    EMBEDDING_DIMENSIONS: int = 768   # Gemini text-embedding-004

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
