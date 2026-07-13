from __future__ import annotations

import json
from pathlib import Path

from ..config import Settings
from ..models import Transcript, TranscriptSegment
from .processes import ProcessRegistry


class WhisperService:
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
