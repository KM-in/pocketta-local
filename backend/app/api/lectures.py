from __future__ import annotations

import shutil
import uuid
from pathlib import Path

import httpx
from fastapi import APIRouter, File, HTTPException, Request, UploadFile, status
from fastapi.responses import PlainTextResponse

from ..models import HealthComponent, HealthResponse, LectureDetail, LectureSummary
from ..services.exporter import render_markdown
from ..services.media import SUPPORTED_EXTENSIONS


router = APIRouter(prefix="/api")


@router.get("/health", response_model=HealthResponse)
async def health(request: Request) -> HealthResponse:
    settings = request.app.state.settings
    processor = request.app.state.processor
    components = {
        "database": HealthComponent(
            ready=settings.database_path.is_file(),
            detail=str(settings.database_path.resolve()),
        ),
        "storage": HealthComponent(
            ready=settings.pocketta_data_dir.is_dir(),
            detail=str(settings.pocketta_data_dir.resolve()),
        ),
        "ffmpeg": HealthComponent(
            ready=settings.executable_available(settings.ffmpeg_path),
            detail=settings.ffmpeg_path,
        ),
        "ffprobe": HealthComponent(
            ready=settings.executable_available(settings.ffprobe_path),
            detail=settings.ffprobe_path,
        ),
        "whisper_cli": HealthComponent(
            ready=settings.executable_available(settings.whisper_cli_path),
            detail=str(settings.whisper_cli_path),
        ),
        "whisper_model": HealthComponent(
            ready=settings.whisper_model_path.is_file(),
            detail=str(settings.whisper_model_path),
        ),
    }
    try:
        models = await processor.lm_studio.available_models()
        configured = settings.lm_studio_model_id
        components["lm_studio"] = HealthComponent(
            ready=bool(configured and configured in models),
            detail=(
                f"model {configured} is available"
                if configured and configured in models
                else f"configure LM_STUDIO_MODEL_ID; available: {', '.join(models) or 'none'}"
            ),
        )
    except (httpx.HTTPError, KeyError, TypeError, ValueError) as error:
        components["lm_studio"] = HealthComponent(
            ready=False,
            detail=f"Local server unavailable: {error}",
        )
    return HealthResponse(
        ready=all(component.ready for component in components.values()),
        components=components,
    )


@router.post(
    "/lectures", response_model=LectureSummary, status_code=status.HTTP_202_ACCEPTED
)
async def upload_lecture(request: Request, file: UploadFile = File(...)) -> LectureSummary:
    settings = request.app.state.settings
    database = request.app.state.database
    processor = request.app.state.processor
    filename = Path(file.filename or "recording").name
    suffix = Path(filename).suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported media type. Allowed: {', '.join(sorted(SUPPORTED_EXTENSIONS))}",
        )
    lecture_id = str(uuid.uuid4())
    lecture_dir = settings.lectures_dir / lecture_id
    lecture_dir.mkdir(parents=True, exist_ok=False)
    source_path = lecture_dir / f"source{suffix}"
    max_bytes = settings.max_upload_mb * 1024 * 1024
    written = 0
    try:
        with source_path.open("wb") as output:
            while chunk := await file.read(1024 * 1024):
                written += len(chunk)
                if written > max_bytes:
                    raise HTTPException(
                        status_code=413,
                        detail=f"Upload exceeds the {settings.max_upload_mb} MB limit",
                    )
                output.write(chunk)
        if written == 0:
            raise HTTPException(status_code=400, detail="The uploaded file is empty")
        database.create_lecture(lecture_id, filename, source_path)
        processor.enqueue(lecture_id)
        lecture = database.get_lecture(lecture_id)
        assert lecture is not None
        return LectureSummary(**lecture.model_dump(exclude={"transcript", "study_pack"}))
    except Exception:
        if not database.exists(lecture_id):
            shutil.rmtree(lecture_dir, ignore_errors=True)
        raise
    finally:
        await file.close()


@router.get("/lectures", response_model=list[LectureSummary])
def list_lectures(request: Request) -> list[LectureSummary]:
    return request.app.state.database.list_lectures()


@router.get("/lectures/{lecture_id}", response_model=LectureDetail)
def get_lecture(request: Request, lecture_id: str) -> LectureDetail:
    lecture = request.app.state.database.get_lecture(lecture_id)
    if not lecture:
        raise HTTPException(status_code=404, detail="Lecture not found")
    return lecture


@router.get("/lectures/{lecture_id}/export.md", response_class=PlainTextResponse)
def export_lecture(request: Request, lecture_id: str) -> PlainTextResponse:
    lecture = request.app.state.database.get_lecture(lecture_id)
    if not lecture:
        raise HTTPException(status_code=404, detail="Lecture not found")
    try:
        content = render_markdown(lecture)
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    return PlainTextResponse(
        content,
        media_type="text/markdown; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="pocketta-{lecture_id}.md"'
        },
    )


@router.delete("/lectures/{lecture_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_lecture(request: Request, lecture_id: str) -> None:
    if not await request.app.state.processor.delete(lecture_id):
        raise HTTPException(status_code=404, detail="Lecture not found")
