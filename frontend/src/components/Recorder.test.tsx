import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { Recorder } from "./Recorder";

const originalMediaDevices = Object.getOwnPropertyDescriptor(navigator, "mediaDevices");
const originalMediaRecorder = Object.getOwnPropertyDescriptor(window, "MediaRecorder");
const originalMediaStream = Object.getOwnPropertyDescriptor(globalThis, "MediaStream");
const originalCreateObjectUrl = Object.getOwnPropertyDescriptor(URL, "createObjectURL");
const originalRevokeObjectUrl = Object.getOwnPropertyDescriptor(URL, "revokeObjectURL");

const restore = (target: object, key: PropertyKey, descriptor?: PropertyDescriptor) => {
  if (descriptor) Object.defineProperty(target, key, descriptor);
  else Reflect.deleteProperty(target, key);
};

const track = (kind: "audio" | "video", displaySurface = "browser") => ({
  kind,
  stop: vi.fn(),
  addEventListener: vi.fn(),
  getSettings: vi.fn(() => ({ displaySurface })),
}) as unknown as MediaStreamTrack;

const captureStream = (audioTracks: MediaStreamTrack[], otherTracks: MediaStreamTrack[] = []) => ({
  getAudioTracks: vi.fn(() => audioTracks),
  getVideoTracks: vi.fn(() => otherTracks.filter((item) => item.kind === "video")),
  getTracks: vi.fn(() => [...audioTracks, ...otherTracks]),
}) as unknown as MediaStream;

class MockMediaStream {
  static instances: MockMediaStream[] = [];
  tracks: MediaStreamTrack[];

  constructor(tracks: MediaStreamTrack[]) {
    this.tracks = tracks;
    MockMediaStream.instances.push(this);
  }

  getTracks = () => this.tracks;
  getAudioTracks = () => this.tracks.filter((item) => item.kind === "audio");
}

class MockMediaRecorder {
  static instances: MockMediaRecorder[] = [];
  static isTypeSupported = vi.fn(() => true);
  inputStream: MediaStream;
  mimeType = "audio/webm";
  state = "inactive";
  ondataavailable: ((event: BlobEvent) => void) | null = null;
  onstop: (() => void) | null = null;

  constructor(inputStream: MediaStream) {
    this.inputStream = inputStream;
    MockMediaRecorder.instances.push(this);
  }

  start = vi.fn(() => { this.state = "recording"; });
  stop = vi.fn(() => {
    this.state = "inactive";
    this.onstop?.();
  });
}

const installBrowserMedia = ({
  getUserMedia = vi.fn(),
  getDisplayMedia = vi.fn(),
}: {
  getUserMedia?: ReturnType<typeof vi.fn>;
  getDisplayMedia?: ReturnType<typeof vi.fn>;
} = {}) => {
  Object.defineProperty(navigator, "mediaDevices", {
    configurable: true,
    value: { getUserMedia, getDisplayMedia },
  });
  Object.defineProperty(window, "MediaRecorder", {
    configurable: true,
    value: MockMediaRecorder,
  });
  Object.defineProperty(globalThis, "MediaStream", {
    configurable: true,
    value: MockMediaStream,
  });
  Object.defineProperty(URL, "createObjectURL", {
    configurable: true,
    value: vi.fn(() => "blob:pocketta-recording"),
  });
  Object.defineProperty(URL, "revokeObjectURL", {
    configurable: true,
    value: vi.fn(),
  });
  return { getUserMedia, getDisplayMedia };
};

afterEach(() => {
  cleanup();
  restore(navigator, "mediaDevices", originalMediaDevices);
  restore(window, "MediaRecorder", originalMediaRecorder);
  restore(globalThis, "MediaStream", originalMediaStream);
  restore(URL, "createObjectURL", originalCreateObjectUrl);
  restore(URL, "revokeObjectURL", originalRevokeObjectUrl);
  MockMediaRecorder.instances = [];
  MockMediaStream.instances = [];
  vi.restoreAllMocks();
});

