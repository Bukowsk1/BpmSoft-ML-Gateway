from __future__ import annotations

import logging
import pickle
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from app.schemas.common import ModelStatus

logger = logging.getLogger(__name__)

DATE_COLUMN = "date"
TARGET_COLUMN = "units_sold"
GROUP_COLUMN = "sku"
LAGS = (1, 7, 14, 28)
ROLLING_WINDOWS = (7, 14, 28)


class RLDemandAdapter:
    def __init__(self, artifact_path: Path, preprocessor_path: Path, reference_data_path: Path) -> None:
        self.artifact_path = artifact_path
        self.preprocessor_path = preprocessor_path
        self.reference_data_path = reference_data_path
        self.model: Any | None = None
        self.preprocessor: dict[str, Any] | None = None
        self.history_frame: pd.DataFrame | None = None
        self._load_error: str | None = None

    def load(self) -> None:
        missing = [
            str(path)
            for path in (self.artifact_path, self.preprocessor_path, self.reference_data_path)
            if not path.exists()
        ]
        if missing:
            self._load_error = f"Missing RL artifacts: {', '.join(missing)}"
            logger.warning(self._load_error)
            return

        try:
            from stable_baselines3 import PPO

            self.model = PPO.load(str(self.artifact_path))
            with self.preprocessor_path.open("rb") as file:
                self.preprocessor = pickle.load(file)
            self.history_frame = self._prepare_history(pd.read_csv(self.reference_data_path))
            self._load_error = None
            logger.info("RL demand model loaded from %s", self.artifact_path)
        except Exception as exc:
            self.model = None
            self.preprocessor = None
            self.history_frame = None
            self._load_error = f"{type(exc).__name__}: {exc}"
            logger.exception("Failed to load RL demand model: %s", self._load_error)

    def status(self) -> ModelStatus:
        return ModelStatus(
            name="RL Demand",
            loaded=self.model is not None and self.preprocessor is not None and self.history_frame is not None,
            artifact_path=str(self.artifact_path),
            details=self._load_error or "Модель успешно загружена и готова к работе.",
        )

    def predict_frame(self, payload_records: list[dict[str, Any]]) -> pd.DataFrame | None:
        if self.model is None or self.preprocessor is None or self.history_frame is None:
            return None

        incoming = pd.DataFrame(payload_records)
        incoming[DATE_COLUMN] = pd.to_datetime(incoming[DATE_COLUMN], errors="coerce")
        prepared = []

        for _, row in incoming.iterrows():
            feature_row = self._build_feature_row(row)
            prepared.append(feature_row)

        feature_frame = pd.DataFrame(prepared)
        feature_columns = self.preprocessor["feature_columns"]
        scaler = self.preprocessor["scaler"]
        baseline_model = self.preprocessor["baseline_model"]
        residual_scale = float(self.preprocessor["residual_scale"])
        max_log_target = float(self.preprocessor["max_log_target"])

        feature_input_columns = [column for column in feature_columns if column != "baseline_log_prediction"]
        scaled_features = scaler.transform(feature_frame[feature_input_columns])
        scaled_frame = pd.DataFrame(scaled_features, columns=feature_input_columns, index=feature_frame.index)

        baseline_log_prediction = baseline_model.predict(scaled_frame[feature_input_columns])
        scaled_frame["baseline_log_prediction"] = np.clip(baseline_log_prediction, 0.0, None)

        predictions = []
        for _, row in scaled_frame[feature_columns].iterrows():
            action, _ = self.model.predict(row.to_numpy(dtype=np.float32), deterministic=True)
            delta = float(np.clip(action[0], -3.0, 3.0) * residual_scale)
            final_log_prediction = float(np.clip(row["baseline_log_prediction"] + delta, 0.0, max_log_target))
            predictions.append(float(np.expm1(final_log_prediction)))

        result = incoming.copy()
        result["rl_predicted_quantity"] = predictions
        return result

    def _prepare_history(self, frame: pd.DataFrame) -> pd.DataFrame:
        frame[DATE_COLUMN] = pd.to_datetime(frame[DATE_COLUMN], errors="coerce")
        frame[TARGET_COLUMN] = pd.to_numeric(frame[TARGET_COLUMN], errors="coerce")
        frame = frame.dropna(subset=[DATE_COLUMN, TARGET_COLUMN]).copy()
        frame[TARGET_COLUMN] = frame[TARGET_COLUMN].clip(lower=0.0)
        return frame.sort_values([GROUP_COLUMN, DATE_COLUMN]).reset_index(drop=True)

    def _build_feature_row(self, row: pd.Series) -> dict[str, Any]:
        history = self.history_frame
        assert history is not None

        sku_history = history[
            (history[GROUP_COLUMN] == row[GROUP_COLUMN]) & (history[DATE_COLUMN] < row[DATE_COLUMN])
        ].sort_values(DATE_COLUMN)

        target_series = sku_history[TARGET_COLUMN].astype(float)
        values = target_series.to_numpy()

        feature_row: dict[str, Any] = {
            "price_unit": float(row["price_unit"]),
            "promotion_flag": int(row["promotion_flag"]),
            "delivery_days": int(row["delivery_days"]),
            "stock_available": int(row["stock_available"]),
            "delivered_qty": int(row["delivered_qty"]),
            "day_of_week": row[DATE_COLUMN].dayofweek,
            "day_of_month": row[DATE_COLUMN].day,
            "month": row[DATE_COLUMN].month,
            "quarter": row[DATE_COLUMN].quarter,
            "week_of_year": int(row[DATE_COLUMN].isocalendar().week),
            "is_weekend": int(row[DATE_COLUMN].dayofweek >= 5),
            "day_of_year_sin": np.sin(2 * np.pi * row[DATE_COLUMN].dayofyear / 365.25),
            "day_of_year_cos": np.cos(2 * np.pi * row[DATE_COLUMN].dayofyear / 365.25),
        }

        for lag in LAGS:
            feature_row[f"lag_{lag}"] = float(values[-lag]) if len(values) >= lag else 0.0

        for window in ROLLING_WINDOWS:
            window_values = values[-window:] if len(values) >= window else values
            feature_row[f"rolling_mean_{window}"] = float(np.mean(window_values)) if len(window_values) else 0.0
            feature_row[f"rolling_std_{window}"] = float(np.std(window_values)) if len(window_values) else 0.0

        feature_row["baseline_forecast"] = (
            0.50 * feature_row["rolling_mean_7"]
            + 0.30 * feature_row["lag_7"]
            + 0.20 * feature_row["lag_14"]
        )

        categorical_values = {
            "brand": row["brand"],
            "segment": row["segment"],
            "category": row["category"],
            "channel": row["channel"],
            "region": row["region"],
            "pack_type": row["pack_type"],
            GROUP_COLUMN: row[GROUP_COLUMN],
        }

        feature_columns = self.preprocessor["feature_columns"]
        for column in feature_columns:
            if column.startswith("baseline_log_prediction"):
                continue
            if column in feature_row:
                continue
            feature_row[column] = 0.0

        for category_name, value in categorical_values.items():
            dummy_column = f"{category_name}_{value}"
            if dummy_column in feature_columns:
                feature_row[dummy_column] = 1.0

        return feature_row
