import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it } from "vitest";
import { DEFAULT_ARRANGEMENT, useDoc } from "@/store/doc";
import {
  formatA,
  formatPct,
  formatV,
  formatW,
  IssueList,
  PowerCapEditor,
  ReportPanel,
} from "./ReportPanel";

describe("number formatting", () => {
  it("shows watts and amps with one decimal and a thousands separator", () => {
    expect(formatW(1228.8)).toBe("1,228.8 W");
    expect(formatW(76)).toBe("76.0 W");
    expect(formatA(51.2)).toBe("51.2 A");
    expect(formatA(0.04)).toBe("0.0 A");
  });

  it("shows volts to two decimals and fractions as one-decimal percent", () => {
    expect(formatV(0.17)).toBe("0.17 V");
    expect(formatV(24)).toBe("24.00 V");
    expect(formatPct(0.853)).toBe("85.3%");
    expect(formatPct(1)).toBe("100.0%");
  });
});

const report = {
  totals: {
    pixels: 3072,
    worst_w: 1228.8,
    worst_a: 51.2,
    rgb_worst_w: 614.4,
    rgb_worst_a: 25.6,
    capped_w: 113.0,
    capped_a: 4.71,
    controllers: 2,
    psus: 2,
    feeds: 24,
  },
  outputs: [
    {
      controller: "c1",
      output: "rmt0",
      pixels: 512,
      led_label: "SK6812",
      frame_s: 0.0155,
      wire_fps: 64.5,
    },
  ],
  psus: [
    {
      id: "p1",
      type: "a",
      v_out: 24,
      i_max_a: 12.5,
      current_a: 5,
      load_fraction: 0.4,
      watts: 120,
    },
    {
      id: "p2",
      type: "a",
      v_out: 24,
      i_max_a: 12.5,
      current_a: 10,
      load_fraction: 0.8,
      watts: 240,
    },
  ],
  basis: [
    {
      fact: "m12.rated_a",
      v: 4,
      status: "assumed",
      src: "RES-017",
      used_for: ["feeds"],
    },
  ],
};

describe("ReportPanel", () => {
  it("leads with the summary, unrounded", () => {
    render(<ReportPanel stale={false} issues={[]} report={report} />);
    const summary = screen.getByRole("region", { name: "Summary" });
    expect(within(summary).getByText("1,228.8 W")).toBeInTheDocument();
    expect(within(summary).getByText("51.2 A")).toBeInTheDocument();
    expect(screen.getByTestId("report-capped")).toHaveTextContent(
      "113.0 W 4.7 ARGB draws at most 614.4 W",
    );
    expect(within(summary).getByText("2 · 1")).toBeInTheDocument();
    expect(
      within(summary).getByText("2 · 80.0% (240.0 W)"),
    ).toBeInTheDocument();
  });

  it("collapses every section and the warnings by default", () => {
    render(
      <ReportPanel
        stale={false}
        issues={[
          { level: "error", code: "e", message: "broken" },
          { level: "violation", code: "v", message: "over cap" },
          { level: "warning", code: "w", message: "assumed rating" },
        ]}
        report={report}
      />,
    );
    const details = Array.from(document.querySelectorAll("details"));
    expect(details.map((d) => d.querySelector("summary")?.textContent)).toEqual(
      expect.arrayContaining([
        "▸Warnings1",
        "▸Outputs1",
        "▸PSUs2",
        "▸Bill of materials0",
      ]),
    );
    expect(details.every((d) => !d.open)).toBe(true);
    expect(
      document.querySelector('[data-level="error"]')?.closest("details"),
    ).toBeNull();
    expect(
      document.querySelector('[data-level="violation"]')?.closest("details"),
    ).toBeNull();
    expect(
      document.querySelector('[data-level="warning"]')?.closest("details"),
    ).not.toBeNull();
  });

  it("says when there is no report", () => {
    render(<ReportPanel stale={false} issues={[]} report={null} />);
    expect(
      screen.getByText("The server sent no report for this rig."),
    ).toBeInTheDocument();
  });
});

describe("IssueList", () => {
  it("says when there are no issues", () => {
    render(<IssueList issues={[]} />);
    expect(screen.getByText("No issues.")).toBeInTheDocument();
  });
});

describe("PowerCapEditor", () => {
  beforeEach(() =>
    useDoc.getState().load(DEFAULT_ARRANGEMENT, { mode: "draft" }),
  );
  const present = () => useDoc.getState().history.present;

  it("writes the cap into the arrangement and drops it when it caps nothing", async () => {
    const user = userEvent.setup();
    render(<PowerCapEditor />);
    const watts = screen.getByLabelText(/Max watts/);
    const brightness = screen.getByLabelText(/Max brightness/);
    expect(watts).toHaveValue(null);
    expect(brightness).toHaveValue(100);

    await user.type(watts, "500");
    expect(present().power).toEqual({ max_watts: 500 });
    await user.clear(brightness);
    await user.type(brightness, "18.4");
    expect(present().power).toEqual({ max_watts: 500, max_brightness: 0.184 });

    await user.clear(watts);
    expect(present().power).toEqual({ max_brightness: 0.184 });
    await user.clear(brightness);
    await user.type(brightness, "100");
    expect(present()).not.toHaveProperty("power");
    expect(present()).toEqual(DEFAULT_ARRANGEMENT);
  });

  it("shows the cap of the arrangement it opens", () => {
    useDoc.getState().load(
      {
        ...DEFAULT_ARRANGEMENT,
        power: { max_watts: 750, max_brightness: 0.5 },
      },
      { mode: "shared", id: "x" },
    );
    render(<PowerCapEditor />);
    expect(screen.getByLabelText(/Max watts/)).toHaveValue(750);
    expect(screen.getByLabelText(/Max brightness/)).toHaveValue(50);
  });
});
