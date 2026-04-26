from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "BPMSoft ML Router"
    app_version: str = "0.1.0"
    api_prefix: str = "/api"
    api_v1_prefix: str = "/v1"
    debug: bool = False
    log_level: str = "INFO"
    host: str = "0.0.0.0"
    port: int = 8000

    backend_dir: Path = Path(__file__).resolve().parents[2]
    project_root: Path = Path(__file__).resolve().parents[3]
    karina_dir: Path = Path(__file__).resolve().parents[3] / "Karina"
    karina_package_dir: Path = Path(__file__).resolve().parents[3] / "Karina" / "Forecasting-demand"
    karina_model_path: Path = Path(__file__).resolve().parents[3] / "Karina" / "champion_model_best.zip"
    vlad_dir: Path = Path(__file__).resolve().parents[3] / "Vlad"
    dashboard_api_base_url: str = "http://127.0.0.1:8000/api"

    model_config = SettingsConfigDict(
        env_prefix="BPMSOFT_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
