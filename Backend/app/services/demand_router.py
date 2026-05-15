from __future__ import annotations

from typing import Any

import pandas as pd

from app.schemas.demand import DemandPredictionItem, DemandPredictionRequest, DemandPredictionResponse
from app.services.demand_adapter import DemandModelAdapter
from app.services.rl_demand_adapter import RLDemandAdapter
from app.services.rl_metrics_service import RLMetricsService


class DemandRouterService:
    SKU_SMAPE_THRESHOLD = 0.75
    SEGMENT_SMAPE_THRESHOLD = 0.50
    CATEGORY_SMAPE_THRESHOLD = 0.35
    OVERALL_SMAPE_THRESHOLD = 0.25

    def __init__(
        self,
        karina_adapter: DemandModelAdapter,
        rl_adapter: RLDemandAdapter,
        metrics_service: RLMetricsService,
    ) -> None:
        self.karina_adapter = karina_adapter
        self.rl_adapter = rl_adapter
        self.metrics_service = metrics_service

    def predict(self, payload: DemandPredictionRequest) -> DemandPredictionResponse:
        karina_frame = self.karina_adapter.predict_frame(payload.records)
        rl_frame = self.rl_adapter.predict_frame([record.model_dump(mode="json") for record in payload.records])

        merged = karina_frame.copy()
        merged = merged.rename(columns={"predicted_quantity": "karina_prediction"})

        if rl_frame is not None:
            merged["rl_prediction"] = rl_frame["rl_predicted_quantity"]
        else:
            merged["rl_prediction"] = None

        selected_models = []
        selected_predictions = []
        routing_reasons = []

        for _, row in merged.iterrows():
            selected_model, reason = self._select_model(row)
            selected_models.append(selected_model)
            routing_reasons.append(reason)
            if selected_model == "RL agent" and pd.notnull(row["rl_prediction"]):
                selected_predictions.append(float(row["rl_prediction"]))
            else:
                selected_predictions.append(float(row["karina_prediction"]))

        merged["selected_model"] = selected_models
        merged["routing_reason"] = routing_reasons
        merged["predicted_quantity"] = selected_predictions
        merged = merged.where(pd.notnull(merged), None)

        items = [DemandPredictionItem.model_validate(item) for item in merged.to_dict(orient="records")]
        return DemandPredictionResponse(
            model_name="Demand AutoML Router",
            rows=len(items),
            prediction_column="predicted_quantity",
            items=items,
        )

    def _select_model(self, row: pd.Series) -> tuple[str, str]:
        metrics = self.metrics_service.get_metrics()
        rl_ready = self.rl_adapter.status().loaded

        if not rl_ready:
            return "karina", "RL-модель пока не подключена, используем Karina как чемпион."

        if metrics is None:
            return "karina", "Офлайн-метрики RL не загружены, используем Karina как чемпион."

        segment_label = str(row["segment"])
        category_label = str(row["category"])
        sku_label = str(row["sku"])

        sku_match = self.metrics_service.get_best_row("sku", sku_label)
        if self._is_positive_proxy(sku_match, self.SKU_SMAPE_THRESHOLD):
            return "RL agent", (
                f"Товар {sku_label}: RL agent точнее бейзлайна "
                f"(улучшение SMAPE: {sku_match.smape_gain:.2f}%)."
            )
        if self._is_negative_proxy(sku_match):
            return "karina", (
                f"Товар {sku_label}: RL agent ошибается чаще бейзлайна, "
                "безопасно переключаем на модель Karina."
            )

        segment_match = self.metrics_service.get_best_row("segment", segment_label)
        if self._is_positive_proxy(segment_match, self.SEGMENT_SMAPE_THRESHOLD):
            return "RL agent", (
                f"Сегмент {segment_label}: RL agent точнее бейзлайна "
                f"(улучшение SMAPE: {segment_match.smape_gain:.2f}%)."
            )
        if self._is_negative_proxy(segment_match):
            return "karina", (
                f"Сегмент {segment_label}: RL agent ошибается чаще бейзлайна, "
                "безопасно переключаем на модель Karina."
            )

        category_match = self.metrics_service.get_best_row("category", category_label)
        if self._is_positive_proxy(category_match, self.CATEGORY_SMAPE_THRESHOLD):
            return "RL agent", (
                f"Категория {category_label}: RL agent точнее бейзлайна "
                f"(улучшение SMAPE: {category_match.smape_gain:.2f}%)."
            )
        if self._is_negative_proxy(category_match):
            return "karina", (
                f"Категория {category_label}: RL agent ошибается чаще бейзлайна, "
                "безопасно переключаем на модель Karina."
            )

        if self._is_positive_proxy(metrics.overall, self.OVERALL_SMAPE_THRESHOLD):
            return "RL agent", (
                "В среднем RL agent точнее бейзлайна, "
                "поэтому выбран как лучший кандидат."
            )

        return "karina", "Перестраховываемся и используем стабильную модель Karina."

    @staticmethod
    def _is_positive_proxy(metric_row: Any | None, threshold: float) -> bool:
        if metric_row is None or metric_row.smape_gain is None or metric_row.mae_gain is None:
            return False
        return metric_row.smape_gain >= threshold and metric_row.mae_gain > 0

    @staticmethod
    def _is_negative_proxy(metric_row: Any | None) -> bool:
        if metric_row is None or metric_row.smape_gain is None:
            return False
        return metric_row.smape_gain <= 0
