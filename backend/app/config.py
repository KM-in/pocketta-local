from __future__ import annotations

import os
import shutil
from pathlib import Path
from urllib.parse import urlparse

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    pocketta_data_dir: Path = Path("./data")
    ffmpeg_path: str = "ffmpeg"
    ffprobe_path: str = "ffprobe"
    whisper_cli_path: Path = Path("./vendor/whisper.cpp/build/bin/whisper-cli")
    whisper_model_path: Path = Path("./vendor/whisper.cpp/models/ggml-base.en.bin")
    whisper_use_gpu: bool = False
    lm_studio_base_url: str = "http://127.0.0.1:1234/v1"
    lm_studio_model_id: str = ""
    lm_studio_api_key: str = ""
    lm_studio_timeout_seconds: float = 480.0
    max_audio_minutes: int = 15
    max_upload_mb: int = 200
    uncertain_confidence_threshold: float = 0.60

    @field_validator("lm_studio_base_url")
    @classmethod
    def lm_studio_must_be_loopback(cls, value: str) -> str:
        host = urlparse(value).hostname
        if host not in {"127.0.0.1", "localhost", "::1"}:
            raise ValueError("LM Studio must use a loopback URL")
        return value.rstrip("/")

    @property
    def database_path(self) -> Path:
        return self.pocketta_data_dir / "pocketta.sqlite3"

    @property
    def lectures_dir(self) -> Path:
        return self.pocketta_data_dir / "lectures"

    def prepare_directories(self) -> None:
        self.lectures_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def executable_available(value: str | Path) -> bool:
        candidate = str(value)
        if os.path.sep in candidate or (os.path.altsep and os.path.altsep in candidate):
            return Path(candidate).expanduser().is_file()
        return shutil.which(candidate) is not None
