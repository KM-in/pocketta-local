import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { EvidenceLinks } from "./EvidenceLinks";

describe("EvidenceLinks", () => {
  it("moves to the cited transcript segment", () => {
    const segment = document.createElement("div");
    segment.id = "seg-0001";
    segment.scrollIntoView = vi.fn();
    document.body.appendChild(segment);
    render(<EvidenceLinks ids={["seg-0001"]} />);
    fireEvent.click(screen.getByRole("button", { name: "seg-0001" }));
    expect(segment.scrollIntoView).toHaveBeenCalledWith({ behavior: "smooth", block: "center" });
  });
});
