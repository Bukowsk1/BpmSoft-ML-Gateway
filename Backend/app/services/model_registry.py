from app.core.config import Settings
from app.schemas.common import ModelStatus
from app.services.demand_adapter import DemandModelAdapter
from app.services.price_mock import PriceMockService


class ModelRegistry:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.demand_adapter = DemandModelAdapter(
            package_dir=settings.karina_package_dir,
            artifact_path=settings.karina_model_path,
        )
        self.price_service = PriceMockService()

    def load(self) -> None:
        self.demand_adapter.load()

    def demand_status(self) -> ModelStatus:
        return self.demand_adapter.status()
