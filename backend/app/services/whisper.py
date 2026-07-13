from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any, Literal

from ..config import Settings
from ..models import Transcript, TranscriptSegment
from .processes import ProcessRegistry


BackendName = Literal["whisper_cpp", "faster_whisper"]


class WhisperCppService:
    def __init__(self, settings: Settings, processes: ProcessRegistry):
        self.settings = settings
        self.processes = processes

    def transcribe(self, lecture_id: str, audio: Path, duration_ms: int) -> Transcript:
        output_prefix = audio.parent / "whisper"
        command = [
                str(self.settings.whisper_cli_path),
                "-m",
                str(self.settings.whisper_model_path),
                "-f",
                str(audio),
                "-l",
                "en",
                "-ojf",
                "-of",
                str(output_prefix),
                "-np",
            ]
        if not self.settings.whisper_use_gpu:
            command.append("-ng")
        self.processes.run(lecture_id, command)
        output_path = output_prefix.with_suffix(".json")
        if not output_path.is_file():
            raise RuntimeError("whisper.cpp completed without producing JSON output")
        try:
            payload = json.loads(output_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise RuntimeError("Could not read whisper.cpp JSON output") from error
        return transcript_from_whisper(
            payload, duration_ms, self.settings.uncertain_confidence_threshold
        )


class FasterWhisperService:
    def __init__(self, settings: Settings):
        self.settings = settings
        self._model: Any | None = None

    def transcribe(self, lecture_id: str, audio: Path, duration_ms: int) -> Transcript:
        del lecture_id
        model = self._load_model()
        segments, _info = model.transcribe(
            str(audio),
            beam_size=self.settings.faster_whisper_beam_size,
            language="en",
            vad_filter=self.settings.faster_whisper_vad_filter,
        )
        return transcript_from_faster_whisper(
            list(segments),
            duration_ms,
            self.settings.uncertain_confidence_threshold,
        )

    def _load_model(self) -> Any:
        if self._model is None:
            try:
                from faster_whisper import WhisperModel
            except ImportError as error:
                raise RuntimeError(
                    "Faster Whisper is not installed. Run: python -m pip install -r backend/requirements-faster-whisper.txt"
                ) from error
            model_ref = (
                str(self.settings.faster_whisper_model_path)
                if self.settings.faster_whisper_model_path
                else self.settings.faster_whisper_model_name
            )
            self._model = WhisperModel(
                model_ref,
                device="cuda",
                compute_type=self.settings.faster_whisper_compute_type,
            )
        return self._model


class TranscriptionService:
    def __init__(self, settings: Settings, processes: ProcessRegistry):
        self.settings = settings
        self.whisper_cpp = WhisperCppService(settings, processes)
        self.faster_whisper = FasterWhisperService(settings)

    def selected_backend(self) -> BackendName:
        configured = self.settings.transcription_backend
        if configured == "whisper_cpp":
            return "whisper_cpp"
        if configured == "faster_whisper":
            return "faster_whisper"
        faster_status = faster_whisper_readiness(self.settings)
        return "faster_whisper" if faster_status.ready else "whisper_cpp"

    def transcribe(self, lecture_id: str, audio: Path, duration_ms: int) -> Transcript:
        backend = self.selected_backend()
        if backend == "faster_whisper":
            return self.faster_whisper.transcribe(lecture_id, audio, duration_ms)
        return self.whisper_cpp.transcribe(lecture_id, audio, duration_ms)


class Readiness:
    def __init__(self, ready: bool, detail: str):
        self.ready = ready
        self.detail = detail


def whisper_cpp_readiness(settings: Settings) -> Readiness:
    missing: list[str] = []
    if not settings.executable_available(settings.whisper_cli_path):
        missing.append(
            f"whisper.cpp CLI missing at {settings.whisper_cli_path}. Build whisper.cpp, or set WHISPER_CLI_PATH in .env."
        )
    if not settings.whisper_model_path.is_file():
        missing.append(
            f"Whisper model missing at {settings.whisper_model_path}. Place ggml-base.en.bin there, or set WHISPER_MODEL_PATH in .env."
        )
    if missing:
        return Readiness(False, " ".join(missing))
    return Readiness(True, f"using {settings.whisper_cli_path} with {settings.whisper_model_path}")


def faster_whisper_readiness(settings: Settings) -> Readiness:
    try:
        import faster_whisper  # noqa: F401
    except ImportError:
        return Readiness(
            False,
            "Faster Whisper package missing. Run: python -m pip install -r backend/requirements-faster-whisper.txt",
        )

    try:
        import ctranslate2
    except ImportError:
        return Readiness(
            False,
            "CTranslate2 package missing. Run: python -m pip install -r backend/requirements-faster-whisper.txt",
        )

    cuda_count = getattr(ctranslate2, "get_cuda_device_count", None)
    if callable(cuda_count):
        try:
            if int(cuda_count()) < 1:
                return Readiness(
                    False,
                    "No CUDA device detected. Install NVIDIA drivers/CUDA runtime, or use TRANSCRIPTION_BACKEND=whisper_cpp.",
                )
        except Exception as error:
            return Readiness(
                False,
                f"CUDA readiness check failed: {error}. Install NVIDIA CUDA cuBLAS/cuDNN runtime libraries.",
            )

    if settings.faster_whisper_model_path:
        if not settings.faster_whisper_model_path.is_dir():
            return Readiness(
                False,
                f"Faster Whisper model path missing: {settings.faster_whisper_model_path}. Set FASTER_WHISPER_MODEL_PATH, or run: python -m backend.app.tools.prepare_faster_whisper",
            )
        return Readiness(True, f"using local model at {settings.faster_whisper_model_path}")

    if not _cached_faster_whisper_model_exists(settings.faster_whisper_model_name):
        return Readiness(
            False,
            f"Faster Whisper model '{settings.faster_whisper_model_name}' is not prepared locally. Run while online: python -m backend.app.tools.prepare_faster_whisper",
        )
    return Readiness(True, f"using prepared model {settings.faster_whisper_model_name}")


def transcript_from_faster_whisper(
    raw_segments: list[Any], duration_ms: int, threshold: float
) -> Transcript:
    segments: list[TranscriptSegment] = []
    for raw in raw_segments:
        text = str(getattr(raw, "text", "")).strip()
        if not text:
            continue
        confidence = _faster_whisper_confidence(raw)
        start_ms = max(0, round(float(getattr(raw, "start", 0.0)) * 1000))
        end_ms = max(start_ms, round(float(getattr(raw, "end", 0.0)) * 1000))
        segments.append(
            TranscriptSegment(
                id=f"seg-{len(segments) + 1:04d}",
                start_ms=start_ms,
                end_ms=end_ms,
                text=text,
                confidence=round(confidence, 4),
                uncertain=confidence < threshold,
            )
        )
    if not segments:
        raise ValueError("Faster Whisper returned no transcript segments")
    return Transcript(language="en", duration_ms=duration_ms, segments=segments)


def transcript_from_whisper(
    payload: dict, duration_ms: int, threshold: float
) -> Transcript:
    raw_segments = payload.get("transcription") or payload.get("segments") or []
    segments: list[TranscriptSegment] = []
    for index, raw in enumerate(raw_segments, start=1):
        offsets = raw.get("offsets", {})
        start_ms = _offset_ms(offsets.get("from", raw.get("start", 0)))
        end_ms = _offset_ms(offsets.get("to", raw.get("end", start_ms)))
        probabilities = [
            float(token["p"])
            for token in raw.get("tokens", [])
            if isinstance(token, dict)
            and isinstance(token.get("p"), (int, float))
            and not str(token.get("text", "")).startswith("[")
        ]
        confidence = sum(probabilities) / len(probabilities) if probabilities else 0.5
        confidence = max(0.0, min(1.0, confidence))
        text = str(raw.get("text", "")).strip()
        if not text:
            continue
        segments.append(
            TranscriptSegment(
                id=f"seg-{len(segments) + 1:04d}",
                start_ms=start_ms,
                end_ms=max(start_ms, end_ms),
                text=text,
                confidence=round(confidence, 4),
                uncertain=confidence < threshold,
            )
        )
    if not segments:
        raise ValueError("whisper.cpp returned no transcript segments")
    return Transcript(language="en", duration_ms=duration_ms, segments=segments)


def _offset_ms(value: object) -> int:
    if isinstance(value, float):
        return max(0, round(value * 1000))
    if isinstance(value, int):
        return max(0, value)
    try:
        return max(0, int(float(str(value))))
    except ValueError:
        return 0


def _faster_whisper_confidence(segment: Any) -> float:
    words = getattr(segment, "words", None) or []
    probabilities = [
        float(getattr(word, "probability"))
        for word in words
        if isinstance(getattr(word, "probability", None), (int, float))
    ]
    if probabilities:
        confidence = sum(probabilities) / len(probabilities)
    else:
        avg_logprob = getattr(segment, "avg_logprob", None)
        if isinstance(avg_logprob, (int, float)):
            confidence = math.exp(float(avg_logprob))
        else:
            confidence = 0.5
    return max(0.0, min(1.0, confidence))


def _cached_faster_whisper_model_exists(model_name: str) -> bool:
    try:
        from huggingface_hub import try_to_load_from_cache
    except ImportError:
        return False
    candidates = [
        f"Systran/faster-whisper-{model_name}",
        f"openai/whisper-{model_name}",
        model_name,
    ]
    for repo_id in candidates:
        for filename in ("config.json", "model.bin"):
            try:
                cached = try_to_load_from_cache(repo_id, filename)
            except Exception:
                cached = None
            if cached:
                return True
    return False


WhisperService = WhisperCppService
