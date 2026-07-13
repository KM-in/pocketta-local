import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { ReadinessDetails } from "./App";

describe("ReadinessDetails", () => {
  it("shows an exact remediation for a missing component", () => {
    render(
      <ReadinessDetails
        health={{
          ready: false,
          components: {
            ffmpeg: {
              ready: false,
              detail: "ffmpeg",
              remediation: "brew install ffmpeg",
            },
          },
        }}
      />,
    );
    expect(screen.getByText("Needs attention")).toBeInTheDocument();
    expect(screen.getByText("brew install ffmpeg")).toBeInTheDocument();
  });
});
