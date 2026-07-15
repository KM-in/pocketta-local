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
        +-- long transcript map/reduce -> evidence-linked chunk summaries
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

SQLite stores statuses, progress, metrics, and JSON results. Additive startup migrations preserve earlier hackathon databases. Completed/failed lectures survive restarts; interrupted jobs return to the queue and reuse a saved transcript when available. The frontend polls every 1.5 seconds while work is active.

The queue is designed for one local user. Short transcripts use one schema-constrained request; longer inputs are divided on segment boundaries, summarized with evidence IDs, and reduced into the final study pack. Progress is stage-level. Cancellation retains completed intermediate results, transcript edits invalidate stale generated material, and generation can be retried independently.

Normalized audio and Whisper scratch JSON are removed after successful transcription. The original recording remains until explicit deletion, and startup cleanup removes abandoned temporary files older than 24 hours.
