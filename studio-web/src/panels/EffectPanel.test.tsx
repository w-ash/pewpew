import { act, fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { MOCK_PATTERNS } from "@/mocks/frames";
import type { SessionClient } from "@/session/client";
import { decodeParam } from "@/session/params";
import { initialSession, useSession } from "@/store/session";
import { zooRecord } from "@/test/describe";
import { EffectPanel } from "./EffectPanel";

function client() {
  const setParam = vi.fn();
  return {
    setParam,
    client: { setParam, setPattern: vi.fn() } as unknown as SessionClient,
  };
}

describe("EffectPanel", () => {
  beforeEach(() => {
    useSession.setState({
      ...initialSession,
      connection: "open",
      patterns: ["pulse", "rainbow"],
      pattern: "pulse",
      params: [...MOCK_PATTERNS.pulse, ...MOCK_PATTERNS.rainbow],
      accepted: {
        color: { h: 0, s: 1, v: 1 },
        bands: 3,
        invert: true,
        shape: "ramp",
      },
    });
  });

  it("draws one control per param, by kind, at the engine's values", () => {
    render(<EffectPanel client={client().client} />);
    expect(screen.getByLabelText("Color")).toHaveValue("#ff0000");
    const bands = screen.getByLabelText("Bands");
    expect(bands).toHaveAttribute("type", "range");
    expect(bands).toHaveAttribute("step", "1");
    expect(bands).toHaveValue("3");
    expect(screen.getByRole("switch", { name: "Invert" })).toBeChecked();
    expect(screen.getByLabelText("Shape")).toHaveValue("ramp");
    const speed = screen.getByLabelText("Speed");
    expect(speed).toHaveAttribute("max", "2");
    expect(speed).toHaveAttribute("step", "0.01");
    expect(screen.getByText("0.25 /s")).toBeInTheDocument();
  });

  it("sends each kind's value in its JSON form", async () => {
    const { client: c, setParam } = client();
    render(<EffectPanel client={c} />);
    fireEvent.change(screen.getByLabelText("Bands"), {
      target: { value: "5" },
    });
    await userEvent.click(screen.getByRole("switch", { name: "Invert" }));
    await userEvent.selectOptions(screen.getByLabelText("Shape"), "flat");
    fireEvent.change(screen.getByLabelText("Color"), {
      target: { value: "#0000ff" },
    });
    fireEvent.change(screen.getByLabelText("Speed"), {
      target: { value: "1.5" },
    });
    expect(setParam.mock.calls).toEqual([
      ["bands", 5],
      ["invert", false],
      ["shape", "flat"],
      ["color", { h: 240, s: 1, v: 1 }],
      ["speed", 1.5],
    ]);
  });

  it("follows each echo and snaps back on a refusal", () => {
    render(<EffectPanel client={client().client} />);
    fireEvent.change(screen.getByLabelText("Bands"), {
      target: { value: "6" },
    });
    expect(screen.getByLabelText("Bands")).toHaveValue("6");
    act(() => useSession.setState({ refusedAt: { bands: 1 } }));
    expect(screen.getByLabelText("Bands")).toHaveValue("3");
    act(() =>
      useSession.setState({
        accepted: { ...useSession.getState().accepted, shape: "flat" },
      }),
    );
    expect(screen.getByLabelText("Shape")).toHaveValue("flat");
  });

  it("resets every param to its default", async () => {
    const { client: c, setParam } = client();
    render(<EffectPanel client={c} />);
    await userEvent.click(screen.getByRole("button", { name: "Reset" }));
    expect(setParam).toHaveBeenCalledWith("color", { h: 200, s: 1, v: 1 });
    expect(setParam).toHaveBeenCalledWith("invert", false);
    expect(setParam).toHaveBeenCalledWith("shape", "ramp");
  });

  it("offers a palette's presets, sends a pick by label, and shows the gradient", async () => {
    const palette = decodeParam(zooRecord("palette"));
    if (palette?.kind !== "palette") throw new Error("no palette in the zoo");
    const own = {
      label: "",
      stops: [
        { at: 0, h: 0, s: 1, v: 1 },
        { at: 1, h: 240, s: 1, v: 1 },
      ],
    };
    useSession.setState({ params: [palette], accepted: { palette: own } });
    const { client: c, setParam } = client();
    render(<EffectPanel client={c} />);
    const menu = screen.getByLabelText("Palette");
    expect(menu).toHaveValue("");
    expect(screen.getByRole("option", { name: "Custom" })).toBeInTheDocument();
    // The DOM keeps the swatch's colors as rgb().
    expect(screen.getByTestId("palette-palette").style.backgroundImage).toBe(
      "linear-gradient(to right, rgb(255, 0, 0) 0%, rgb(0, 0, 255) 100%)",
    );
    await userEvent.selectOptions(menu, "ocean");
    expect(setParam.mock.calls).toEqual([["palette", "ocean"]]);
    expect(menu).toHaveValue("ocean");
    expect(screen.queryByRole("option", { name: "Custom" })).toBeNull();
    await userEvent.click(screen.getByRole("button", { name: "Reset" }));
    expect(setParam).toHaveBeenLastCalledWith("palette", palette.default);
  });
});
