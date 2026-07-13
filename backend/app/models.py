from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field, field_validator


class LectureStatus(StrEnum):
    QUEUED = "queued"
    NORMALIZING = "normalizing"
    TRANSCRIBING = "transcribing"
    GENERATING = "generating"
    COMPLETED = "completed"
    FAILED = "failed"
    DELETING = "deleting"


class TranscriptSegment(BaseModel):
    id: str
    start_ms: int = Field(ge=0)
    end_ms: int = Field(ge=0)
    text: str
    confidence: float = Field(ge=0, le=1)
    uncertain: bool


class Transcript(BaseModel):
    language: str = "en"
    duration_ms: int = Field(ge=0)
    segments: list[TranscriptSegment]


class Note(BaseModel):
    title: str
    body: str
    segment_ids: list[str] = Field(min_length=1)


class Concept(BaseModel):
    name: str
    definition: str
    segment_ids: list[str] = Field(min_length=1)


class Flashcard(BaseModel):
    front: str
    back: str
    segment_ids: list[str] = Field(min_length=1)


class QuizQuestion(BaseModel):
    question: str
    options: list[str] = Field(min_length=2, max_length=6)
    correct_answer: int = Field(ge=0)
    explanation: str
    segment_ids: list[str] = Field(min_length=1)

    @field_validator("correct_answer")
    @classmethod
    def answer_must_exist(cls, value: int, info):
        options = info.data.get("options", [])
        if options and value >= len(options):
            raise ValueError("correct_answer must index an option")
        return value


class StudyPack(BaseModel):
    title: str
    overview: str
    notes: list[Note] = Field(min_length=1)
    concepts: list[Concept] = Field(min_length=1)
    flashcards: list[Flashcard] = Field(min_length=1)
    quiz: list[QuizQuestion] = Field(min_length=1)

    def validate_evidence(self, transcript: Transcript) -> "StudyPack":
        valid = {segment.id for segment in transcript.segments}
        cited: list[str] = []
        for collection in (self.notes, self.concepts, self.flashcards, self.quiz):
            for item in collection:
                cited.extend(item.segment_ids)
        invalid = sorted(set(cited) - valid)
        if invalid:
            raise ValueError(f"Unknown transcript segment IDs: {', '.join(invalid)}")
        return self


class LectureSummary(BaseModel):
    id: str
    original_filename: str
    status: LectureStatus
    created_at: datetime
    updated_at: datetime
    error: str | None = None


class LectureDetail(LectureSummary):
    transcript: Transcript | None = None
    study_pack: StudyPack | None = None


class HealthComponent(BaseModel):
    ready: bool
    detail: str


class HealthResponse(BaseModel):
    ready: bool
    components: dict[str, HealthComponent]
