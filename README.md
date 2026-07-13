# PocketTA Local

PocketTA Local turns lecture recordings into private, offline transcripts and evidence-linked study material on a student's laptop. FastAPI, SQLite, whisper.cpp, LM Studio, and React all run locally; the app binds only to loopback addresses.

## What works

- Upload WAV, MP3, M4A, or MP4 recordings up to 15 minutes/200 MB.
- Normalize with FFmpeg and transcribe English locally with whisper.cpp.
- Mark low-confidence transcript segments and exclude them from confident generated evidence.
- Build notes, concepts, flashcards, and quizzes with Qwen 3.5 4B in LM Studio.
- Trace generated items to transcript segments, persist results, export Markdown, and permanently delete data.

The hackathon build intentionally omits recording, transcript editing, PDF, chat, diarisation, accounts, and cloud sync.

## Prerequisites

- Python 3.11
- Node.js 22 or newer
- FFmpeg and FFprobe on `PATH`
- A locally built whisper.cpp CLI and `ggml-base.en.bin`
- Optional for NVIDIA GPUs: Faster Whisper, CUDA cuBLAS/cuDNN runtime libraries, and a prepared `turbo` model
- LM Studio with the Qwen 3.5 4B model already downloaded

Normal app startup, health checks, and lecture processing never download a model. Prepare native tools and models while online, then use the complete workflow without Wi-Fi.

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

For NVIDIA CUDA transcription, install the optional Python dependency while online:

```bash
.venv/bin/python -m pip install -r backend/requirements-faster-whisper.txt
```

Install the NVIDIA CUDA libraries required by Faster Whisper for your OS, then prepare the default `turbo` model while online:

```bash
.venv/bin/python -m backend.app.tools.prepare_faster_whisper
```

With `TRANSCRIPTION_BACKEND=auto`, PocketTA uses Faster Whisper when CUDA and the prepared model are ready, and otherwise falls back to whisper.cpp.

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

PocketTA never starts, loads, or downloads models. Failed readiness rows include the local command or LM Studio action needed to fix them.

## Verify

```bash
.venv/bin/python -m pytest
cd frontend && npm test && npm run build
```

See [docs/README.md](docs/README.md) for native setup, cross-platform notes, and the offline acceptance checklist.

## Benchmark a prepared machine

With FastAPI and LM Studio running:

```bash
mkdir -p benchmark-results
.venv/bin/python scripts/benchmark.py pocketta_test_10min.mp4 \
  --json-out benchmark-results/ten-minute.json \
  --markdown-out benchmark-results/ten-minute.md
```

The runner records observed stages and total time, then verifies evidence, uncertainty handling, summary presence, and demo item counts. Its output is ignored by Git.

The hardened 10-minute run on the 8 GB reference machine completed in 390.2 seconds: 1.0s normalization, 23.8s transcription, and approximately 365s structured generation. It produced 188 transcript segments, 14 notes, 6 concepts, 6 flashcards, and 5 quiz questions; every cited ID resolved and the one uncertain segment was not cited. This run used localhost services, but Wi-Fi-off status was not independently captured and is not claimed.

## Privacy and limitations

PocketTA binds to loopback addresses, restricts the LM Studio URL to loopback, ignores proxy environment variables for model calls, and contains no analytics, CDN assets, cloud AI, accounts, or model downloader. Data remains under `POCKETTA_DATA_DIR` until deletion.

Initial installation requires internet. Local execution reduces disclosure risk but is not a formal security proof, and generated material can be incomplete or wrong. Inspect its cited evidence.

## Project documentation

- [Architecture](docs/ARCHITECTURE.md)
- [Operations and offline acceptance](docs/README.md)
- [Demo runbook](docs/DEMO.md)
- [Contributing](CONTRIBUTING.md)
- [Security](SECURITY.md)

## Model and runtime attribution

| Component | Role | Licence/source | Included here? |
|---|---|---|---|
| PocketTA Local | Application | [MIT](LICENSE) | Yes |
| whisper.cpp | Speech runtime | [MIT](https://github.com/ggml-org/whisper.cpp/blob/master/LICENSE) | No |
| Whisper `base.en` | Speech model | [OpenAI Whisper](https://github.com/openai/whisper) | No |
| Qwen 3.5 4B | Study-pack model | [Apache-2.0 model card](https://huggingface.co/Qwen/Qwen3.5-4B) | No |
| LM Studio | Local model server | [LM Studio terms](https://lmstudio.ai/terms) | No |

Dependencies retain their own licences. Models and runtime binaries must be installed separately.
