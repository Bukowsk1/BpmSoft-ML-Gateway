from datetime import date

from pydantic import BaseModel, ConfigDict, Field, field_validator


class DemandRecord(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
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
        },
    )

    date: date
    sku: str = Field(..., min_length=1)
    brand: str = Field(..., min_length=1)
    segment: str = Field(..., min_length=1)
    category: str = Field(..., min_length=1)
    channel: str = Field(..., min_length=1)
    region: str = Field(..., min_length=1)
    pack_type: str = Field(..., min_length=1)
    price_unit: float = Field(..., ge=0)
    promotion_flag: int = Field(..., ge=0, le=1)
    delivery_days: int = Field(..., ge=0)
    stock_available: int = Field(..., ge=0)
    delivered_qty: int = Field(..., ge=0)
    units_sold: float | None = Field(
        default=None,
        ge=0,
        description="Для будущих периодов можно передавать null.",
    )

    @field_validator(
        "sku",
        "brand",
        "segment",
        "category",
        "channel",
        "region",
        "pack_type",
    )
    @classmethod
    def strip_text(cls, value: str) -> str:
        return value.strip()


class DemandPredictionRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
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
                    },
                    {
                        "date": "2025-01-07",
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
                        "units_sold": 0,
                    },
                ]
            }
        }
    )

    records: list[DemandRecord] = Field(..., min_length=1)


class DemandPredictionItem(BaseModel):
    date: date
    sku: str
    brand: str
    segment: str
    category: str
    channel: str
    region: str
    pack_type: str
    price_unit: float
    promotion_flag: int
    delivery_days: int
    stock_available: int
    delivered_qty: int
    units_sold: float | None = None
    karina_prediction: float
    rl_prediction: float | None = None
    predicted_quantity: float
    selected_model: str
    routing_reason: str


class DemandPredictionResponse(BaseModel):
    model_name: str
    rows: int
    prediction_column: str
    items: list[DemandPredictionItem]


class DemandMetricRow(BaseModel):
    label: str
    rows: int
    mae_baseline: float | None = None
    mae_rl: float
    mae_gain: float | None = None
    rmse_baseline: float | None = None
    rmse_rl: float
    rmse_gain: float | None = None
    mape_baseline: float | None = None
    mape_rl: float
    mape_gain: float | None = None
    smape_baseline: float | None = None
    smape_rl: float
    smape_gain: float | None = None


class DemandMetricsResponse(BaseModel):
    overall: DemandMetricRow
    by_category: list[DemandMetricRow]
    by_segment: list[DemandMetricRow]
    by_sku: list[DemandMetricRow]
    routing_policy: str
    rl_ready_for_routing: bool
