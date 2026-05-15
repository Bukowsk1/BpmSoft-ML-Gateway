from fastapi import APIRouter, Request

from app.core.audit import log_audit
from app.schemas.common import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
def healthcheck(request: Request) -> HealthResponse:
    registry = request.app.state.model_registry
    settings = request.app.state.settings
    request_id = getattr(request.state, "request_id", None)

    log_audit(
        "healthcheck",
        request_id=request_id,
        loaded_models=sum(1 for item in registry.demand_statuses() if item.loaded),
    )

    return HealthResponse(
        status="ok",
        service=settings.app_name,
        demand_models=registry.demand_statuses(),
    )
