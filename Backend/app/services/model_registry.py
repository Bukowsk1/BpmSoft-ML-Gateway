from app.core.config import Settings
from app.schemas.common import ModelStatus
from app.services.demand_router import DemandRouterService
from app.services.demand_adapter import DemandModelAdapter
from app.services.rl_demand_adapter import RLDemandAdapter
from app.services.rl_metrics_service import RLMetricsService


class ModelRegistry:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.karina_adapter = DemandModelAdapter(
            package_dir=settings.karina_package_dir,
            artifact_path=settings.karina_model_path,
        )
        self.rl_adapter = RLDemandAdapter(
            artifact_path=settings.rl_model_path,
            preprocessor_path=settings.rl_preprocessor_path,
            reference_data_path=settings.rl_reference_data_path,
        )
        self.metrics_service = RLMetricsService(settings.rl_metrics_dir)
        self.demand_router = DemandRouterService(
            karina_adapter=self.karina_adapter,
            rl_adapter=self.rl_adapter,
            metrics_service=self.metrics_service,
        )

    def load(self) -> None:
        self.karina_adapter.load()
        self.rl_adapter.load()
        self.metrics_service.load()

    def demand_statuses(self) -> list[ModelStatus]:
        return [self.karina_adapter.status(), self.rl_adapter.status()]
