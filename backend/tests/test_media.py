import json
from pathlib import Path

import pytest

from backend.app.config import Settings
from backend.app.services.media import MediaService


class FakeProcesses:
    def __init__(self, *outputs: str):
        self.outputs = list(outputs)
        self.commands: list[list[str]] = []

    def run(self, lecture_id: str, command: list[str]) -> str:
        self.commands.append(command)
        if self.outputs:
            return self.outputs.pop(0)
        return ""


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


def test_media_uses_normalized_wav_duration_when_source_duration_is_missing(
    tmp_path: Path,
) -> None:
    processes = FakeProcesses(
        json.dumps({"format": {"duration": "N/A"}, "streams": [{}]}),
        "",
        json.dumps({"format": {"duration": "12.25"}}),
    )
    service = MediaService(Settings(pocketta_data_dir=tmp_path), processes)  # type: ignore[arg-type]
    duration = service.normalize(
        "lecture", tmp_path / "source.webm", tmp_path / "audio.wav"
    )

    assert duration == 12_250
    assert processes.commands[0][processes.commands[0].index("-show_entries") + 1] == (
        "format=duration:stream=duration"
    )
    assert processes.commands[1][0] == "ffmpeg"
    assert processes.commands[2][-1] == str(tmp_path / "audio.wav")


def test_media_reads_stream_duration_when_format_duration_is_missing(
    tmp_path: Path,
) -> None:
    processes = FakeProcesses(
        json.dumps({"format": {}, "streams": [{"duration": "8.5"}]}),
        "",
    )
    service = MediaService(Settings(pocketta_data_dir=tmp_path), processes)  # type: ignore[arg-type]
    duration = service.normalize(
        "lecture", tmp_path / "source.webm", tmp_path / "audio.wav"
    )

    assert duration == 8_500
    assert len(processes.commands) == 2
