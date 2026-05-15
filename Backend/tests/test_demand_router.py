import pandas as pd

from app.schemas.common import ModelStatus
from app.schemas.demand import DemandMetricRow, DemandMetricsResponse
from app.services.demand_router import DemandRouterService


class StubKarinaAdapter:
    def predict_frame(self, records):
        return pd.DataFrame(
            [
                {
                    **records[0].model_dump(mode="json"),
                    "predicted_quantity": 10.0,
                }
            ]
        )


class StubRLAdapter:
    def __init__(self, loaded: bool, prediction: float | None = 12.0) -> None:
        self._loaded = loaded
        self._prediction = prediction

    def status(self):
        return ModelStatus(
            name="RL Demand v2",
            loaded=self._loaded,
            artifact_path="/tmp/rl_demand_model.zip",
            details="ok" if self._loaded else "missing",
        )

    def predict_frame(self, payload_records):
        if not self._loaded or self._prediction is None:
            return None
        return pd.DataFrame([{**payload_records[0], "rl_predicted_quantity": self._prediction}])


class StubMetricsService:
    def __init__(self, metrics: DemandMetricsResponse | None) -> None:
        self._metrics = metrics

    def get_metrics(self):
        return self._metrics

    def get_best_row(self, scope: str, label: str):
        if self._metrics is None:
            return None
        mapping = {
            "sku": self._metrics.by_sku,
            "segment": self._metrics.by_segment,
            "category": self._metrics.by_category,
            "overall": [self._metrics.overall],
        }
        for row in mapping.get(scope, []):
            if row.label == label:
                return row
        return None


def build_metrics() -> DemandMetricsResponse:
    return DemandMetricsResponse(
        overall=DemandMetricRow(
            label="overall",
            rows=1000,
            mae_baseline=5.0,
            mae_rl=4.5,
            mae_gain=0.5,
            rmse_baseline=7.0,
            rmse_rl=6.0,
            rmse_gain=1.0,
            mape_baseline=30.0,
            mape_rl=29.0,
            mape_gain=1.0,
            smape_baseline=27.0,
            smape_rl=25.5,
            smape_gain=1.5,
        ),
        by_category=[
            DemandMetricRow(
                label="Milk",
                rows=100,
                mae_baseline=5.0,
                mae_rl=4.8,
                mae_gain=0.2,
                rmse_baseline=7.0,
                rmse_rl=6.7,
                rmse_gain=0.3,
                mape_baseline=30.0,
                mape_rl=29.0,
                mape_gain=1.0,
                smape_baseline=27.0,
                smape_rl=26.4,
                smape_gain=0.6,
            )
        ],
        by_segment=[
            DemandMetricRow(
                label="Milk-Seg3",
                rows=50,
                mae_baseline=5.0,
                mae_rl=4.7,
                mae_gain=0.3,
                rmse_baseline=7.0,
                rmse_rl=6.6,
                rmse_gain=0.4,
                mape_baseline=30.0,
                mape_rl=29.0,
                mape_gain=1.0,
                smape_baseline=27.0,
                smape_rl=26.2,
                smape_gain=0.8,
            )
        ],
        by_sku=[
            DemandMetricRow(
                label="MI-006",
                rows=25,
                mae_baseline=5.0,
                mae_rl=4.5,
                mae_gain=0.5,
                rmse_baseline=7.0,
                rmse_rl=6.3,
                rmse_gain=0.7,
                mape_baseline=30.0,
                mape_rl=28.0,
                mape_gain=2.0,
                smape_baseline=27.0,
                smape_rl=25.8,
                smape_gain=1.2,
            )
        ],
        routing_policy="proxy",
        rl_ready_for_routing=True,
    )


def test_router_selects_rl_for_strong_sku_profile():
    from app.schemas.demand import DemandPredictionRequest

    payload = DemandPredictionRequest.model_validate(
        {
            "records": [
                {
                    "date": "2025-01-07",
                    "sku": "MI-006",
                    "brand": "MiBrand1",
                    "segment": "Milk-Seg3",
                    "category": "Milk",
                    "channel": "Retail",
                    "region": "PL-Central",
                    "pack_type": "Multipack",
                    "price_unit": 2.38,
                    "promotion_flag": 0,
                    "delivery_days": 1,
                    "stock_available": 141,
                    "delivered_qty": 128,
                    "units_sold": 0,
                }
            ]
        }
    )

    router = DemandRouterService(
        karina_adapter=StubKarinaAdapter(),
        rl_adapter=StubRLAdapter(loaded=True, prediction=12.0),
        metrics_service=StubMetricsService(build_metrics()),
    )

    response = router.predict(payload)

    assert response.items[0].selected_model == "rl_v2"
    assert response.items[0].predicted_quantity == 12.0
    assert "SKU MI-006" in response.items[0].routing_reason


def test_router_falls_back_to_karina_without_live_rl():
    from app.schemas.demand import DemandPredictionRequest

    payload = DemandPredictionRequest.model_validate(
        {
            "records": [
                {
                    "date": "2025-01-07",
                    "sku": "MI-006",
                    "brand": "MiBrand1",
                    "segment": "Milk-Seg3",
                    "category": "Milk",
                    "channel": "Retail",
                    "region": "PL-Central",
                    "pack_type": "Multipack",
                    "price_unit": 2.38,
                    "promotion_flag": 0,
                    "delivery_days": 1,
                    "stock_available": 141,
                    "delivered_qty": 128,
                    "units_sold": 0,
                }
            ]
        }
    )

    router = DemandRouterService(
        karina_adapter=StubKarinaAdapter(),
        rl_adapter=StubRLAdapter(loaded=False),
        metrics_service=StubMetricsService(build_metrics()),
    )

    response = router.predict(payload)

    assert response.items[0].selected_model == "karina"
    assert response.items[0].predicted_quantity == 10.0
    assert "Karina" in response.items[0].routing_reason
