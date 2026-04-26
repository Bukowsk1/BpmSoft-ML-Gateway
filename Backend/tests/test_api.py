from fastapi.testclient import TestClient

from app.main import create_app
from app.schemas.common import ModelStatus
from app.schemas.demand import DemandPredictionResponse
from app.schemas.price import PricePredictionResponse
from app.services.price_mock import PriceMockService


class FakeDemandAdapter:
    def status(self):
        return ModelStatus(
            name="Forecasting-demand",
            loaded=True,
            artifact_path="/tmp/champion_model_best.zip",
            details="Модель успешно загружена и готова к работе.",
        )

    def predict(self, payload):
        item = payload.records[0].model_dump()
        item["predicted_quantity"] = 123.45
        return DemandPredictionResponse(
            model_name="Karina demand champion",
            rows=1,
            prediction_column="predicted_quantity",
            items=[item],
        )


class FakeRegistry:
    def __init__(self, settings):
        self.settings = settings
        self.demand_adapter = FakeDemandAdapter()
        self.price_service = PriceMockService()

    def load(self):
        return None

    def demand_status(self):
        return self.demand_adapter.status()


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


def test_healthcheck_returns_model_status(monkeypatch):
    client = create_test_client(monkeypatch)

    response = client.get("/api/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["demand_model"]["loaded"] is True
    assert payload["demand_model"]["name"] == "Forecasting-demand"
    assert "x-request-id" in response.headers


def test_v1_healthcheck_supports_request_id_passthrough(monkeypatch):
    client = create_test_client(monkeypatch)

    response = client.get("/api/v1/health", headers={"X-Request-ID": "demo-request-123"})

    assert response.status_code == 200
    assert response.headers["x-request-id"] == "demo-request-123"


def test_sample_endpoints_return_demo_payloads(monkeypatch):
    client = create_test_client(monkeypatch)

    demand_sample = client.get("/api/v1/predict/demand/sample")
    price_sample = client.get("/api/v1/predict/price/sample")

    assert demand_sample.status_code == 200
    assert price_sample.status_code == 200
    assert demand_sample.json()["records"][0]["sku"] == "MI-006"
    assert len(demand_sample.json()["records"]) == 2
    assert price_sample.json()["sku"] == "MI-006"


def test_price_prediction_returns_mock_payload(monkeypatch):
    client = create_test_client(monkeypatch)

    response = client.post(
        "/api/predict/price",
        json={
            "sku": "MI-006",
            "brand": "MiBrand1",
            "category": "Milk",
            "region": "PL-Central",
            "current_price": 2.38,
            "stock_available": 141,
            "delivered_qty": 128,
            "promotion_flag": 0,
        },
    )

    assert response.status_code == 200
    payload = PricePredictionResponse.model_validate(response.json())
    assert payload.model_name == "Vlad pricing mock"
    assert payload.is_mock is True
    assert payload.recommended_price > 0


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
    assert payload.items[0].predicted_quantity == 123.45
