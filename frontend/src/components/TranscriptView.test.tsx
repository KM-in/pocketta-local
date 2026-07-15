import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { TranscriptView } from "./TranscriptView";

const transcript = {
  language: "en",
  duration_ms: 1000,
  segments: [
    { id: "seg-0001", start_ms: 0, end_ms: 1000, text: "Original text", confidence: 0.9, uncertain: false },
  ],
};

describe("TranscriptView", () => {
  it("saves only changed segment text", async () => {
    const onSave = vi.fn().mockResolvedValue(undefined);
    render(<TranscriptView transcript={transcript} editable onSave={onSave} />);
    fireEvent.click(screen.getByRole("button", { name: "Correct transcript" }));
    fireEvent.change(screen.getByLabelText("Transcript text for seg-0001"), { target: { value: "Corrected text" } });
    fireEvent.click(screen.getByRole("button", { name: "Save corrections" }));
    await waitFor(() => expect(onSave).toHaveBeenCalledWith([{ segment_id: "seg-0001", text: "Corrected text" }]));
  });
});
