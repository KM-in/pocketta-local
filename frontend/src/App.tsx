import { ChangeEvent, DragEvent, useCallback, useEffect, useState } from "react";
import { api } from "./api/client";
import { Recorder } from "./components/Recorder";
import { StudyPackView } from "./components/StudyPackView";
import { TranscriptView } from "./components/TranscriptView";
import type { HealthResponse, LectureDetail, LectureStatus, LectureSummary, SegmentCorrection } from "./types";
import "./styles.css";

const ACTIVE = new Set<LectureStatus>(["queued", "normalizing", "transcribing", "generating", "deleting"]);

function App() {
  const [lectures, setLectures] = useState<LectureSummary[]>([]);
  const [selected, setSelected] = useState<LectureDetail | null>(null);
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [showSetup, setShowSetup] = useState(false);
  const [online, setOnline] = useState(navigator.onLine);

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

  useEffect(() => { void refresh(); }, []);
  useEffect(() => {
    const update = () => setOnline(navigator.onLine);
    window.addEventListener("online", update);
    window.addEventListener("offline", update);
    return () => {
      window.removeEventListener("online", update);
      window.removeEventListener("offline", update);
    };
  }, []);
  useEffect(() => {
    if (!lectures.some((lecture) => ACTIVE.has(lecture.status))) return;
    const timer = window.setInterval(() => void refresh(), 1500);
    return () => window.clearInterval(timer);
  }, [lectures, refresh]);

  const selectSummary = async (lecture: LectureSummary) => {
    setLectures((current) => [lecture, ...current.filter((item) => item.id !== lecture.id)]);
    setSelected(await api.get(lecture.id));
  };

  const upload = async (file?: File, title?: string) => {
    if (!file) return;
    setBusy(true);
    setError("");
    try {
      await selectSummary(await api.upload(file, title));
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Upload failed");
    } finally {
      setBusy(false);
    }
  };

  const tryDemo = async () => {
    setBusy(true);
    setError("");
    try {
      await selectSummary(await api.demo());
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Demo could not start");
    } finally {
      setBusy(false);
    }
  };

  const chooseLecture = async (lecture: LectureSummary) => {
    try { setSelected(await api.get(lecture.id)); }
    catch (cause) { setError(cause instanceof Error ? cause.message : "Could not open lecture"); }
  };

  const actOnSelected = async (action: (id: string) => Promise<unknown>) => {
    if (!selected) return;
    setBusy(true);
    setError("");
    try {
      await action(selected.id);
      await refresh();
      setSelected(await api.get(selected.id));
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Action failed");
    } finally {
      setBusy(false);
    }
  };

  const remove = async () => {
    if (!selected || !window.confirm(`Permanently delete “${selected.title}” and all generated data?`)) return;
    setBusy(true);
    try {
      await api.delete(selected.id);
      setLectures((current) => current.filter((item) => item.id !== selected.id));
      setSelected(null);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Deletion failed");
    } finally { setBusy(false); }
  };

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand"><div className="brand-mark">P</div><div><strong>PocketTA</strong><span>Local study desk</span></div></div>
        <label className={`upload-small ${busy ? "disabled" : ""}`}>
          <input type="file" accept=".wav,.mp3,.m4a,.mp4,.webm,.ogg" disabled={busy} onChange={(event: ChangeEvent<HTMLInputElement>) => void upload(event.target.files?.[0])} />
          <span>＋</span> New lecture
        </label>
        <nav className="lecture-list" aria-label="Lectures">
          <p className="nav-label">Your lectures</p>
          {lectures.length === 0 && <p className="empty-list">Nothing here yet.</p>}
          {lectures.map((lecture) => (
            <button type="button" className={selected?.id === lecture.id ? "selected" : ""} onClick={() => void chooseLecture(lecture)} key={lecture.id}>
              <span className="lecture-name">{lecture.title}</span>
              <span className={`status ${lecture.status}`}>{lecture.status}</span>
            </button>
          ))}
        </nav>
        <div className={`network-badge ${online ? "online" : "offline"}`}><span className="dot" /><strong>{online ? "Browser online" : "Browser offline"}</strong><small>Core processing uses localhost</small></div>
        <button type="button" className={`readiness ${health?.ready ? "ready" : "not-ready"}`} onClick={() => setShowSetup((current) => !current)} aria-expanded={showSetup}>
          <span className="dot" /><span className="readiness-copy"><strong>{health?.ready ? "Local engine ready" : "Setup required"}</strong><span>{health?.ready ? "Core AI on this Mac" : "Open readiness details"}</span></span>
        </button>
      </aside>

      <main>
        {error && <div className="error-banner" role="alert">{error}</div>}
        {showSetup && health && <section className="setup-card setup-dialog" aria-label="Local engine readiness"><div className="setup-heading"><div><p className="eyebrow">Local mode</p><h2>Local engine and storage</h2><p>{online ? "The browser is online; PocketTA still calls only loopback services." : "Wi-Fi is offline. Prepared local models remain available."}</p></div><button type="button" className="button" onClick={() => setShowSetup(false)}>Close</button></div><ReadinessDetails health={health} /></section>}
        {!selected ? <Welcome health={health} busy={busy} upload={upload} tryDemo={tryDemo} /> : (
          <LecturePage
            lecture={selected}
            busy={busy}
            remove={remove}
            cancel={() => actOnSelected(api.cancel)}
            generate={() => actOnSelected(api.generate)}
            update={async (payload) => { await actOnSelected((id) => api.update(id, payload)); }}
          />
        )}
      </main>
    </div>
  );
}

