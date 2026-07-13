# Contributing to PocketTA Local

PocketTA welcomes focused changes that preserve offline operation, evidence traceability, and safe local deletion.

## Development

1. Follow `README.md` and copy `.env.example` to `.env`.
2. Keep models, recordings, databases, exports, and secrets out of Git.
3. Add tests for changed behavior and failure modes.
4. Run:

```bash
.venv/bin/python -m pytest
cd frontend && npm test && npm run build
```

Pull requests should describe user-visible behavior, privacy/network impact, test evidence, and new dependency/model licences. Never submit classroom recordings without explicit consent and redistribution rights. New HTTP destinations, telemetry, downloads, or non-loopback bind addresses require design review.
