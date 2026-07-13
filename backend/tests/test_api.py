from pathlib import Path

from fastapi.testclient import TestClient

from backend.app.config import Settings
from backend.app.main import create_app
from backend.app.services.whisper import Readiness


async def _available_models():
    return ["local-qwen"]


def test_upload_rejects_unsupported_extension(tmp_path: Path) -> None:
    app = create_app(Settings(pocketta_data_dir=tmp_path))
    with TestClient(app) as client:
        response = client.post(
            "/api/lectures", files={"file": ("notes.txt", b"not media", "text/plain")}
        )
    assert response.status_code == 415


def test_empty_upload_leaves_no_lecture(tmp_path: Path) -> None:
    app = create_app(Settings(pocketta_data_dir=tmp_path))
    with TestClient(app) as client:
        response = client.post(
            "/api/lectures", files={"file": ("empty.mp3", b"", "audio/mpeg")}
        )
        assert response.status_code == 400
        assert client.get("/api/lectures").json() == []


def test_health_reports_faster_whisper_without_requiring_it_in_auto(
    tmp_path: Path, monkeypatch
) -> None:
    whisper_cli = tmp_path / "whisper-cli"
    whisper_model = tmp_path / "ggml-base.en.bin"
    whisper_cli.write_text("stub", encoding="utf-8")
    whisper_model.write_text("stub", encoding="utf-8")
    monkeypatch.setattr(
        "backend.app.services.whisper.faster_whisper_readiness",
        lambda settings: Readiness(False, "optional CUDA path is not ready"),
    )
    monkeypatch.setattr(
        "backend.app.api.lectures.faster_whisper_readiness",
        lambda settings: Readiness(False, "optional CUDA path is not ready"),
    )
    monkeypatch.setattr(
        "backend.app.services.lm_studio.LMStudioService.available_models",
        lambda self: _available_models(),
    )
    app = create_app(
        Settings(
            pocketta_data_dir=tmp_path,
            whisper_cli_path=whisper_cli,
            whisper_model_path=whisper_model,
            lm_studio_model_id="local-qwen",
        )
    )

    with TestClient(app) as client:
        response = client.get("/api/health")

    assert response.status_code == 200
    body = response.json()
    assert body["ready"] is True
    assert body["components"]["faster_whisper"]["ready"] is False
    assert "selected=whisper_cpp" in body["components"]["transcription_backend"]["detail"]
