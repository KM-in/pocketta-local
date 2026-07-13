# Frontend

The React/Vite interface uses bundled assets and communicates only with the FastAPI backend on `127.0.0.1`. It supports upload, status polling, evidence-linked study material, uncertainty highlighting, Markdown export, and permanent deletion.

```bash
npm ci
npm run dev
```

Override `VITE_API_BASE_URL` only when the loopback backend uses a non-default port.