describe("Recorder", () => {
  it("explains the upload fallback when recording is unsupported", async () => {
    render(<Recorder disabled={false} onUse={vi.fn()} />);
    fireEvent.click(screen.getByRole("button", { name: "Record microphone" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Upload a file instead");
  });

  it("keeps microphone recording available", async () => {
    const audioTrack = track("audio");
    const microphoneStream = captureStream([audioTrack]);
    const getUserMedia = vi.fn().mockResolvedValue(microphoneStream);
    const { getDisplayMedia } = installBrowserMedia({ getUserMedia });

    render(<Recorder disabled={false} onUse={vi.fn()} />);
    fireEvent.click(screen.getByRole("button", { name: "Record microphone" }));

    await waitFor(() => expect(getUserMedia).toHaveBeenCalledWith({ audio: true }));
    expect(getDisplayMedia).not.toHaveBeenCalled();
    expect(await screen.findByText("Recording microphone")).toBeInTheDocument();
    expect(MockMediaRecorder.instances[0].inputStream).toBe(microphoneStream);
  });

  it("captures a browser tab but records only its audio track", async () => {
    const audioTrack = track("audio");
    const videoTrack = track("video");
    const sharedTab = captureStream([audioTrack], [videoTrack]);
    const getDisplayMedia = vi.fn().mockResolvedValue(sharedTab);
    installBrowserMedia({ getDisplayMedia });

    const onUse = vi.fn().mockResolvedValue(undefined);
    render(<Recorder disabled={false} onUse={onUse} />);
    fireEvent.click(screen.getByRole("button", { name: "Record browser tab audio" }));

    await waitFor(() => expect(getDisplayMedia).toHaveBeenCalledWith(expect.objectContaining({
      audio: expect.objectContaining({ systemAudio: "include" }),
      video: expect.objectContaining({ displaySurface: "browser" }),
      systemAudio: "include",
    })));
    expect(await screen.findByText("Recording browser tab")).toBeInTheDocument();
    expect(MockMediaStream.instances[0].tracks).toEqual([audioTrack]);
    expect(MockMediaRecorder.instances[0].inputStream).toBe(MockMediaStream.instances[0]);
    expect(videoTrack.stop).not.toHaveBeenCalled();

    MockMediaRecorder.instances[0].ondataavailable?.({
      data: new Blob(["tab audio"], { type: "audio/webm" }),
    } as BlobEvent);
    fireEvent.click(screen.getByRole("button", { name: "Stop recording" }));

    fireEvent.click(await screen.findByRole("button", { name: "Use recording" }));
    await waitFor(() => expect(onUse).toHaveBeenCalledOnce());
    expect(onUse.mock.calls[0][0]).toEqual(expect.objectContaining({ type: "audio/webm" }));
    expect(audioTrack.stop).toHaveBeenCalledOnce();
    expect(videoTrack.stop).toHaveBeenCalledOnce();
  });

  it("explains how to retry when the selected tab has no shared audio", async () => {
    const videoTrack = track("video");
    const getDisplayMedia = vi.fn().mockResolvedValue(captureStream([], [videoTrack]));
    installBrowserMedia({ getDisplayMedia });

    render(<Recorder disabled={false} onUse={vi.fn()} />);
    fireEvent.click(screen.getByRole("button", { name: "Record browser tab audio" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Share tab audio");
    expect(videoTrack.stop).toHaveBeenCalledOnce();
    expect(MockMediaRecorder.instances).toHaveLength(0);
  });

  it("explains that window sharing cannot provide tab audio", async () => {
    const videoTrack = track("video", "window");
    const getDisplayMedia = vi.fn().mockResolvedValue(captureStream([], [videoTrack]));
    installBrowserMedia({ getDisplayMedia });

    render(<Recorder disabled={false} onUse={vi.fn()} />);
    fireEvent.click(screen.getByRole("button", { name: "Record browser tab audio" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Choose a browser tab, not a window or screen");
    expect(videoTrack.stop).toHaveBeenCalledOnce();
    expect(MockMediaRecorder.instances).toHaveLength(0);
  });

  it("reports a cancelled tab-sharing prompt", async () => {
    const getDisplayMedia = vi.fn().mockRejectedValue(new DOMException("Denied", "NotAllowedError"));
    installBrowserMedia({ getDisplayMedia });

    render(<Recorder disabled={false} onUse={vi.fn()} />);
    fireEvent.click(screen.getByRole("button", { name: "Record browser tab audio" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("cancelled or denied");
  });
});
