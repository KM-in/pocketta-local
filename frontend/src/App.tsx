import { ChangeEvent, DragEvent, useCallback, useEffect, useState } from "react";
import { api } from "./api/client";
import { StudyPackView } from "./components/StudyPackView";
import { TranscriptView } from "./components/TranscriptView";
import type { HealthResponse, LectureDetail, LectureSummary } from "./types";
import "./styles.css";

const ACTIVE = new Set(["queued", "normalizing", "transcribing", "generating", "deleting"]);

function App() {
  const [lectures, setLectures] = useState<LectureSummary[]>([]);
  const [selected, setSelected] = useState<LectureDetail | null>(null);
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [showSetup, setShowSetup] = useState(false);

  const refresh = useCallback(async () => {
    try {
      const [nextLectures, nextHealth] = await Promise.all([api.list(), api.health()]);
      setLectures(nextLectures);
      setHealth(nextHealth);
      if (selected) {
        const current = nextLectures.find((lecture) => lecture.id === selected.id);
        if (current) setSelected(await api.get(current.id));
      }
      setError("");
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Could not reach PocketTA");
    }
  }, [selected?.id]);

  useEffect(() => {
    void refresh();
  }, []);

  useEffect(() => {
    if (!lectures.some((lecture) => ACTIVE.has(lecture.status))) return;
    const timer = window.setInterval(() => void refresh(), 1500);
    return () => window.clearInterval(timer);
  }, [lectures, refresh]);

  const upload = async (file?: File) => {
    if (!file) return;
    setBusy(true);
    setError("");
    try {
      const lecture = await api.upload(file);
      setLectures((current) => [lecture, ...current]);
      setSelected(await api.get(lecture.id));
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Upload failed");
    } finally {
      setBusy(false);
    }
  };

  const chooseLecture = async (lecture: LectureSummary) => {
    try {
      setSelected(await api.get(lecture.id));
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Could not open lecture");
    }
  };

  const remove = async () => {
    if (!selected || !window.confirm(`Permanently delete “${selected.original_filename}” and all generated data?`)) return;
    setBusy(true);
    try {
      await api.delete(selected.id);
      setLectures((current) => current.filter((item) => item.id !== selected.id));
      setSelected(null);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Deletion failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark">P</div>
          <div><strong>PocketTA</strong><span>Local study desk</span></div>
        </div>
        <label className={`upload-small ${busy ? "disabled" : ""}`}>
          <input type="file" accept="audio/*,video/*" disabled={busy} onChange={(event: ChangeEvent<HTMLInputElement>) => void upload(event.target.files?.[0])} />
          <span>＋</span> New lecture
        </label>
        <nav className="lecture-list" aria-label="Lectures">
          <p className="nav-label">Your lectures</p>
          {lectures.length === 0 && <p className="empty-list">Nothing here yet.</p>}
          {lectures.map((lecture) => (
            <button type="button" className={selected?.id === lecture.id ? "selected" : ""} onClick={() => void chooseLecture(lecture)} key={lecture.id}>
              <span className="lecture-name">{lecture.original_filename}</span>
              <span className={`status ${lecture.status}`}>{lecture.status}</span>
            </button>
          ))}
        </nav>
        <button
          type="button"
          className={`readiness ${health?.ready ? "ready" : "not-ready"}`}
          onClick={() => setShowSetup((current) => !current)}
          aria-expanded={showSetup}
        >
          <span className="dot" />
          <span className="readiness-copy"><strong>{health?.ready ? "Offline engine ready" : "Setup required"}</strong><span>{health?.ready ? "View local components" : "Open readiness details"}</span></span>
        </button>
      </aside>

      <main>
        {error && <div className="error-banner" role="alert">{error}</div>}
        {showSetup && health && (
          <section className="setup-card setup-dialog" aria-label="Local engine readiness">
            <div className="setup-heading">
              <div><p className="eyebrow">Readiness</p><h2>Local engine components</h2></div>
              <button type="button" className="button" onClick={() => setShowSetup(false)}>Close</button>
            </div>
            <ReadinessDetails health={health} />
          </section>
        )}
        {!selected ? (
          <Welcome health={health} busy={busy} upload={upload} />
        ) : (
          <LecturePage lecture={selected} busy={busy} remove={remove} />
        )}
      </main>
    </div>
  );
}

function Welcome({ health, busy, upload }: { health: HealthResponse | null; busy: boolean; upload: (file?: File) => Promise<void> }) {
  const drop = (event: DragEvent<HTMLLabelElement>) => {
    event.preventDefault();
    void upload(event.dataTransfer.files[0]);
  };
  return (
    <div className="welcome">
      <div className="welcome-copy">
        <p className="eyebrow">Private by default · Works offline</p>
        <h1>Turn a lecture into a study pack.</h1>
        <p>Your recording stays on this laptop. PocketTA creates a transcript, notes, flashcards, and a quiz—with every answer linked to its source.</p>
      </div>
      <label className={`drop-zone ${busy ? "disabled" : ""}`} onDragOver={(event) => event.preventDefault()} onDrop={drop}>
        <input type="file" accept="audio/*,video/*" disabled={busy} onChange={(event) => void upload(event.target.files?.[0])} />
        <span className="upload-icon">↑</span>
        <strong>{busy ? "Uploading…" : "Drop a lecture recording here"}</strong>
        <span>or click to choose · up to 200 MB</span>
      </label>
      {health && !health.ready && (
        <section className="setup-card">
          <div><p className="eyebrow">Readiness</p><h2>Finish local setup</h2></div>
          <ReadinessDetails health={health} onlyFailures />
        </section>
      )}
      <div className="privacy-note"><span>⌂</span><div><strong>No cloud. No account. No tracking.</strong><p>Audio, transcript, and study materials live only in PocketTA’s local data folder until you delete them.</p></div></div>
    </div>
  );
}

export function ReadinessDetails({ health, onlyFailures = false }: { health: HealthResponse; onlyFailures?: boolean }) {
  const components = Object.entries(health.components).filter(([, value]) => !onlyFailures || !value.ready);
  return (
    <ul className="readiness-details">
      {components.map(([name, value]) => (
        <li key={name}>
          <strong>{name.replaceAll("_", " ")}</strong>
          <span className={value.ready ? "component-ready" : "component-missing"}>{value.ready ? "Ready" : "Needs attention"}</span>
          <code>{value.detail}</code>
          {!value.ready && value.remediation && <code className="remediation">{value.remediation}</code>}
        </li>
      ))}
    </ul>
  );
}

function LecturePage({ lecture, busy, remove }: { lecture: LectureDetail; busy: boolean; remove: () => Promise<void> }) {
  const active = ACTIVE.has(lecture.status);
  return (
    <div className="lecture-page">
      <header className="lecture-header">
        <div><p className="eyebrow">{active ? "Processing locally" : "Lecture"}</p><h1>{lecture.study_pack?.title ?? lecture.original_filename}</h1><span className={`status ${lecture.status}`}>{lecture.status}</span></div>
        <div className="header-actions">
          {lecture.status === "completed" && <a className="button secondary" href={api.exportUrl(lecture.id)}>Export Markdown</a>}
          <button className="button danger" type="button" disabled={busy} onClick={() => void remove()}>Delete permanently</button>
        </div>
      </header>
      {active && <div className="processing-card"><div className="spinner" /><div><h2>{statusMessage(lecture.status)}</h2><p>You can leave this page. One lecture is processed at a time.</p></div></div>}
      {lecture.status === "failed" && <div className="failure-card"><p className="eyebrow">Processing stopped</p><h2>We couldn’t finish this lecture.</h2><p>{lecture.error}</p></div>}
      {lecture.study_pack && <StudyPackView pack={lecture.study_pack} />}
      {lecture.transcript && <TranscriptView transcript={lecture.transcript} />}
    </div>
  );
}

function statusMessage(status: LectureSummary["status"]) {
  return ({ queued: "Waiting for the local worker…", normalizing: "Preparing the recording…", transcribing: "Listening with whisper.cpp…", generating: "Building your study pack with Qwen…", deleting: "Deleting local data…", completed: "Complete", failed: "Failed" })[status];
}

export default App;
