# PocketTA Local Operations

## Native preparation

Install FFmpeg using the operating system package manager. Build whisper.cpp into `vendor/whisper.cpp`, then place `ggml-base.en.bin` in `vendor/whisper.cpp/models`. The configured paths can be overridden in `.env` and must point to prepared local files.

`WHISPER_USE_GPU=false` is the reliable default. Enable it only after a native smoke test succeeds on the target GPU; PocketTA otherwise uses whisper.cpp's CPU backend.

For NVIDIA CUDA systems, PocketTA can auto-prefer Faster Whisper. Install it while online with:

```bash
.venv/bin/python -m pip install -r backend/requirements-faster-whisper.txt
```

Install the NVIDIA CUDA cuBLAS/cuDNN runtime libraries required by Faster Whisper for the target OS. If `FASTER_WHISPER_MODEL_PATH` points at a local CTranslate2 model directory, PocketTA uses that directory. Otherwise, prepare the configured model name, default `turbo`, while online:

```bash
.venv/bin/python -m backend.app.tools.prepare_faster_whisper
```

`TRANSCRIPTION_BACKEND=auto` uses Faster Whisper only when its package, CUDA runtime, and local/prepared model are ready; otherwise it falls back to whisper.cpp. Use `TRANSCRIPTION_BACKEND=faster_whisper` to require CUDA transcription, or `TRANSCRIPTION_BACKEND=whisper_cpp` to force the original path.

Install LM Studio, download Qwen 3.5 4B while online, and load it manually with a context length of at least 16K. Start the local server in LM Studio's Developer tab on `127.0.0.1:1234`. PocketTA checks `/v1/models` but never starts the server, loads a model, or downloads one.

The prepared reference machine uses model identifier `qwen3.5-4b`, whisper.cpp commit `080bbbe85230f624f0b52127f1ae1218247989f9`, and `base.en` SHA-256 `b7518e435da610821f88090732a6c5c685e9194edf1214b9d36a0eb9dff2051b`.

Windows uses the `.exe` whisper CLI path in `.env`. All application subprocess calls use argument arrays and portable paths rather than shell syntax.

## Data and privacy

SQLite and lecture directories are stored below `POCKETTA_DATA_DIR`. Each UUID directory contains the original source, normalized audio, transcript, and study pack. `DELETE /api/lectures/{id}` cancels owned native work, deletes this directory, and removes its database row.

The application contains no CDN, telemetry, cloud client, account, model downloader, vector database, or chatbot.

## Offline acceptance checklist

1. While online, complete project setup, build whisper.cpp, download `base.en`, optionally prepare Faster Whisper CUDA, and prepare Qwen in LM Studio.
2. Start LM Studio, load Qwen, start FastAPI and Vite, and confirm `/api/health` reports every component ready.
3. Disable Wi-Fi.
4. Upload a consented English recording of less than 15 minutes and 200 MB.
5. Confirm the job reaches `completed`, uncertain transcript text is marked, and every generated item links to a real transcript segment. If using CUDA, confirm `/api/health` reports `selected=faster_whisper`.
6. Export Markdown and verify its evidence links target the transcript appendix.
7. Restart PocketTA and confirm the lecture persists.
8. Delete the lecture and verify both its UUID directory and SQLite row are gone.

Record OS, CPU, GPU, memory, selected transcription backend, whisper.cpp commit or Faster Whisper model, LM Studio version, recording duration, processing time, and peak memory for the hackathon demo.
