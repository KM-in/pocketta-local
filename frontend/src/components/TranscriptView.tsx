import { useEffect, useState } from "react";
import type { SegmentCorrection, Transcript } from "../types";

const timestamp = (milliseconds: number) => {
  const seconds = Math.floor(milliseconds / 1000);
  return `${String(Math.floor(seconds / 60)).padStart(2, "0")}:${String(seconds % 60).padStart(2, "0")}`;
};

export function TranscriptView({
  transcript,
  editable = false,
  hasStudyPack = false,
  onSave,
}: {
  transcript: Transcript;
  editable?: boolean;
  hasStudyPack?: boolean;
  onSave?: (corrections: SegmentCorrection[]) => Promise<void>;
}) {
  const uncertainCount = transcript.segments.filter((segment) => segment.uncertain).length;
  const [editing, setEditing] = useState(false);
  const [drafts, setDrafts] = useState<Record<string, string>>({});
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    setDrafts(Object.fromEntries(transcript.segments.map((segment) => [segment.id, segment.text])));
    setEditing(false);
  }, [transcript]);

  const save = async () => {
    if (!onSave) return;
    const corrections = transcript.segments
      .filter((segment) => drafts[segment.id]?.trim() !== segment.text)
      .map((segment) => ({ segment_id: segment.id, text: drafts[segment.id].trim() }));
    if (!corrections.length) {
      setEditing(false);
      return;
    }
    if (hasStudyPack && !window.confirm("Saving transcript corrections will remove the current study pack. Regenerate it afterward?")) return;
    setSaving(true);
    try {
      await onSave(corrections);
      setEditing(false);
    } finally {
      setSaving(false);
    }
  };

  return (
    <section className="transcript" aria-labelledby="transcript-heading">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Source of truth</p>
          <h2 id="transcript-heading">Transcript</h2>
        </div>
        <div className="transcript-actions">
          <span className="uncertainty-count">{uncertainCount} uncertain</span>
          {editable && !editing && <button type="button" className="button" onClick={() => setEditing(true)}>Correct transcript</button>}
          {editing && <>
            <button type="button" className="button" disabled={saving} onClick={() => void save()}>{saving ? "Saving…" : "Save corrections"}</button>
            <button type="button" className="button secondary" disabled={saving} onClick={() => setEditing(false)}>Cancel</button>
          </>}
        </div>
      </div>
      {editing && <p className="editing-note">Segment IDs and timestamps stay fixed. Correct wording only; the current study pack will be invalidated.</p>}
      <div className="segments">
        {transcript.segments.map((segment) => (
          <article
            id={segment.id}
            tabIndex={-1}
            className={`segment ${segment.uncertain ? "uncertain" : ""}`}
            key={segment.id}
          >
            <div className="segment-meta">
              <time>{timestamp(segment.start_ms)}</time>
              <span>{segment.id}</span>
              {segment.uncertain && <span className="flag">Check audio</span>}
            </div>
            {editing ? (
              <textarea
                aria-label={`Transcript text for ${segment.id}`}
                value={drafts[segment.id] ?? segment.text}
                onChange={(event) => setDrafts((current) => ({ ...current, [segment.id]: event.target.value }))}
              />
            ) : <p>{segment.text}</p>}
          </article>
        ))}
      </div>
    </section>
  );
}
