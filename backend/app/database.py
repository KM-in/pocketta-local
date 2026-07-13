from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from .models import LectureDetail, LectureStatus, LectureSummary, StudyPack, Transcript


class Database:
    def __init__(self, path: Path):
        self.path = path

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=30)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def initialize(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.execute("PRAGMA journal_mode = WAL")
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS lectures (
                    id TEXT PRIMARY KEY,
                    original_filename TEXT NOT NULL,
                    source_path TEXT NOT NULL,
                    status TEXT NOT NULL,
                    transcript_json TEXT,
                    study_pack_json TEXT,
                    error TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )

    def create_lecture(self, lecture_id: str, filename: str, source_path: Path) -> None:
        now = datetime.now(UTC).isoformat()
        with self._connect() as connection:
            connection.execute(
                """INSERT INTO lectures
                (id, original_filename, source_path, status, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)""",
                (lecture_id, filename, str(source_path), LectureStatus.QUEUED, now, now),
            )

    def update_status(
        self, lecture_id: str, status: LectureStatus, error: str | None = None
    ) -> bool:
        with self._connect() as connection:
            cursor = connection.execute(
                "UPDATE lectures SET status = ?, error = ?, updated_at = ? WHERE id = ?",
                (status, error, datetime.now(UTC).isoformat(), lecture_id),
            )
            return cursor.rowcount > 0

    def save_transcript(self, lecture_id: str, transcript: Transcript) -> None:
        with self._connect() as connection:
            connection.execute(
                "UPDATE lectures SET transcript_json = ?, updated_at = ? WHERE id = ?",
                (transcript.model_dump_json(), datetime.now(UTC).isoformat(), lecture_id),
            )

    def save_study_pack(self, lecture_id: str, study_pack: StudyPack) -> None:
        with self._connect() as connection:
            connection.execute(
                "UPDATE lectures SET study_pack_json = ?, updated_at = ? WHERE id = ?",
                (study_pack.model_dump_json(), datetime.now(UTC).isoformat(), lecture_id),
            )

    def get_source_path(self, lecture_id: str) -> Path | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT source_path FROM lectures WHERE id = ?", (lecture_id,)
            ).fetchone()
        return Path(row["source_path"]) if row else None

    def exists(self, lecture_id: str) -> bool:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT 1 FROM lectures WHERE id = ?", (lecture_id,)
            ).fetchone()
        return row is not None

    def list_lectures(self) -> list[LectureSummary]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM lectures ORDER BY created_at DESC"
            ).fetchall()
        return [self._summary(row) for row in rows]

    def get_lecture(self, lecture_id: str) -> LectureDetail | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM lectures WHERE id = ?", (lecture_id,)
            ).fetchone()
        if not row:
            return None
        return LectureDetail(
            **self._summary(row).model_dump(),
            transcript=Transcript.model_validate_json(row["transcript_json"])
            if row["transcript_json"]
            else None,
            study_pack=StudyPack.model_validate_json(row["study_pack_json"])
            if row["study_pack_json"]
            else None,
        )

    def recover_incomplete(self) -> list[str]:
        active = (
            LectureStatus.QUEUED,
            LectureStatus.NORMALIZING,
            LectureStatus.TRANSCRIBING,
            LectureStatus.GENERATING,
        )
        placeholders = ",".join("?" for _ in active)
        with self._connect() as connection:
            rows = connection.execute(
                f"SELECT id FROM lectures WHERE status IN ({placeholders})", active
            ).fetchall()
            ids = [row["id"] for row in rows]
            if ids:
                connection.executemany(
                    "UPDATE lectures SET status = ?, error = NULL, updated_at = ? WHERE id = ?",
                    [
                        (LectureStatus.QUEUED, datetime.now(UTC).isoformat(), lecture_id)
                        for lecture_id in ids
                    ],
                )
        return ids

    def delete(self, lecture_id: str) -> bool:
        with self._connect() as connection:
            cursor = connection.execute("DELETE FROM lectures WHERE id = ?", (lecture_id,))
            return cursor.rowcount > 0

    @staticmethod
    def _summary(row: sqlite3.Row) -> LectureSummary:
        return LectureSummary(
            id=row["id"],
            original_filename=row["original_filename"],
            status=row["status"],
            error=row["error"],
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )
