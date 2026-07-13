from __future__ import annotations

import asyncio
import shutil
from pathlib import Path

from ..config import Settings
from ..database import Database
from ..models import LectureStatus
from .lm_studio import LMStudioService
from .media import MediaService
from .processes import ProcessRegistry
from .whisper import TranscriptionService


class LectureCancelled(RuntimeError):
    pass


class LectureProcessor:
    def __init__(self, settings: Settings, database: Database):
        self.settings = settings
        self.database = database
        self.queue: asyncio.Queue[str] = asyncio.Queue()
        self.processes = ProcessRegistry()
        self.media = MediaService(settings, self.processes)
        self.transcription = TranscriptionService(settings, self.processes)
        self.lm_studio = LMStudioService(settings)
        self.cancelled: set[str] = set()
        self.active_tasks: dict[str, asyncio.Task] = {}
        self.worker_task: asyncio.Task | None = None

    async def start(self) -> None:
        for lecture_id in self.database.recover_incomplete():
            self.queue.put_nowait(lecture_id)
        self.worker_task = asyncio.create_task(self._worker(), name="pocketta-worker")

    async def stop(self) -> None:
        for lecture_id, task in list(self.active_tasks.items()):
            self.cancelled.add(lecture_id)
            await asyncio.to_thread(self.processes.terminate, lecture_id)
            task.cancel()
        if self.worker_task:
            self.worker_task.cancel()
            try:
                await self.worker_task
            except asyncio.CancelledError:
                pass

    def enqueue(self, lecture_id: str) -> None:
        self.queue.put_nowait(lecture_id)

    async def delete(self, lecture_id: str) -> bool:
        if not self.database.exists(lecture_id):
            return False
        self.cancelled.add(lecture_id)
        self.database.update_status(lecture_id, LectureStatus.DELETING)
        active_task = self.active_tasks.get(lecture_id)
        if active_task:
            active_task.cancel()
        await asyncio.to_thread(self.processes.terminate, lecture_id)
        lecture_dir = self.settings.lectures_dir / lecture_id
        await asyncio.to_thread(shutil.rmtree, lecture_dir, True)
        deleted = self.database.delete(lecture_id)
        return deleted

    async def _worker(self) -> None:
        while True:
            lecture_id = await self.queue.get()
            try:
                job_task = asyncio.create_task(self._process(lecture_id))
                self.active_tasks[lecture_id] = job_task
                await job_task
            except LectureCancelled:
                pass
            except asyncio.CancelledError:
                if asyncio.current_task() and asyncio.current_task().cancelling():
                    raise
            except Exception as error:
                if self.database.exists(lecture_id):
                    self.database.update_status(
                        lecture_id, LectureStatus.FAILED, _safe_error(error)
                    )
            finally:
                self.active_tasks.pop(lecture_id, None)
                self.cancelled.discard(lecture_id)
                self.queue.task_done()

    async def _process(self, lecture_id: str) -> None:
        source = self.database.get_source_path(lecture_id)
        if not source:
            raise LectureCancelled()
        lecture_dir = self.settings.lectures_dir / lecture_id
        normalized = lecture_dir / "audio.wav"

        self._check(lecture_id)
        self.database.update_status(lecture_id, LectureStatus.NORMALIZING)
        duration_ms = await asyncio.to_thread(
            self.media.normalize, lecture_id, source, normalized
        )

        self._check(lecture_id)
        self.database.update_status(lecture_id, LectureStatus.TRANSCRIBING)
        transcript = await asyncio.to_thread(
            self.transcription.transcribe, lecture_id, normalized, duration_ms
        )
        self._check(lecture_id)
        self.database.save_transcript(lecture_id, transcript)
        (lecture_dir / "transcript.json").write_text(
            transcript.model_dump_json(indent=2), encoding="utf-8"
        )

        self.database.update_status(lecture_id, LectureStatus.GENERATING)
        study_pack = await self.lm_studio.generate(transcript)
        self._check(lecture_id)
        self.database.save_study_pack(lecture_id, study_pack)
        (lecture_dir / "study_pack.json").write_text(
            study_pack.model_dump_json(indent=2), encoding="utf-8"
        )
        self.database.update_status(lecture_id, LectureStatus.COMPLETED)

    def _check(self, lecture_id: str) -> None:
        if lecture_id in self.cancelled or not self.database.exists(lecture_id):
            raise LectureCancelled()


def _safe_error(error: Exception) -> str:
    text = str(error).strip() or error.__class__.__name__
    return text[-2000:]
