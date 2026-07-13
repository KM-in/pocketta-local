# PocketTA Local architecture

## Data flow

```text
React/Vite on 127.0.0.1:5173
        | REST upload and polling
FastAPI on 127.0.0.1:8000
        +-- SQLite metadata and structured results
        +-- single in-process lecture queue
        +-- FFprobe/FFmpeg -> 16 kHz mono PCM WAV
        +-- whisper.cpp -> timestamped transcript JSON
        +-- LM Studio on 127.0.0.1:1234 -> validated study pack JSON
        +-- Markdown export and permanent deletion
```

Uploads live below generated UUID directories; user filenames are display metadata only. Normalization, transcription, and generation run sequentially, with one heavy lecture job at a time.

## Trust and validation boundaries

- Upload byte limits are enforced while streaming; FFprobe authoritatively checks media duration.
- Native commands receive argument arrays, never shell strings.
- PocketTA creates stable Whisper segment IDs.
- Low-confidence segments remain visible but are excluded from generation.
- Pydantic validates model output; cited IDs must exist and cannot be uncertain.
- LM Studio must use loopback, and its HTTP client ignores proxy environment variables.
- Deletion terminates owned native work, removes the UUID directory, and deletes SQLite state.

## Persistence and limitations

SQLite stores statuses and JSON results. Completed/failed lectures survive restarts; interrupted jobs return to the queue. The frontend polls every 1.5 seconds while work is active.

The queue is designed for one local user. Generation uses one prompt because P0 caps recordings at 15 minutes. Progress is stage-level, and cancellation is exposed through permanent deletion rather than a separate retry/cancel API.
