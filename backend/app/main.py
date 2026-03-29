"""
Anchora – Decision Intelligence & Governance Platform
FastAPI Application Entry Point
"""

from collections import deque
from contextlib import asynccontextmanager
from time import perf_counter

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.config.settings import settings
from app.core.database import engine
from app.core.dependencies import require_role
from app.modules.auth.router import router as auth_router
from app.modules.knowledge.router import router as knowledge_router
from app.modules.decision.router import router as decision_router
from app.modules.workflow.router import router as workflow_router
from app.modules.compliance.router import router as compliance_router
from app.modules.audit.router import router as audit_router
from app.modules.integration.router import router as integration_router
from app.modules.users.router import router as users_router


_request_count = 0
_error_count = 0
_latency_samples: deque[float] = deque(maxlen=2000)


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
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS refresh_tokens (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                jti VARCHAR(64) UNIQUE NOT NULL,
                user_id VARCHAR(64) NOT NULL,
                issued_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                expires_at TIMESTAMPTZ,
                revoked_at TIMESTAMPTZ,
                used_at TIMESTAMPTZ,
                replaced_by_jti VARCHAR(64)
            )
        """))
        await conn.execute(text(
            "CREATE INDEX IF NOT EXISTS idx_refresh_tokens_user_id ON refresh_tokens(user_id)"
        ))
        await conn.execute(text(
            "CREATE INDEX IF NOT EXISTS idx_refresh_tokens_jti ON refresh_tokens(jti)"
        ))
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS auth_login_attempts (
                email VARCHAR(255) PRIMARY KEY,
                failed_attempts INTEGER NOT NULL DEFAULT 0,
                first_failed_at TIMESTAMPTZ,
                lock_until TIMESTAMPTZ,
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
        """))
        await conn.execute(text(
            "CREATE INDEX IF NOT EXISTS idx_auth_login_attempts_lock_until ON auth_login_attempts(lock_until)"
        ))
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS idempotency_keys (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                user_id VARCHAR(64) NOT NULL,
                endpoint VARCHAR(255) NOT NULL,
                idem_key VARCHAR(255) NOT NULL,
                request_hash VARCHAR(64) NOT NULL,
                status_code INTEGER NOT NULL,
                response_body JSONB NOT NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                UNIQUE (user_id, endpoint, idem_key)
            )
        """))
        await conn.execute(text(
            "CREATE INDEX IF NOT EXISTS idx_idempotency_created_at ON idempotency_keys(created_at)"
        ))

        # Phase 2: policy version pinning column — idempotent, safe to run every boot
        await conn.execute(text(
            "ALTER TABLE decisions ADD COLUMN IF NOT EXISTS policy_snapshot JSONB NOT NULL DEFAULT '{}'::jsonb"
        ))
        await conn.execute(text(
            "ALTER TABLE decisions ADD COLUMN IF NOT EXISTS quality_snapshot JSONB NOT NULL DEFAULT '{}'::jsonb"
        ))

        # Query performance indexes for Phase 1 list/filter/sort contracts
        await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_decisions_created_at ON decisions(created_at DESC)"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_decisions_status ON decisions(status)"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_decisions_created_by ON decisions(created_by)"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_workflows_triggered_at ON workflows(triggered_at DESC)"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_workflows_status ON workflows(status)"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_workflows_decision_id ON workflows(decision_id)"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_tasks_workflow_id ON tasks(workflow_id)"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status)"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_documents_created_at ON documents(created_at DESC)"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_documents_title ON documents(title)"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_audit_logs_entity_type ON audit_logs(entity_type)"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_audit_logs_entity_id ON audit_logs(entity_id)"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_audit_logs_timestamp ON audit_logs(timestamp DESC)"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_compliance_checks_decision_id ON compliance_checks(decision_id)"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_compliance_checks_policy_id ON compliance_checks(policy_id)"))
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

    @application.middleware("http")
    async def metrics_middleware(request: Request, call_next):
        global _request_count, _error_count
        start = perf_counter()
        _request_count += 1
        try:
            response = await call_next(request)
            if response.status_code >= 500:
                _error_count += 1
            return response
        except Exception:
            _error_count += 1
            raise
        finally:
            duration_ms = (perf_counter() - start) * 1000
            _latency_samples.append(duration_ms)

    # Register module routers
    application.include_router(auth_router,        prefix="/api/auth",        tags=["Auth"])
    application.include_router(knowledge_router,   prefix="/api/knowledge",   tags=["Knowledge"])
    application.include_router(decision_router,    prefix="/api/decisions",   tags=["Decisions"])
    application.include_router(workflow_router,    prefix="/api/workflows",   tags=["Workflows"])
    application.include_router(compliance_router,  prefix="/api/compliance",  tags=["Compliance"])
    application.include_router(audit_router,       prefix="/api/audit",       tags=["Audit"])
    application.include_router(integration_router, prefix="/api/integration", tags=["Integration"])
    application.include_router(users_router,       prefix="/api/admin",       tags=["User Management"])

    @application.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "success": False,
                "error": {
                    "code": f"HTTP_{exc.status_code}",
                    "detail": exc.detail,
                },
                "detail": exc.detail,
            },
        )

    @application.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        return JSONResponse(
            status_code=422,
            content={
                "success": False,
                "error": {
                    "code": "VALIDATION_ERROR",
                    "detail": exc.errors(),
                },
                "detail": exc.errors(),
            },
        )

    return application


app = create_application()


@app.get("/api/health", tags=["Health"])
def health_check():
    return {"status": "ok", "version": "0.1.0"}


@app.get("/api/ops/slo", tags=["Operations"])
def slo_status(current_user: dict = Depends(require_role("admin", "auditor"))):
    total_requests = _request_count
    total_errors = _error_count
    latencies = _latency_samples

    error_rate = (total_errors / total_requests) if total_requests else 0.0
    if latencies:
        ordered = sorted(latencies)
        p95_idx = max(0, int(0.95 * (len(ordered) - 1)))
        p95_ms = round(ordered[p95_idx], 2)
    else:
        p95_ms = 0.0

    return {
        "requests": total_requests,
        "errors": total_errors,
        "error_rate": round(error_rate, 4),
        "p95_latency_ms": p95_ms,
        "targets": {
            "max_error_rate": settings.SLO_ERROR_RATE_TARGET,
            "max_p95_latency_ms": settings.SLO_P95_LATENCY_MS_TARGET,
        },
        "slo_pass": (
            error_rate <= settings.SLO_ERROR_RATE_TARGET
            and p95_ms <= settings.SLO_P95_LATENCY_MS_TARGET
        ),
    }
