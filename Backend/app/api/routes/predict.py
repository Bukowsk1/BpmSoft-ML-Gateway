from fastapi import APIRouter, Request

from app.core.audit import log_audit
from app.schemas.demand import DemandPredictionRequest, DemandPredictionResponse
from app.schemas.price import PricePredictionRequest, PricePredictionResponse

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


@router.get("/price/sample")
def get_price_sample() -> dict:
    return {
        "sku": "MI-006",
        "brand": "MiBrand1",
        "category": "Milk",
        "region": "PL-Central",
        "current_price": 2.38,
        "stock_available": 141,
        "delivered_qty": 128,
        "promotion_flag": 0,
    }


@router.post("/demand", response_model=DemandPredictionResponse)
def predict_demand(
    payload: DemandPredictionRequest,
    request: Request,
) -> DemandPredictionResponse:
    registry = request.app.state.model_registry
    response = registry.demand_adapter.predict(payload)
    log_audit(
        "predict_demand",
        request_id=getattr(request.state, "request_id", None),
        rows=response.rows,
        skus=[item.sku for item in response.items],
        prediction_column=response.prediction_column,
    )
    return response


@router.post("/price", response_model=PricePredictionResponse)
def predict_price(
    payload: PricePredictionRequest,
    request: Request,
) -> PricePredictionResponse:
    registry = request.app.state.model_registry
    response = registry.price_service.predict(payload)
    log_audit(
        "predict_price",
        request_id=getattr(request.state, "request_id", None),
        sku=payload.sku,
        region=payload.region,
        recommended_price=response.recommended_price,
        is_mock=response.is_mock,
    )
    return response
