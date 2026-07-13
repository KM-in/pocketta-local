from __future__ import annotations

import json

import httpx
from pydantic import ValidationError

from ..config import Settings
from ..models import StudyPack, Transcript


class LMStudioError(RuntimeError):
    pass


class LMStudioService:
    def __init__(self, settings: Settings):
        self.settings = settings

    @property
    def headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.settings.lm_studio_api_key:
            headers["Authorization"] = f"Bearer {self.settings.lm_studio_api_key}"
        return headers

    async def available_models(self) -> list[str]:
        async with httpx.AsyncClient(timeout=5, trust_env=False) as client:
            response = await client.get(
                f"{self.settings.lm_studio_base_url.rstrip('/')}/models",
                headers=self.headers,
            )
            response.raise_for_status()
        return [str(item["id"]) for item in response.json().get("data", []) if item.get("id")]

    async def generate(self, transcript: Transcript) -> StudyPack:
        if not self.settings.lm_studio_model_id:
            raise LMStudioError("LM_STUDIO_MODEL_ID is not configured")
        prompt = _transcript_prompt(transcript)
        error_context = ""
        for attempt in range(2):
            messages = [
                {
                    "role": "system",
                    "content": (
                        "You create concise English study packs using only the supplied "
                        "transcript. Every item must cite one or more exact segment IDs. "
                        "Never invent a segment ID or unsupported fact."
                    ),
                },
                {
                    "role": "user",
                    "content": prompt + error_context,
                },
            ]
            payload = {
                "model": self.settings.lm_studio_model_id,
                "messages": messages,
                "temperature": 0.2,
                "max_tokens": 4096,
                "stream": False,
                "response_format": {
                    "type": "json_schema",
                    "json_schema": {
                        "name": "pocketta_study_pack",
                        "strict": True,
                        "schema": StudyPack.model_json_schema(),
                    },
                },
            }
            try:
                raw = await self._complete(payload)
                pack = StudyPack.model_validate_json(raw)
                return pack.validate_evidence(transcript)
            except (ValidationError, ValueError, json.JSONDecodeError) as error:
                if attempt == 1:
                    raise LMStudioError(f"Invalid structured study pack: {error}") from error
                error_context = (
                    "\n\nYour previous response failed validation. Return a corrected study pack "
                    f"that strictly follows the schema. Validation error: {error}"
                )
        raise LMStudioError("LM Studio generation failed")

    async def _complete(self, payload: dict) -> str:
        try:
            async with httpx.AsyncClient(
                timeout=self.settings.lm_studio_timeout_seconds, trust_env=False
            ) as client:
                response = await client.post(
                    f"{self.settings.lm_studio_base_url.rstrip('/')}/chat/completions",
                    headers=self.headers,
                    json=payload,
                )
                response.raise_for_status()
            return _extract_content(response.json())
        except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError) as error:
            raise LMStudioError(f"LM Studio request failed: {error}") from error


def _transcript_prompt(transcript: Transcript) -> str:
    lines = [
        f"{segment.id} [{_timestamp(segment.start_ms)}-{_timestamp(segment.end_ms)}] "
        f"{segment.text}"
        for segment in transcript.segments
    ]
    return (
        "Create notes, key concepts, flashcards, and multiple-choice quiz questions "
        "from this lecture transcript. Cite evidence using segment_ids.\n\n"
        + "\n".join(lines)
    )


def _extract_content(payload: dict) -> str:
    message = payload["choices"][0]["message"]
    content = message.get("content") or message.get("reasoning_content")
    if not isinstance(content, str) or not content.strip():
        raise ValueError("LM Studio returned no structured response content")
    return content.strip()


def _timestamp(milliseconds: int) -> str:
    total_seconds = milliseconds // 1000
    return f"{total_seconds // 60:02d}:{total_seconds % 60:02d}"