function Welcome({ health, busy, upload, tryDemo }: { health: HealthResponse | null; busy: boolean; upload: (file?: File, title?: string) => Promise<void>; tryDemo: () => Promise<void> }) {
  const [title, setTitle] = useState("");
  const drop = (event: DragEvent<HTMLLabelElement>) => { event.preventDefault(); void upload(event.dataTransfer.files[0], title); };
  return (
    <div className="welcome">
      <div className="welcome-copy"><p className="eyebrow">Private by default · Works offline</p><h1>Turn a lecture into a study pack.</h1><p>Your recording stays on this laptop. PocketTA creates a transcript, notes, flashcards, and a quiz—with every answer linked to its source.</p></div>
      <label className="title-field"><span>Optional lecture title</span><input value={title} maxLength={200} onChange={(event) => setTitle(event.target.value)} placeholder="e.g. Introduction to computation" /></label>
      <label className={`drop-zone ${busy ? "disabled" : ""}`} onDragOver={(event) => event.preventDefault()} onDrop={drop}>
        <input type="file" accept=".wav,.mp3,.m4a,.mp4,.webm,.ogg" disabled={busy} onChange={(event) => void upload(event.target.files?.[0], title)} />
        <span className="upload-icon">↑</span><strong>{busy ? "Starting…" : "Drop a lecture recording here"}</strong><span>or click to choose · up to 200 MB</span>
      </label>
      <div className="welcome-actions"><button type="button" className="button demo-button" disabled={busy} onClick={() => void tryDemo()}>Try the offline demo</button><span>No recording needed · attributed sample</span></div>
      <Recorder disabled={busy} onUse={(file) => upload(file, title)} />
      {health && !health.ready && <section className="setup-card"><div><p className="eyebrow">Readiness</p><h2>Finish local setup</h2></div><ReadinessDetails health={health} onlyFailures /></section>}
      <div className="privacy-note"><span>⌂</span><div><strong>No cloud. No account. No tracking.</strong><p>Audio, transcript, and study materials live only in PocketTA’s local data folder until you delete them.</p></div></div>
    </div>
  );
}

export function ReadinessDetails({ health, onlyFailures = false }: { health: HealthResponse; onlyFailures?: boolean }) {
  const components = Object.entries(health.components).filter(([, value]) => !onlyFailures || !value.ready);
  return <ul className="readiness-details">{components.map(([name, value]) => <li key={name}><strong>{name.replaceAll("_", " ")}</strong><span className={value.ready ? "component-ready" : "component-missing"}>{value.ready ? "Ready" : "Needs attention"}</span><code>{value.detail}</code>{!value.ready && value.remediation && <code className="remediation">{value.remediation}</code>}</li>)}</ul>;
}

