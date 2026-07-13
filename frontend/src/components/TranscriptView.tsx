import type { Transcript } from "../types";

const timestamp = (milliseconds: number) => {
  const seconds = Math.floor(milliseconds / 1000);
  return `${String(Math.floor(seconds / 60)).padStart(2, "0")}:${String(seconds % 60).padStart(2, "0")}`;
};

export function TranscriptView({ transcript }: { transcript: Transcript }) {
  const uncertainCount = transcript.segments.filter((segment) => segment.uncertain).length;
  return (
    <section className="transcript" aria-labelledby="transcript-heading">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Source of truth</p>
          <h2 id="transcript-heading">Transcript</h2>
        </div>
        <span className="uncertainty-count">{uncertainCount} uncertain</span>
      </div>
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
            <p>{segment.text}</p>
          </article>
        ))}
      </div>
    </section>
  );
}
