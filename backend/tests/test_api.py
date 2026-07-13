from pathlib import Path

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
