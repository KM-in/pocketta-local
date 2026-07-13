from unittest.mock import AsyncMock

import pytest

from backend.app.config import Settings
from backend.app.services.lm_studio import LMStudioService, _extract_content
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


def test_qwen_reasoning_content_is_supported() -> None:
    payload = {
        "choices": [
            {"message": {"content": "", "reasoning_content": '{"title":"local"}'}}
        ]
    }
    assert _extract_content(payload) == '{"title":"local"}'
