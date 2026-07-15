import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { Recorder } from "./Recorder";

describe("Recorder", () => {
  it("explains the upload fallback when recording is unsupported", async () => {
    render(<Recorder disabled={false} onUse={vi.fn()} />);
    fireEvent.click(screen.getByRole("button", { name: "Start recording" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Upload a file instead");
  });
});
