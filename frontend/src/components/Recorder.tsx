import { useEffect, useRef, useState } from "react";

const supportedMime = () =>
  ["audio/webm;codecs=opus", "audio/webm", "audio/ogg;codecs=opus", "audio/mp4"].find(
    (value) => window.MediaRecorder?.isTypeSupported(value),
  ) ?? "";

const clock = (seconds: number) =>
  `${String(Math.floor(seconds / 60)).padStart(2, "0")}:${String(seconds % 60).padStart(2, "0")}`;

export function Recorder({ disabled, onUse }: { disabled: boolean; onUse: (file: File) => Promise<void> }) {
  const recorder = useRef<MediaRecorder | null>(null);
  const stream = useRef<MediaStream | null>(null);
  const chunks = useRef<Blob[]>([]);
  const [recording, setRecording] = useState(false);
  const [seconds, setSeconds] = useState(0);
  const [preview, setPreview] = useState<{ file: File; url: string } | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!recording) return;
    const timer = window.setInterval(() => setSeconds((value) => value + 1), 1000);
    return () => window.clearInterval(timer);
  }, [recording]);

  useEffect(() => () => {
    stream.current?.getTracks().forEach((track) => track.stop());
    if (preview) URL.revokeObjectURL(preview.url);
  }, [preview]);

  const start = async () => {
    setError("");
    if (!navigator.mediaDevices?.getUserMedia || !window.MediaRecorder) {
      setError("This browser does not support local audio recording. Upload a file instead.");
      return;
    }
    try {
      const nextStream = await navigator.mediaDevices.getUserMedia({ audio: true });
      stream.current = nextStream;
      chunks.current = [];
      const mimeType = supportedMime();
      const nextRecorder = new MediaRecorder(nextStream, mimeType ? { mimeType } : undefined);
      recorder.current = nextRecorder;
      nextRecorder.ondataavailable = (event) => {
        if (event.data.size) chunks.current.push(event.data);
      };
      nextRecorder.onstop = () => {
        const type = nextRecorder.mimeType || mimeType || "audio/webm";
        const extension = type.includes("mp4") ? "m4a" : type.includes("ogg") ? "ogg" : "webm";
        const blob = new Blob(chunks.current, { type });
        const file = new File([blob], `pocketta-recording-${Date.now()}.${extension}`, { type });
        setPreview((current) => {
          if (current) URL.revokeObjectURL(current.url);
          return { file, url: URL.createObjectURL(blob) };
        });
        nextStream.getTracks().forEach((track) => track.stop());
        stream.current = null;
      };
      nextRecorder.start(250);
      setSeconds(0);
      setRecording(true);
    } catch (cause) {
      setError(cause instanceof DOMException && cause.name === "NotAllowedError"
        ? "Microphone permission was denied. Allow it in browser settings or upload a recording."
        : "The microphone could not be started. Upload a recording instead.");
    }
  };

  const stop = () => {
    recorder.current?.stop();
    recorder.current = null;
    setRecording(false);
  };

  const discard = () => {
    if (preview) URL.revokeObjectURL(preview.url);
    setPreview(null);
    setSeconds(0);
  };

  return (
    <section className="recorder" aria-label="Record a lecture">
      <div>
        <strong>Record from this browser</strong>
        <span>Microphone audio stays local and follows the same processing flow.</span>
      </div>
      {recording ? (
        <div className="recording-controls" aria-live="polite">
          <span className="recording-dot" /> <time>{clock(seconds)}</time>
          <button type="button" className="button danger" onClick={stop}>Stop recording</button>
        </div>
      ) : preview ? (
        <div className="recording-preview">
          <audio controls src={preview.url} />
          <button type="button" className="button" disabled={disabled} onClick={() => void onUse(preview.file)}>Use recording</button>
          <button type="button" className="button secondary" disabled={disabled} onClick={discard}>Discard</button>
        </div>
      ) : (
        <button type="button" className="button record-button" disabled={disabled} onClick={() => void start()}>Start recording</button>
      )}
      {error && <p className="inline-error" role="alert">{error}</p>}
    </section>
  );
}
