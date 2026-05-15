from __future__ import annotations

import sys
from pathlib import Path
from typing import Any
import logging

import pandas as pd
from fastapi import HTTPException

from app.schemas.common import ModelStatus
from app.core.runtime_checks import libomp_hint
from app.schemas.demand import DemandPredictionRequest

logger = logging.getLogger(__name__)


class DemandModelAdapter:
    def __init__(self, package_dir: Path, artifact_path: Path) -> None:
        self.package_dir = package_dir
        self.artifact_path = artifact_path
        self.model: Any | None = None
        self._load_error: str | None = None

    def load(self) -> None:
        if not self.artifact_path.exists():
            self._load_error = f"Artifact not found: {self.artifact_path}"
            logger.error(self._load_error)
            return

        try:
            self._ensure_import_path()
            from src.model import DemandForecastModel  # type: ignore

            self.model = DemandForecastModel.load(str(self.artifact_path))
            self._load_error = None
            logger.info("Demand champion model loaded from %s", self.artifact_path)
        except Exception as exc:
            self.model = None
            self._load_error = f"{type(exc).__name__}: {exc}. {libomp_hint()}"
            logger.exception("Failed to load demand model: %s", self._load_error)

    def status(self) -> ModelStatus:
        return ModelStatus(
            name="Forecasting-demand",
            loaded=self.model is not None,
            artifact_path=str(self.artifact_path),
            details=self._load_error or "Модель успешно загружена и готова к работе.",
        )

    def predict_frame(self, records: list[DemandPredictionRequest | Any]) -> pd.DataFrame:
        if self.model is None:
            raise HTTPException(status_code=503, detail={"message": "Demand model is not loaded.", "reason": self._load_error or "Unknown load error."})

        serialized_records = []
        for record in records:
            if hasattr(record, "model_dump"):
                serialized_records.append(record.model_dump(mode="json"))
            else:
                serialized_records.append(record)
        frame = pd.DataFrame(serialized_records)

        # Champion model was trained with target column `quantity`,
        # while the external BPMSoft contract uses `units_sold`.
        frame["quantity"] = frame["units_sold"]

        prediction_frame = self.model.predict(future_df=frame)
        return prediction_frame.where(pd.notnull(prediction_frame), None)

    def _ensure_import_path(self) -> None:
        package_dir = str(self.package_dir)
        if package_dir not in sys.path:
            sys.path.insert(0, package_dir)
