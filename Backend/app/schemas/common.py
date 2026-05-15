from pydantic import BaseModel


class ModelStatus(BaseModel):
    name: str
    loaded: bool
    artifact_path: str
    details: str


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str
    demand_models: list[ModelStatus]
