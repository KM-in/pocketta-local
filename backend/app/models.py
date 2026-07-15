from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field, field_validator


class LectureStatus(StrEnum):
    QUEUED = "queued"
    NORMALIZING = "normalizing"
    TRANSCRIBING = "transcribing"
    GENERATING = "generating"
    TRANSCRIBED = "transcribed"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
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

    def validate_evidence(
        self, transcript: Transcript, *, allow_uncertain: bool = False
    ) -> "StudyPack":
        valid = {segment.id for segment in transcript.segments}
        uncertain = {segment.id for segment in transcript.segments if segment.uncertain}
        cited: list[str] = []
        for collection in (self.notes, self.concepts, self.flashcards, self.quiz):
            for item in collection:
                cited.extend(item.segment_ids)
        invalid = sorted(set(cited) - valid)
        if invalid:
            raise ValueError(f"Unknown transcript segment IDs: {', '.join(invalid)}")
        uncertain_citations = sorted(set(cited) & uncertain)
        if uncertain_citations and not allow_uncertain:
            raise ValueError(
                "Uncertain transcript segments cannot support confident study material: "
                + ", ".join(uncertain_citations)
            )
        return self


class ProcessingMetrics(BaseModel):
    stage_seconds: dict[str, float] = Field(default_factory=dict)
    total_seconds: float = Field(default=0, ge=0)
    peak_system_memory_mb: float = Field(default=0, ge=0)


class SegmentCorrection(BaseModel):
    segment_id: str = Field(min_length=1)
    text: str = Field(min_length=1, max_length=10_000)

    @field_validator("segment_id", "text")
    @classmethod
    def strip_correction_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("must not be blank")
        return value


class LectureUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    corrections: list[SegmentCorrection] = Field(default_factory=list, max_length=500)

    @field_validator("title")
    @classmethod
    def strip_title(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("title must not be blank")
        return value


class LectureSummary(BaseModel):
    id: str
    title: str
    original_filename: str
    status: LectureStatus
    progress: int = Field(default=0, ge=0, le=100)
    message: str = ""
    metrics: ProcessingMetrics = Field(default_factory=ProcessingMetrics)
    created_at: datetime
    updated_at: datetime
    error: str | None = None


class LectureDetail(LectureSummary):
    transcript: Transcript | None = None
    study_pack: StudyPack | None = None


class HealthComponent(BaseModel):
    ready: bool
    detail: str
    remediation: str | None = None


class HealthResponse(BaseModel):
    ready: bool
    components: dict[str, HealthComponent]
