from fastapi import APIRouter, Depends

from app.core.dependencies import require_role

router = APIRouter()


@router.get("/health")
async def integration_health(current_user: dict = Depends(require_role("admin"))):
    """Integration layer health check — Phase 6 placeholder."""
    return {"status": "integration_layer_ready", "adapters": ["erp_mock", "crm_mock"]}
