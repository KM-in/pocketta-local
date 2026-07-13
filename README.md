# PocketTA Local

PocketTA Local turns lecture recordings into private, offline transcripts and evidence-linked study material on a student's laptop. FastAPI, SQLite, whisper.cpp, LM Studio, and React all run locally; the app binds only to loopback addresses.

## Prerequisites

- Python 3.11
- Node.js 22 or newer
- FFmpeg and FFprobe on `PATH`
- A locally built whisper.cpp CLI and `ggml-base.en.bin`
- LM Studio with the Qwen 3.5 4B model already downloaded

The application never downloads a model. Prepare native tools and models while online, then use the complete workflow without Wi-Fi.

## Clean project setup

Python dependencies live only in `.venv`; JavaScript dependencies live only in `frontend/node_modules`. System packages and LM Studio models are never removed.

macOS/Linux:

```bash
./scripts/bootstrap.sh --clean
```

Windows PowerShell:

```powershell
./scripts/bootstrap.ps1 -Clean
```

Copy `.env.example` to `.env`. In LM Studio, load Qwen with a context length of at least 16K and start the local server on `127.0.0.1:1234`. Obtain the exact identifier from:

```bash
curl http://127.0.0.1:1234/v1/models
```

Set that value as `LM_STUDIO_MODEL_ID` in `.env`.

## Run

From the repository root, start the backend:

```bash
.venv/bin/python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

In another terminal, start the frontend:

```bash
cd frontend
npm run dev
```

Open `http://127.0.0.1:5173`. The readiness panel identifies any missing local prerequisite.

## Verify

```bash
.venv/bin/python -m pytest
cd frontend && npm test && npm run build
```

See [docs/README.md](docs/README.md) for native setup, cross-platform notes, and the offline acceptance checklist.
