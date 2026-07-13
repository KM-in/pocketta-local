# Backend

The FastAPI backend provides SQLite persistence, a single heavy-work queue, FFmpeg and whisper.cpp subprocess adapters, LM Studio structured generation, Markdown export, and permanent local deletion.

Always invoke Python through the repository `.venv`. Run the development server from the repository root:

```bash
.venv/bin/python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
```

API documentation is available locally at `http://127.0.0.1:8000/docs`.
