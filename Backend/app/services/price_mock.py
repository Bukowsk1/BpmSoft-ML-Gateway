from app.schemas.price import PricePredictionRequest, PricePredictionResponse


class PriceMockService:
    def predict(self, payload: PricePredictionRequest) -> PricePredictionResponse:
        stock_pressure = 1.03 if payload.stock_available < max(payload.delivered_qty, 1) else 0.98
        promo_adjustment = 0.94 if payload.promotion_flag else 1.05
        region_adjustment = 1.01 + (sum(map(ord, payload.region)) % 7) / 100

        recommended_price = round(
            payload.current_price * stock_pressure * promo_adjustment * region_adjustment,
            2,
        )

        return PricePredictionResponse(
            model_name="Vlad pricing mock",
            recommended_price=recommended_price,
            currency="RUB",
            confidence=0.61,
            is_mock=True,
            reasoning="Симуляция ценообразования",
        )
