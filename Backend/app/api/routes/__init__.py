from fastapi import APIRouter

from app.api.routes.health import router as health_router
from app.api.routes.predict import router as predict_router

v1_router = APIRouter()
v1_router.include_router(health_router, tags=["health"])
v1_router.include_router(predict_router, tags=["predict"])

api_router = APIRouter()
api_router.include_router(v1_router, prefix="/v1")
api_router.include_router(v1_router)
