from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI

from app.api.routes import api_router
from app.core.config import get_settings
from app.core.errors import register_exception_handlers
from app.core.logging import configure_logging
from app.core.runtime_checks import prepare_runtime_cache
from app.middleware.request_id import RequestIDMiddleware
from app.services.model_registry import ModelRegistry

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    configure_logging(settings.log_level)
    prepare_runtime_cache(settings.backend_dir)
    registry = ModelRegistry(settings)
    registry.load()
    app.state.settings = settings
    app.state.model_registry = registry
    logger.info(
        "Application started. Loaded demand models: %s/%s",
        sum(1 for item in registry.demand_statuses() if item.loaded),
        len(registry.demand_statuses()),
    )
    yield
    logger.info("Application stopped.")


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        debug=settings.debug,
        lifespan=lifespan,
    )
    app.add_middleware(RequestIDMiddleware)
    register_exception_handlers(app)
    app.include_router(api_router, prefix=settings.api_prefix)
    return app


app = create_app()
