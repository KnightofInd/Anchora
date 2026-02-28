"""
Anchora – Decision Intelligence & Governance Platform
FastAPI Application Entry Point
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.config.settings import settings
from app.core.database import engine
from app.modules.auth.router import router as auth_router
from app.modules.knowledge.router import router as knowledge_router
from app.modules.decision.router import router as decision_router
from app.modules.workflow.router import router as workflow_router
from app.modules.compliance.router import router as compliance_router
from app.modules.audit.router import router as audit_router
from app.modules.integration.router import router as integration_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create helper tables that aren't handled by migrations."""
    async with engine.begin() as conn:
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS revoked_tokens (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                jti VARCHAR(64) UNIQUE NOT NULL,
                user_id VARCHAR(64) NOT NULL,
                revoked_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                expires_at TIMESTAMPTZ
            )
        """))
        await conn.execute(text(
            "CREATE INDEX IF NOT EXISTS idx_revoked_tokens_jti ON revoked_tokens(jti)"
        ))
    yield


def create_application() -> FastAPI:
    application = FastAPI(
        title="Anchora",
        description="Decision Intelligence & Governance Platform",
        version="0.1.0",
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        lifespan=lifespan,
    )

    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register module routers
    application.include_router(auth_router,        prefix="/api/auth",        tags=["Auth"])
    application.include_router(knowledge_router,   prefix="/api/knowledge",   tags=["Knowledge"])
    application.include_router(decision_router,    prefix="/api/decisions",   tags=["Decisions"])
    application.include_router(workflow_router,    prefix="/api/workflows",   tags=["Workflows"])
    application.include_router(compliance_router,  prefix="/api/compliance",  tags=["Compliance"])
    application.include_router(audit_router,       prefix="/api/audit",       tags=["Audit"])
    application.include_router(integration_router, prefix="/api/integration", tags=["Integration"])

    return application


app = create_application()


@app.get("/api/health", tags=["Health"])
def health_check():
    return {"status": "ok", "version": "0.1.0"}
