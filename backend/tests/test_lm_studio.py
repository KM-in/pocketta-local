from unittest.mock import AsyncMock

import pytest

from backend.app.config import Settings
from backend.app.models import Transcript, TranscriptSegment
from backend.app.services.lm_studio import (
    LMStudioError,
    LMStudioService,
    _extract_content,
)
from backend.tests.test_models import study_pack, transcript


@pytest.mark.asyncio
async def test_generation_validates_structured_response() -> None:
    service = LMStudioService(Settings(lm_studio_model_id="local-qwen"))
    service._complete = AsyncMock(return_value=study_pack().model_dump_json())
    result = await service.generate(transcript())
    assert result.title == "Test lecture"
    payload = service._complete.await_args.args[0]
    assert payload["model"] == "local-qwen"
    assert payload["response_format"]["type"] == "json_schema"


@pytest.mark.asyncio
async def test_generation_retries_invalid_citations() -> None:
    service = LMStudioService(Settings(lm_studio_model_id="local-qwen"))
    service._complete = AsyncMock(
        side_effect=[
            study_pack("seg-9999").model_dump_json(),
            study_pack().model_dump_json(),
        ]
    )
    result = await service.generate(transcript())
    assert result.title == "Test lecture"
    assert service._complete.await_count == 2


@pytest.mark.asyncio
async def test_generation_excludes_uncertain_segments_from_prompt() -> None:
    source = Transcript(
        duration_ms=2000,
        segments=[
            TranscriptSegment(
                id="seg-0001", start_ms=0, end_ms=1000, text="Reliable", confidence=0.9, uncertain=False
            ),
            TranscriptSegment(
                id="seg-0002", start_ms=1000, end_ms=2000, text="Unreliable", confidence=0.2, uncertain=True
            ),
        ],
    )
    service = LMStudioService(Settings(lm_studio_model_id="local-qwen"))
    service._complete = AsyncMock(return_value=study_pack().model_dump_json())
    await service.generate(source)
    prompt = service._complete.await_args.args[0]["messages"][1]["content"]
    assert "seg-0001" in prompt
    assert "seg-0002" not in prompt
    assert "5-10 flashcards" in prompt


@pytest.mark.asyncio
async def test_generation_stops_when_all_speech_is_uncertain() -> None:
    source = transcript()
    source.segments[0].uncertain = True
    service = LMStudioService(Settings(lm_studio_model_id="local-qwen"))
    with pytest.raises(LMStudioError, match="not enough reliable speech"):
        await service.generate(source)


def test_qwen_reasoning_content_is_supported() -> None:
    payload = {
        "choices": [
            {"message": {"content": "", "reasoning_content": '{"title":"local"}'}}
        ]
    }
    assert _extract_content(payload) == '{"title":"local"}'
