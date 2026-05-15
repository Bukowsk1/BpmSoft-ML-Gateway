from fastapi import APIRouter, Request
from fastapi import HTTPException

from app.core.audit import log_audit
from app.schemas.demand import DemandMetricsResponse, DemandPredictionRequest, DemandPredictionResponse

router = APIRouter(prefix="/predict")


@router.get("/demand/sample")
def get_demand_sample() -> dict:
    return {
        "records": [
            {
                "date": "2022-01-21",
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
                "units_sold": 9,
            },
            {
                "date": "2022-01-21",
                "sku": "YO-020",
                "brand": "YoBrand3",
                "segment": "Yogurt-Seg2",
                "category": "Yogurt",
                "channel": "Retail",
                "region": "PL-Central",
                "pack_type": "Carton",
                "price_unit": 4.84,
                "promotion_flag": 0,
                "delivery_days": 2,
                "stock_available": 161,
                "delivered_qty": 177,
                "units_sold": 13,
            }
        ]
    }


@router.get("/demand/metrics", response_model=DemandMetricsResponse)
def get_demand_metrics(request: Request) -> DemandMetricsResponse:
    registry = request.app.state.model_registry
    metrics = registry.metrics_service.get_metrics()
    if metrics is None:
        raise HTTPException(status_code=503, detail=registry.metrics_service.load_error() or "RL metrics are not loaded.")
    return metrics


@router.post("/demand", response_model=DemandPredictionResponse)
def predict_demand(
    payload: DemandPredictionRequest,
    request: Request,
) -> DemandPredictionResponse:
    registry = request.app.state.model_registry
    response = registry.demand_router.predict(payload)
    log_audit(
        "predict_demand",
        request_id=getattr(request.state, "request_id", None),
        rows=response.rows,
        skus=[item.sku for item in response.items],
        prediction_column=response.prediction_column,
        selected_models=[item.selected_model for item in response.items],
    )
    return response