function LecturePage({ lecture, busy, remove, cancel, generate, update }: { lecture: LectureDetail; busy: boolean; remove: () => Promise<void>; cancel: () => Promise<void>; generate: () => Promise<void>; update: (payload: { title?: string; corrections?: SegmentCorrection[] }) => Promise<void> }) {
  const active = ACTIVE.has(lecture.status);
  const [title, setTitle] = useState(lecture.title);
  const [editingTitle, setEditingTitle] = useState(false);
  useEffect(() => setTitle(lecture.title), [lecture.title]);
  const saveTitle = async () => {
    if (!title.trim() || title.trim() === lecture.title) { setEditingTitle(false); return; }
    await update({ title: title.trim() });
    setEditingTitle(false);
  };
  const canGenerate = Boolean(lecture.transcript) && !active && ["failed", "cancelled", "transcribed", "completed"].includes(lecture.status);
  return (
    <div className="lecture-page">
      <header className="lecture-header">
        <div><p className="eyebrow">{active ? "Processing locally" : "Lecture"}</p>{editingTitle ? <div className="title-editor"><input value={title} maxLength={200} onChange={(event) => setTitle(event.target.value)} aria-label="Lecture title" /><button className="button" type="button" onClick={() => void saveTitle()}>Save</button><button className="button secondary" type="button" onClick={() => { setTitle(lecture.title); setEditingTitle(false); }}>Cancel</button></div> : <div className="editable-title"><h1>{lecture.title}</h1>{!active && <button type="button" className="text-button" onClick={() => setEditingTitle(true)}>Edit title</button>}</div>}<span className={`status ${lecture.status}`}>{lecture.status}</span></div>
        <div className="header-actions">
          {lecture.status === "completed" && <a className="button secondary" href={api.exportUrl(lecture.id)}>Export Markdown</a>}
          {lecture.status === "completed" && <button className="button secondary" type="button" onClick={() => window.print()}>Print / Save as PDF</button>}
          {canGenerate && <button className="button" type="button" disabled={busy} onClick={() => void generate()}>{lecture.status === "completed" ? "Regenerate" : "Generate study pack"}</button>}
          <button className="button danger" type="button" disabled={busy} onClick={() => void remove()}>Delete permanently</button>
        </div>
      </header>
      {active && lecture.status !== "deleting" && <JobProgress lecture={lecture} disabled={busy} onCancel={cancel} />}
      {lecture.status === "failed" && <div className="failure-card"><p className="eyebrow">Processing stopped</p><h2>We couldn’t finish this lecture.</h2><p>{lecture.error}</p>{lecture.transcript && <p>Your transcript is safe. Retry generation without transcribing again.</p>}</div>}
      {lecture.status === "cancelled" && <div className="failure-card cancelled-card"><p className="eyebrow">Cancelled</p><h2>Local processing stopped.</h2><p>Any completed transcript remains available below.</p></div>}
      {lecture.metrics.total_seconds > 0 && <Metrics metrics={lecture.metrics} />}
      {lecture.study_pack && <StudyPackView pack={lecture.study_pack} />}
      {lecture.transcript && <TranscriptView transcript={lecture.transcript} editable={!active} hasStudyPack={Boolean(lecture.study_pack)} onSave={(corrections) => update({ corrections })} />}
    </div>
  );
}

function JobProgress({ lecture, disabled, onCancel }: { lecture: LectureDetail; disabled: boolean; onCancel: () => Promise<void> }) {
  const stages: Array<[LectureStatus, string]> = [["normalizing", "Preparing"], ["transcribing", "Transcribing"], ["generating", "Creating practice"]];
  const order = stages.findIndex(([status]) => status === lecture.status);
  return <section className="processing-card" aria-live="polite"><div className="progress-copy"><p className="eyebrow">{lecture.progress}% complete</p><h2>{lecture.message || statusMessage(lecture.status)}</h2><progress max="100" value={lecture.progress}>{lecture.progress}%</progress><ol className="stage-list">{stages.map(([status, label], index) => <li className={index < order ? "done" : index === order ? "current" : ""} key={status}><span>{index < order ? "✓" : index + 1}</span>{label}</li>)}</ol><p>You can leave this page. One lecture is processed at a time.</p></div><button type="button" className="button danger" disabled={disabled} onClick={() => void onCancel()}>Cancel processing</button></section>;
}

function Metrics({ metrics }: { metrics: LectureDetail["metrics"] }) {
  return <section className="metrics" aria-label="Local processing metrics"><div><strong>{metrics.total_seconds.toFixed(1)}s</strong><span>Total observed time</span></div>{Object.entries(metrics.stage_seconds).map(([stage, seconds]) => <div key={stage}><strong>{seconds.toFixed(1)}s</strong><span>{stage}</span></div>)}<div><strong>{Math.round(metrics.peak_system_memory_mb)} MB</strong><span>Peak observed system memory</span></div></section>;
}

function statusMessage(status: LectureStatus) {
  return ({ queued: "Waiting for the local worker…", normalizing: "Preparing the recording…", transcribing: "Listening with whisper.cpp…", generating: "Building your study pack with Qwen…", deleting: "Deleting local data…", transcribed: "Transcript ready", cancelled: "Cancelled", completed: "Complete", failed: "Failed" })[status];
}

export default App;
