from pydantic import BaseModel, ConfigDict, Field


class PricePredictionRequest(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "sku": "MI-006",
                "brand": "MiBrand1",
                "category": "Milk",
                "region": "PL-Central",
                "current_price": 2.38,
                "stock_available": 141,
                "delivered_qty": 128,
                "promotion_flag": 0,
            }
        },
    )

    sku: str = Field(..., min_length=1)
    brand: str = Field(..., min_length=1)
    category: str = Field(..., min_length=1)
    region: str = Field(..., min_length=1)
    current_price: float = Field(..., ge=0)
    stock_available: int = Field(..., ge=0)
    delivered_qty: int = Field(..., ge=0)
    promotion_flag: int = Field(..., ge=0, le=1)


class PricePredictionResponse(BaseModel):
    model_name: str
    recommended_price: float
    currency: str
    confidence: float
    is_mock: bool
    reasoning: str
