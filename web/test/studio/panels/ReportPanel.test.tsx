import type { ReactNode } from "react";
import { act } from "react";
import { beforeEach, describe, expect, it } from "vitest";
import { page, userEvent } from "vitest/browser";
import { render } from "vitest-browser-react";
import { WireContext, WireStore } from "../../../src/wire/store";
import { DEFAULT_ARRANGEMENT, useDoc } from "../../../src/studio/store/doc";
import {
  formatA,
  formatPct,
  formatV,
  formatW,
  IssueList,
  PowerCapEditor,
  ReportPanel,
} from "../../../src/studio/panels/ReportPanel";
import type { RigReport } from "../../../src/studio/api/types";

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

// A partial report: the panel shows the parts it is given.
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
} as unknown as RigReport;

const wire = { store: new WireStore(), sender: { send() {}, sendLatest() {}, ask: () => Promise.resolve(true) } };

/** The panel on a wire that has sent no power reading. */
const wired = (ui: ReactNode) => render(<WireContext.Provider value={wire}>{ui}</WireContext.Provider>);

describe("ReportPanel", () => {
  it("leads with the summary, unrounded", async () => {
    const screen = await wired(<ReportPanel stale={false} issues={[]} report={report} />);
    const summary = screen.getByRole("region", { name: "Summary" });
    await expect.element(summary.getByText("1,228.8 W")).toBeInTheDocument();
    await expect.element(summary.getByText("51.2 A")).toBeInTheDocument();
    await expect.element(screen.getByTestId("report-capped")).toHaveTextContent(
      "113.0 W 4.7 ARGB draws at most 614.4 W",
    );
    await expect.element(summary.getByText("2 · 1")).toBeInTheDocument();
    await expect.element(summary.getByText("2 · 80.0% (240.0 W)")).toBeInTheDocument();
  });

  it("shows the live watts from the wire's power reading", async () => {
    const live = new WireStore();
    live.receive({ type: "power", watts: 42.5, uncapped_watts: 60 });
    const screen = await render(
      <WireContext.Provider value={{ ...wire, store: live }}>
        <ReportPanel stale={false} issues={[]} report={report} />
      </WireContext.Provider>,
    );
    const stat = screen.getByTestId("report-watts");
    await expect.poll(() => stat.element().textContent).toContain("42.5 W");
    await expect.poll(() => stat.element().textContent).toContain("60.0 W uncapped");
    act(() => live.receive({ type: "power", watts: 10, uncapped_watts: 10 }));
    await expect.poll(() => stat.element().textContent).toBe("10.0 W");
  });

  it("collapses every section and the warnings by default", async () => {
    await wired(
      <ReportPanel
        stale={false}
        issues={[
          { level: "error", code: "e", message: "broken", ref: null },
          { level: "violation", code: "v", message: "over cap", ref: null },
          { level: "warning", code: "w", message: "assumed rating", ref: null },
        ]}
        report={report}
      />,
    );
    const details = Array.from(document.querySelectorAll("details"));
    expect(details.map((d) => d.querySelector("summary")?.textContent)).toEqual(
      expect.arrayContaining([
        "Warnings (1)",
        "Outputs (1)",
        "PSUs (2)",
        "Bill of materials (0)",
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

  it("says when there is no report", async () => {
    const screen = await wired(<ReportPanel stale={false} issues={[]} report={null} />);
    await expect.element(screen.getByText("The server sent no report for this rig.")).toBeInTheDocument();
  });
});

describe("IssueList", () => {
  it("says when there are no issues", async () => {
    const screen = await render(<IssueList issues={[]} />);
    await expect.element(screen.getByText("No issues.")).toBeInTheDocument();
  });
});

describe("PowerCapEditor", () => {
  beforeEach(() =>
    useDoc.getState().load(DEFAULT_ARRANGEMENT, { mode: "draft" }),
  );
  const present = () => useDoc.getState().history.present;

  const entry = (name: string) => page.getByRole("spinbutton", { name });
  /** Type `text` over what entry `name` shows, then press Enter, as a person does. */
  const retype = async (name: string, text: string) => {
    await userEvent.tripleClick(entry(name));
    // One key at a time, as a person types: each lands after the entry has drawn the last.
    for (const key of text) await userEvent.keyboard(key);
    await expect.element(entry(name)).toHaveValue(text);
    await userEvent.keyboard("{Enter}");
  };

  it("writes the cap into the arrangement and drops it when it caps nothing", async () => {
    const screen = await render(<PowerCapEditor />);
    const cap = screen.getByRole("switch", { name: "Cap the watts" });
    await expect.element(cap).not.toBeChecked();
    await expect.element(entry("Max watts")).not.toBeInTheDocument();
    await expect.element(entry("Max brightness")).toHaveValue("100");

    await cap.click();
    await expect.poll(() => present().power).toEqual({ max_watts: 500 });
    await retype("Max watts", "750");
    expect(present().power).toEqual({ max_watts: 750 });
    await retype("Max brightness", "18");
    expect(present().power).toEqual({ max_watts: 750, max_brightness: 0.18 });

    await cap.click();
    await expect.poll(() => present().power).toEqual({ max_brightness: 0.18 });
    await retype("Max brightness", "100");
    expect(present()).not.toHaveProperty("power");
    expect(present()).toEqual(DEFAULT_ARRANGEMENT);
  });

  it("shows the cap of the arrangement it opens", async () => {
    useDoc.getState().load(
      {
        ...DEFAULT_ARRANGEMENT,
        power: { max_watts: 750, max_brightness: 0.5 },
      },
      { mode: "shared", id: "x" },
    );
    const screen = await render(<PowerCapEditor />);
    await expect.element(screen.getByRole("switch", { name: "Cap the watts" })).toBeChecked();
    await expect.element(entry("Max watts")).toHaveValue("750.0");
    await expect.element(entry("Max brightness")).toHaveValue("50");
  });
});
