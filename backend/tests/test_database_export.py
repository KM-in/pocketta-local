from pathlib import Path

from backend.app.database import Database
from backend.app.models import LectureStatus
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
