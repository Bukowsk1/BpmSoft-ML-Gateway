import sys
import types

from app.services.demand_adapter import DemandModelAdapter


def test_demand_adapter_loads_model_from_zip_artifact(tmp_path, monkeypatch):
    artifact_path = tmp_path / "champion_model_best.zip"
    artifact_path.write_bytes(b"fake-zip-content")

    fake_model_instance = object()

    fake_src_module = types.ModuleType("src")
    fake_model_module = types.ModuleType("src.model")

    class FakeDemandForecastModel:
        @classmethod
        def load(cls, path: str):
            assert path == str(artifact_path)
            return fake_model_instance

    fake_model_module.DemandForecastModel = FakeDemandForecastModel
    monkeypatch.setitem(sys.modules, "src", fake_src_module)
    monkeypatch.setitem(sys.modules, "src.model", fake_model_module)

    adapter = DemandModelAdapter(package_dir=tmp_path, artifact_path=artifact_path)

    adapter.load()

    assert adapter.model is fake_model_instance
    assert adapter.status().loaded is True
    assert adapter.status().details == "Модель успешно загружена и готова к работе."
