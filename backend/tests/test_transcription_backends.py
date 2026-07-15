from pathlib import Path
from types import SimpleNamespace

import pytest

from backend.app.config import Settings
from backend.app.services.processes import ProcessRegistry
from backend.app.services.whisper import (
    FasterWhisperService,
    Readiness,
    TranscriptionService,
    faster_whisper_readiness,
    transcript_from_faster_whisper,
)


def test_faster_whisper_segments_match_transcript_contract() -> None:
    result = transcript_from_faster_whisper(
        [
            SimpleNamespace(
                start=0.0,
                end=1.25,
                text="Clear CUDA segment",
                words=[
                    SimpleNamespace(probability=0.9),
                    SimpleNamespace(probability=0.8),
                ],
            ),
            SimpleNamespace(
                start=1.25,
                end=2.0,
                text="Uncertain CUDA segment",
                avg_logprob=-1.5,
            ),
        ],
        duration_ms=2000,
        threshold=0.6,
    )

    assert [segment.id for segment in result.segments] == ["seg-0001", "seg-0002"]
    assert result.segments[0].start_ms == 0
    assert result.segments[0].end_ms == 1250
    assert result.segments[0].uncertain is False
    assert result.segments[1].uncertain is True


def test_auto_backend_prefers_ready_faster_whisper(monkeypatch) -> None:
    monkeypatch.setattr(
        "backend.app.services.whisper.faster_whisper_readiness",
        lambda settings: Readiness(True, "ready"),
    )
    service = TranscriptionService(Settings(_env_file=None), ProcessRegistry())
    assert service.selected_backend() == "faster_whisper"


def test_auto_backend_falls_back_to_whisper_cpp(monkeypatch) -> None:
    monkeypatch.setattr(
        "backend.app.services.whisper.faster_whisper_readiness",
        lambda settings: Readiness(False, "not ready"),
    )
    service = TranscriptionService(Settings(_env_file=None), ProcessRegistry())
    assert service.selected_backend() == "whisper_cpp"


def test_explicit_faster_whisper_does_not_fallback(monkeypatch) -> None:
    monkeypatch.setattr(
        "backend.app.services.whisper.faster_whisper_readiness",
        lambda settings: Readiness(False, "not ready"),
    )
    service = TranscriptionService(
        Settings(transcription_backend="faster_whisper"), ProcessRegistry()
    )
    assert service.selected_backend() == "faster_whisper"


def test_faster_whisper_uses_batched_inference_pipeline(monkeypatch) -> None:
    calls: dict[str, object] = {}

    class FakeWhisperModel:
        def __init__(self, model_ref: str, device: str, compute_type: str) -> None:
            calls["model_ref"] = model_ref
            calls["device"] = device
            calls["compute_type"] = compute_type

    class FakeBatchedInferencePipeline:
        def __init__(self, model: FakeWhisperModel) -> None:
            calls["pipeline_model"] = model

        def transcribe(self, audio: str, **kwargs: object):
            calls["audio"] = audio
            calls["kwargs"] = kwargs
            return [
                SimpleNamespace(start=0.0, end=1.0, text="Batched segment")
            ], SimpleNamespace()

    monkeypatch.setitem(
        __import__("sys").modules,
        "faster_whisper",
        SimpleNamespace(
            WhisperModel=FakeWhisperModel,
            BatchedInferencePipeline=FakeBatchedInferencePipeline,
        ),
    )

    service = FasterWhisperService(
        Settings(
            _env_file=None,
            faster_whisper_model_name="turbo",
            faster_whisper_model_path=None,
            faster_whisper_compute_type="int8",
            faster_whisper_batch_size=8,
            faster_whisper_vad_filter=True,
        )
    )
    result = service.transcribe("lecture", Path("audio.wav"), 1000)

    assert service._pipeline is None
    assert result.segments[0].text == "Batched segment"
    assert calls["model_ref"] == "turbo"
    assert calls["device"] == "cuda"
    assert calls["compute_type"] == "int8"
    assert calls["audio"] == "audio.wav"
    assert calls["kwargs"] == {
        "beam_size": 5,
        "batch_size": 8,
        "language": "en",
        "vad_filter": True,
    }


def test_faster_whisper_unloads_pipeline_after_transcription_failure(
    monkeypatch,
) -> None:
    class FakeWhisperModel:
        def __init__(self, model_ref: str, device: str, compute_type: str) -> None:
            pass

    class FakeBatchedInferencePipeline:
        def __init__(self, model: FakeWhisperModel) -> None:
            pass

        def transcribe(self, audio: str, **kwargs: object):
            raise RuntimeError("transcription failed")

    monkeypatch.setitem(
        __import__("sys").modules,
        "faster_whisper",
        SimpleNamespace(
            WhisperModel=FakeWhisperModel,
            BatchedInferencePipeline=FakeBatchedInferencePipeline,
        ),
    )

    service = FasterWhisperService(Settings(_env_file=None))

    with pytest.raises(RuntimeError, match="transcription failed"):
        service.transcribe("lecture", Path("audio.wav"), 1000)

    assert service._pipeline is None


def test_faster_whisper_readiness_accepts_local_model_path(
    tmp_path: Path, monkeypatch
) -> None:
    model_dir = tmp_path / "turbo-ct2"
    model_dir.mkdir()
    monkeypatch.setitem(
        __import__("sys").modules,
        "faster_whisper",
        SimpleNamespace(),
    )
    monkeypatch.setitem(
        __import__("sys").modules,
        "ctranslate2",
        SimpleNamespace(get_cuda_device_count=lambda: 1),
    )

    readiness = faster_whisper_readiness(
        Settings(faster_whisper_model_path=model_dir)
    )

    assert readiness.ready is True
    assert str(model_dir) in readiness.detail
