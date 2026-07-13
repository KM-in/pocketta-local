from backend.app.services.whisper import transcript_from_whisper


def test_whisper_segments_get_stable_ids_and_uncertainty() -> None:
    result = transcript_from_whisper(
        {
            "transcription": [
                {
                    "offsets": {"from": 0, "to": 800},
                    "text": "Clear segment",
                    "tokens": [{"text": "Clear", "p": 0.9}],
                },
                {
                    "offsets": {"from": 800, "to": 1400},
                    "text": "Unclear segment",
                    "tokens": [{"text": "Unclear", "p": 0.3}],
                },
            ]
        },
        duration_ms=1400,
        threshold=0.6,
    )
    assert [segment.id for segment in result.segments] == ["seg-0001", "seg-0002"]
    assert result.segments[0].uncertain is False
    assert result.segments[1].uncertain is True
