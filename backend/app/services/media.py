from __future__ import annotations

import json
from pathlib import Path

from ..config import Settings
from .processes import ProcessRegistry


SUPPORTED_EXTENSIONS = {
    ".aac",
    ".flac",
    ".m4a",
    ".mkv",
    ".mov",
    ".mp3",
    ".mp4",
    ".ogg",
    ".wav",
    ".webm",
}


class MediaService:
    def __init__(self, settings: Settings, processes: ProcessRegistry):
        self.settings = settings
        self.processes = processes

    def normalize(self, lecture_id: str, source: Path, output: Path) -> int:
        probe = self.processes.run(
            lecture_id,
            [
                self.settings.ffprobe_path,
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "json",
                str(source),
            ],
        )
        try:
            duration_ms = round(float(json.loads(probe)["format"]["duration"]) * 1000)
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
            raise ValueError("FFprobe could not determine the recording duration") from error
        if duration_ms <= 0:
            raise ValueError("The uploaded recording has no playable duration")
        self.processes.run(
            lecture_id,
            [
                self.settings.ffmpeg_path,
                "-nostdin",
                "-y",
                "-i",
                str(source),
                "-vn",
                "-ac",
                "1",
                "-ar",
                "16000",
                "-c:a",
                "pcm_s16le",
                str(output),
            ],
        )
        return duration_ms
