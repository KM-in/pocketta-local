import json
from pathlib import Path

import pytest

from backend.app.config import Settings
from backend.app.services.media import MediaService


class FakeProcesses:
    def __init__(self, probe_output: str):
        self.probe_output = probe_output
        self.commands: list[list[str]] = []

    def run(self, lecture_id: str, command: list[str]) -> str:
        self.commands.append(command)
        return self.probe_output if len(self.commands) == 1 else ""


def test_media_rejects_corrupt_probe_output(tmp_path: Path) -> None:
    processes = FakeProcesses("not-json")
    service = MediaService(Settings(pocketta_data_dir=tmp_path), processes)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="could not determine"):
        service.normalize("lecture", tmp_path / "source.mp3", tmp_path / "audio.wav")
    assert len(processes.commands) == 1


def test_media_allows_recordings_longer_than_15_minutes(tmp_path: Path) -> None:
    processes = FakeProcesses(json.dumps({"format": {"duration": "901"}}))
    service = MediaService(Settings(pocketta_data_dir=tmp_path), processes)  # type: ignore[arg-type]
    duration = service.normalize(
        "lecture", tmp_path / "source.mp3", tmp_path / "audio.wav"
    )
    assert duration == 901_000
    assert len(processes.commands) == 2


def test_media_normalizes_to_pcm_mono_16khz(tmp_path: Path) -> None:
    processes = FakeProcesses(json.dumps({"format": {"duration": "60.5"}}))
    service = MediaService(Settings(pocketta_data_dir=tmp_path), processes)  # type: ignore[arg-type]
    duration = service.normalize(
        "lecture", tmp_path / "source.m4a", tmp_path / "audio.wav"
    )
    assert duration == 60_500
    command = processes.commands[1]
    assert command[command.index("-ac") + 1] == "1"
    assert command[command.index("-ar") + 1] == "16000"
    assert command[command.index("-c:a") + 1] == "pcm_s16le"
