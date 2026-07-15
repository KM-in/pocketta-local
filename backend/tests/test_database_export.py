from pathlib import Path

from backend.app.database import Database
from backend.app.models import LectureStatus, ProcessingMetrics
from backend.app.services.exporter import render_markdown
from backend.tests.test_models import study_pack, transcript


def test_database_round_trip_and_markdown_evidence(tmp_path: Path) -> None:
    database = Database(tmp_path / "test.sqlite3")
    database.initialize()
    database.create_lecture("lecture-1", "safe.mp3", tmp_path / "source.mp3")
    database.save_transcript("lecture-1", transcript())
    database.save_study_pack("lecture-1", study_pack())
    database.update_status("lecture-1", LectureStatus.COMPLETED)

    lecture = database.get_lecture("lecture-1")
    assert lecture is not None
    output = render_markdown(lecture)
    assert "## Recording metadata" in output
    assert "**Source file:** safe.mp3" in output
    assert "**Duration:** 00:01" in output
    assert "## Summary" in output
    assert "## Uncertainty warnings" in output
    assert "[seg-0001](#seg-0001)" in output
    assert '<a id="seg-0001"></a>' in output
    assert database.delete("lecture-1") is True
    assert database.get_lecture("lecture-1") is None


def test_restart_recovers_queued_and_active_jobs(tmp_path: Path) -> None:
    database = Database(tmp_path / "test.sqlite3")
    database.initialize()
    database.create_lecture("queued", "one.mp3", tmp_path / "one.mp3")
    database.create_lecture("active", "two.mp3", tmp_path / "two.mp3")
    database.update_status("active", LectureStatus.TRANSCRIBING)
    assert set(database.recover_incomplete()) == {"queued", "active"}
    assert database.get_lecture("active").status == LectureStatus.QUEUED


def test_database_migrates_existing_lecture_rows(tmp_path: Path) -> None:
    import sqlite3

    path = tmp_path / "legacy.sqlite3"
    with sqlite3.connect(path) as connection:
        connection.execute(
            """CREATE TABLE lectures (
            id TEXT PRIMARY KEY, original_filename TEXT NOT NULL, source_path TEXT NOT NULL,
            status TEXT NOT NULL, transcript_json TEXT, study_pack_json TEXT, error TEXT,
            created_at TEXT NOT NULL, updated_at TEXT NOT NULL)"""
        )
        connection.execute(
            """INSERT INTO lectures VALUES
            ('legacy', 'old.mp3', '/tmp/old.mp3', 'completed', NULL, NULL, NULL,
             '2026-07-15T00:00:00+00:00', '2026-07-15T00:00:00+00:00')"""
        )
    database = Database(path)
    database.initialize()
    lecture = database.get_lecture("legacy")
    assert lecture is not None
    assert lecture.title == "old.mp3"
    assert lecture.progress == 0


def test_metrics_round_trip_and_markdown_escapes_filename(tmp_path: Path) -> None:
    database = Database(tmp_path / "test.sqlite3")
    database.initialize()
    database.create_lecture("metrics", "[unsafe]*.mp3", tmp_path / "source.mp3", "Title #1")
    database.save_metrics(
        "metrics",
        ProcessingMetrics(
            stage_seconds={"transcribing": 2.5},
            total_seconds=3.5,
            peak_system_memory_mb=2048,
        ),
    )
    database.save_transcript("metrics", transcript())
    database.save_study_pack("metrics", study_pack())
    lecture = database.get_lecture("metrics")
    assert lecture is not None
    assert lecture.metrics.stage_seconds == {"transcribing": 2.5}
    output = render_markdown(lecture)
    assert "# Title \\#1" in output
    assert "\\[unsafe\\]\\*.mp3" in output
