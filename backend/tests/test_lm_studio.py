from unittest.mock import AsyncMock

import pytest

from backend.app.config import Settings
from backend.app.models import Transcript, TranscriptSegment
from backend.app.services.lm_studio import (
    ChunkSummary,
    LMStudioError,
    LMStudioService,
    _chunk_segments,
    _extract_content,
    _extract_json_object,
    _source_supports_full_pack,
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


def test_balanced_json_is_extracted_from_fences_and_commentary() -> None:
    assert _extract_json_object('```json\n{"value":"}"}\n``` trailing') == '{"value":"}"}'


@pytest.mark.asyncio
async def test_long_transcript_is_chunked_before_final_generation() -> None:
    segments = [
        TranscriptSegment(
            id=f"seg-{index:04d}",
            start_ms=index * 1000,
            end_ms=(index + 1) * 1000,
            text=f"Concept {index} " + "evidence " * 180,
            confidence=0.9,
            uncertain=False,
        )
        for index in range(1, 6)
    ]
    source = Transcript(duration_ms=6000, segments=segments)
    settings = Settings(
        lm_studio_model_id="local-qwen",
        lm_studio_chunk_chars=2000,
        lm_studio_chunk_overlap_segments=0,
    )
    chunks = _chunk_segments(segments, max_chars=2000, overlap=0)
    summaries = [
        ChunkSummary(points=[{"point": "Grounded point", "segment_ids": [chunk[0].id]}]).model_dump_json()
        for chunk in chunks
    ]
    service = LMStudioService(settings)
    service._complete = AsyncMock(side_effect=[*summaries, study_pack().model_dump_json()])
    result = await service.generate(source)
    assert result.title == "Test lecture"
    assert service._complete.await_count == len(chunks) + 1
    final_prompt = service._complete.await_args_list[-1].args[0]["messages"][1]["content"]
    assert "CHUNK SUMMARIES" in final_prompt


@pytest.mark.asyncio
async def test_rich_source_enforces_demo_item_counts() -> None:
    segments = [
        TranscriptSegment(
            id=f"seg-{index:04d}",
            start_ms=index * 1000,
            end_ms=(index + 1) * 1000,
            text=(
                "A grounded lecture segment explains programming concepts, practical problem "
                "solving, examples, and careful implementation choices clearly."
            ),
            confidence=0.9,
            uncertain=False,
        )
        for index in range(1, 21)
    ]
    assert _source_supports_full_pack(segments)
    rich = study_pack().model_copy(deep=True)
    rich.concepts *= 3
    rich.flashcards *= 5
    rich.quiz *= 5
    service = LMStudioService(Settings(lm_studio_model_id="local-qwen"))
    service._complete = AsyncMock(
        side_effect=[study_pack().model_dump_json(), rich.model_dump_json()]
    )
    result = await service.generate(Transcript(duration_ms=20_000, segments=segments))
    assert len(result.concepts) == 3
    assert len(result.flashcards) == 5
    assert len(result.quiz) == 5
    assert service._complete.await_count == 2
