from fastapi.testclient import TestClient

from app.main import create_app
from app.schemas.common import ModelStatus
from app.schemas.demand import DemandMetricsResponse, DemandMetricRow, DemandPredictionResponse


class FakeKarinaAdapter:
    def status(self):
        return ModelStatus(
            name="Forecasting-demand",
            loaded=True,
            artifact_path="/tmp/champion_model_best.zip",
            details="Модель успешно загружена и готова к работе.",
        )


class FakeRLAdapter:
    def status(self):
        return ModelStatus(
            name="RL Demand",
            loaded=False,
            artifact_path="/tmp/rl_demand_model.zip",
            details="Missing RL artifacts.",
        )


class FakeDemandRouter:
    def predict(self, payload):
        items = []
        for record in payload.records:
            row = record.model_dump()
            row["karina_prediction"] = 123.45
            row["rl_prediction"] = None
            row["predicted_quantity"] = 123.45
            row["selected_model"] = "karina"
            row["routing_reason"] = "Karina is champion."
            items.append(row)
        return DemandPredictionResponse(
            model_name="Demand AutoML Router",
            rows=len(items),
            prediction_column="predicted_quantity",
            items=items,
        )


class FakeMetricsService:
    def __init__(self):
        self._metrics = DemandMetricsResponse(
            overall=DemandMetricRow(
                label="overall",
                rows=100,
                mae_baseline=5.0,
                mae_rl=4.5,
                mae_gain=0.5,
                rmse_baseline=7.0,
                rmse_rl=6.4,
                rmse_gain=0.6,
                mape_baseline=30.0,
                mape_rl=31.0,
                mape_gain=-1.0,
                smape_baseline=27.0,
                smape_rl=25.6,
                smape_gain=1.4,
            ),
            by_category=[],
            by_segment=[],
            by_sku=[],
            routing_policy="Karina by default.",
            rl_ready_for_routing=False,
        )

    def get_metrics(self):
        return self._metrics

    def load_error(self):
        return None


class FakeRegistry:
    def __init__(self, settings):
        self.settings = settings
        self.karina_adapter = FakeKarinaAdapter()
        self.rl_adapter = FakeRLAdapter()
        self.demand_router = FakeDemandRouter()
        self.metrics_service = FakeMetricsService()

    def load(self):
        return None

    def demand_statuses(self):
        return [self.karina_adapter.status(), self.rl_adapter.status()]


def create_test_client(monkeypatch):
    monkeypatch.setattr("app.main.ModelRegistry", FakeRegistry)
    app = create_app()
    settings = app.state.settings if hasattr(app.state, "settings") else None
    if settings is None:
        from app.core.config import get_settings

        settings = get_settings()
    app.state.settings = settings
    app.state.model_registry = FakeRegistry(settings)
    return TestClient(app)


def test_healthcheck_returns_model_statuses(monkeypatch):
    client = create_test_client(monkeypatch)

    response = client.get("/api/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert len(payload["demand_models"]) == 2
    assert payload["demand_models"][0]["name"] == "Forecasting-demand"
    assert "x-request-id" in response.headers


def test_v1_healthcheck_supports_request_id_passthrough(monkeypatch):
    client = create_test_client(monkeypatch)

    response = client.get("/api/v1/health", headers={"X-Request-ID": "demo-request-123"})

    assert response.status_code == 200
    assert response.headers["x-request-id"] == "demo-request-123"


def test_demand_sample_endpoint(monkeypatch):
    client = create_test_client(monkeypatch)

    demand_sample = client.get("/api/v1/predict/demand/sample")

    assert demand_sample.status_code == 200
    assert demand_sample.json()["records"][0]["sku"] == "MI-006"
    assert len(demand_sample.json()["records"]) == 2


def test_demand_metrics_endpoint(monkeypatch):
    client = create_test_client(monkeypatch)

    response = client.get("/api/predict/demand/metrics")

    assert response.status_code == 200
    payload = response.json()
    assert payload["overall"]["label"] == "overall"
    assert payload["rl_ready_for_routing"] is False


def test_demand_prediction_returns_batch_response(monkeypatch):
    client = create_test_client(monkeypatch)

    response = client.post(
        "/api/predict/demand",
        json={
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
        },
    )

    assert response.status_code == 200
    payload = DemandPredictionResponse.model_validate(response.json())
    assert payload.rows == 1
    assert payload.items[0].sku == "MI-006"
    assert payload.items[0].karina_prediction == 123.45
    assert payload.items[0].selected_model == "karina"
