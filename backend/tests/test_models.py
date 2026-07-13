import pytest
from pydantic import ValidationError

from backend.app.config import Settings
from backend.app.models import (
    Concept,
    Flashcard,
    Note,
    QuizQuestion,
    StudyPack,
    Transcript,
    TranscriptSegment,
)


def transcript() -> Transcript:
    return Transcript(
        duration_ms=1000,
        segments=[
            TranscriptSegment(
                id="seg-0001",
                start_ms=0,
                end_ms=1000,
                text="Local evidence",
                confidence=0.9,
                uncertain=False,
            )
        ],
    )


def study_pack(segment_id: str = "seg-0001") -> StudyPack:
    evidence = [segment_id]
    return StudyPack(
        title="Test lecture",
        overview="Overview",
        notes=[Note(title="Note", body="Body", segment_ids=evidence)],
        concepts=[Concept(name="Concept", definition="Definition", segment_ids=evidence)],
        flashcards=[Flashcard(front="Front", back="Back", segment_ids=evidence)],
        quiz=[
            QuizQuestion(
                question="Question?",
                options=["Right", "Wrong"],
                correct_answer=0,
                explanation="Because.",
                segment_ids=evidence,
            )
        ],
    )


def test_evidence_must_resolve_to_transcript() -> None:
    assert study_pack().validate_evidence(transcript()).title == "Test lecture"
    with pytest.raises(ValueError, match="seg-9999"):
        study_pack("seg-9999").validate_evidence(transcript())


def test_quiz_answer_must_index_an_option() -> None:
    with pytest.raises(ValueError, match="correct_answer"):
        QuizQuestion(
            question="Question?",
            options=["Only", "Other"],
            correct_answer=2,
            explanation="No.",
            segment_ids=["seg-0001"],
        )


def test_lm_studio_url_must_remain_on_loopback() -> None:
    with pytest.raises(ValidationError, match="loopback"):
        Settings(lm_studio_base_url="https://example.com/v1")
