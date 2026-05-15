from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from app.schemas.demand import DemandMetricRow, DemandMetricsResponse


class RLMetricsService:
    def __init__(self, metrics_dir: Path) -> None:
        self.metrics_dir = metrics_dir
        self._metrics: DemandMetricsResponse | None = None
        self._load_error: str | None = None

    def load(self) -> None:
        try:
            overall_path = self.metrics_dir / "metrics_overall.json"
            category_path = self.metrics_dir / "metrics_by_category.csv"
            category_baseline_path = self.metrics_dir / "metrics_by_category_baseline.csv"
            segment_path = self.metrics_dir / "metrics_by_segment.csv"
            segment_baseline_path = self.metrics_dir / "metrics_by_segment_baseline.csv"
            sku_path = self.metrics_dir / "metrics_by_sku.csv"
            sku_baseline_path = self.metrics_dir / "metrics_by_sku_baseline.csv"

            for path in (
                overall_path,
                category_path,
                category_baseline_path,
                segment_path,
                segment_baseline_path,
                sku_path,
                sku_baseline_path,
            ):
                if not path.exists():
                    self._load_error = f"Metrics file not found: {path}"
                    self._metrics = None
                    return

            overall_payload = json.loads(overall_path.read_text(encoding="utf-8"))
            test_rl = overall_payload["test_rl"][0]
            test_baseline = overall_payload["test_baseline"][0]

            self._metrics = DemandMetricsResponse(
                overall=self._merge_metric_rows(test_rl, test_baseline),
                by_category=self._load_and_merge(category_path, category_baseline_path),
                by_segment=self._load_and_merge(segment_path, segment_baseline_path),
                by_sku=self._load_and_merge(sku_path, sku_baseline_path),
                routing_policy=(
                    "Логика выбора: проверяем историческую точность от SKU до общей Категории. "
                    "Если RL agent исторически бил бейзлайн — выбираем его. "
                    "Иначе безопасно переключаемся на основную модель (Karina)."
                ),
                rl_ready_for_routing=True,
            )
            self._load_error = None
        except Exception as exc:
            self._metrics = None
            self._load_error = f"{type(exc).__name__}: {exc}"

    def get_metrics(self) -> DemandMetricsResponse | None:
        return self._metrics

    def load_error(self) -> str | None:
        return self._load_error

    def get_best_row(self, scope: str, label: str) -> DemandMetricRow | None:
        metrics = self._metrics
        if metrics is None:
            return None

        rows_map = {
            "sku": metrics.by_sku,
            "segment": metrics.by_segment,
            "category": metrics.by_category,
            "overall": [metrics.overall],
        }
        for row in rows_map.get(scope, []):
            if row.label == label:
                return row
        return None

    def _load_and_merge(self, rl_path: Path, baseline_path: Path) -> list[DemandMetricRow]:
        rl_frame = pd.read_csv(rl_path)
        baseline_frame = pd.read_csv(baseline_path)
        merged = rl_frame.merge(
            baseline_frame,
            on=["label", "rows"],
            suffixes=("_rl", "_baseline"),
        )
        return [self._merge_metric_rows(row, row, frame_row=True) for _, row in merged.iterrows()]

    def _merge_metric_rows(self, rl_row, baseline_row, frame_row: bool = False) -> DemandMetricRow:
        if frame_row:
            label = str(rl_row["label"])
            rows = int(rl_row["rows"])
            mae_rl = float(rl_row["mae_rl"])
            rmse_rl = float(rl_row["rmse_rl"])
            mape_rl = float(rl_row["mape_rl"])
            smape_rl = float(rl_row["smape_rl"])
            mae_baseline = float(rl_row["mae_baseline"])
            rmse_baseline = float(rl_row["rmse_baseline"])
            mape_baseline = float(rl_row["mape_baseline"])
            smape_baseline = float(rl_row["smape_baseline"])
        else:
            label = str(rl_row["label"])
            rows = int(rl_row["rows"])
            mae_rl = float(rl_row["mae"])
            rmse_rl = float(rl_row["rmse"])
            mape_rl = float(rl_row["mape"])
            smape_rl = float(rl_row["smape"])
            mae_baseline = float(baseline_row["mae"])
            rmse_baseline = float(baseline_row["rmse"])
            mape_baseline = float(baseline_row["mape"])
            smape_baseline = float(baseline_row["smape"])

        return DemandMetricRow(
            label=label,
            rows=rows,
            mae_baseline=mae_baseline,
            mae_rl=mae_rl,
            mae_gain=mae_baseline - mae_rl,
            rmse_baseline=rmse_baseline,
            rmse_rl=rmse_rl,
            rmse_gain=rmse_baseline - rmse_rl,
            mape_baseline=mape_baseline,
            mape_rl=mape_rl,
            mape_gain=mape_baseline - mape_rl,
            smape_baseline=smape_baseline,
            smape_rl=smape_rl,
            smape_gain=smape_baseline - smape_rl,
        )
