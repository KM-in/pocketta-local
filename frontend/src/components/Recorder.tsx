import { useEffect, useRef, useState } from "react";

type CaptureSource = "microphone" | "browser-tab";

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
  const [activeSource, setActiveSource] = useState<CaptureSource | null>(null);
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
  }, []);

  useEffect(() => () => {
    if (preview) URL.revokeObjectURL(preview.url);
  }, [preview]);

  const start = async (source: CaptureSource) => {
    setError("");
    if (!window.MediaRecorder) {
      setError("This browser does not support local audio recording. Upload a file instead.");
      return;
    }
    if (source === "microphone" && !navigator.mediaDevices?.getUserMedia) {
      setError("This browser cannot record microphone audio. Upload a file instead.");
      return;
    }
    if (source === "browser-tab" && !navigator.mediaDevices?.getDisplayMedia) {
      setError("This browser cannot capture tab audio. Try a Chromium browser or upload a file instead.");
      return;
    }
    try {
      const captureStream = source === "browser-tab"
        ? await navigator.mediaDevices.getDisplayMedia({ video: true, audio: true })
        : await navigator.mediaDevices.getUserMedia({ audio: true });
      const audioTracks = captureStream.getAudioTracks();
      if (!audioTracks.length) {
        captureStream.getTracks().forEach((track) => track.stop());
        setError(source === "browser-tab"
          ? "No tab audio was shared. Select the browser tab and enable “Share tab audio”, then try again."
          : "No microphone audio track was available. Check the selected input or upload a recording instead.");
        return;
      }

      stream.current = captureStream;
      const recordingStream = source === "browser-tab" ? new MediaStream(audioTracks) : captureStream;
      chunks.current = [];
      const mimeType = supportedMime();
      const nextRecorder = new MediaRecorder(recordingStream, mimeType ? { mimeType } : undefined);
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
        captureStream.getTracks().forEach((track) => track.stop());
        stream.current = null;
        setActiveSource(null);
      };
      if (source === "browser-tab") {
        captureStream.getTracks().forEach((track) => track.addEventListener("ended", () => {
          if (nextRecorder.state !== "inactive") {
            nextRecorder.stop();
            setRecording(false);
          }
        }, { once: true }));
      }
      nextRecorder.start(250);
      setSeconds(0);
      setActiveSource(source);
      setRecording(true);
    } catch (cause) {
      if (source === "browser-tab") {
        setError(cause instanceof DOMException && cause.name === "NotAllowedError"
          ? "Tab sharing was cancelled or denied. Try again and select a tab with “Share tab audio” enabled."
          : "Browser tab audio could not be started. Try a Chromium browser or upload a recording instead.");
      } else {
        setError(cause instanceof DOMException && cause.name === "NotAllowedError"
          ? "Microphone permission was denied. Allow it in browser settings or upload a recording."
          : "The microphone could not be started. Upload a recording instead.");
      }
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
        <strong>Record microphone or browser tab</strong>
        <span>For YouTube, choose browser tab, select that tab, and enable “Share tab audio”.</span>
      </div>
      {recording ? (
        <div className="recording-controls" aria-live="polite">
          <span className="recording-dot" />
          <span>{activeSource === "browser-tab" ? "Recording browser tab" : "Recording microphone"}</span>
          <time>{clock(seconds)}</time>
          <button type="button" className="button danger" onClick={stop}>Stop recording</button>
        </div>
      ) : preview ? (
        <div className="recording-preview">
          <audio controls src={preview.url} />
          <button type="button" className="button" disabled={disabled} onClick={() => void onUse(preview.file)}>Use recording</button>
          <button type="button" className="button secondary" disabled={disabled} onClick={discard}>Discard</button>
        </div>
      ) : (
        <div className="record-source-actions">
          <button type="button" className="button secondary" disabled={disabled} onClick={() => void start("microphone")}>Record microphone</button>
          <button type="button" className="button record-button" disabled={disabled} onClick={() => void start("browser-tab")}>Record browser tab audio</button>
        </div>
      )}
      {error && <p className="inline-error" role="alert">{error}</p>}
    </section>
  );
}
