from pathlib import Path
from unittest.mock import AsyncMock

from fastapi.testclient import TestClient

from backend.app.config import Settings
from backend.app.main import create_app


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


def test_oversized_upload_cleans_partial_directory(tmp_path: Path) -> None:
    app = create_app(Settings(pocketta_data_dir=tmp_path, max_upload_mb=0))
    with TestClient(app) as client:
        response = client.post(
            "/api/lectures", files={"file": ("large.mp3", b"x", "audio/mpeg")}
        )
        assert response.status_code == 413
        assert client.get("/api/lectures").json() == []
        assert list((tmp_path / "lectures").iterdir()) == []


def test_health_failure_has_actionable_remediation(tmp_path: Path) -> None:
    app = create_app(
        Settings(
            pocketta_data_dir=tmp_path,
            ffmpeg_path="missing-pocketta-ffmpeg",
            ffprobe_path="missing-pocketta-ffprobe",
            lm_studio_model_id="missing-model",
        )
    )
    app.state.processor.lm_studio.available_models = AsyncMock(return_value=[])
    with TestClient(app) as client:
        payload = client.get("/api/health").json()
    assert payload["ready"] is False
    assert payload["components"]["ffmpeg"]["remediation"]
    assert "LM Studio" in payload["components"]["lm_studio"]["remediation"]


def test_delete_removes_database_files_and_api_access(tmp_path: Path) -> None:
    app = create_app(Settings(pocketta_data_dir=tmp_path))
    with TestClient(app) as client:
        lecture_id = "delete-me"
        lecture_dir = tmp_path / "lectures" / lecture_id
        lecture_dir.mkdir()
        source = lecture_dir / "source.mp3"
        source.write_bytes(b"local recording")
        app.state.database.create_lecture(lecture_id, "source.mp3", source)

        response = client.delete(f"/api/lectures/{lecture_id}")
        assert response.status_code == 204
        assert not lecture_dir.exists()
        assert client.get(f"/api/lectures/{lecture_id}").status_code == 404
        assert client.get(f"/api/lectures/{lecture_id}/export.md").status_code == 404
        assert client.get("/api/lectures").json() == []
