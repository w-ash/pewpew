import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { DEFAULT_ARRANGEMENT, useDoc } from "@/store/doc";
import { SharePanel } from "./SharePanel";

describe("SharePanel copy", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("selects the link instead of claiming a copy when there is no clipboard", async () => {
    useDoc.getState().load(DEFAULT_ARRANGEMENT, { mode: "shared", id: "X" });
    vi.stubGlobal("navigator", { ...navigator, clipboard: undefined });
    render(<SharePanel />);
    await userEvent.click(screen.getByRole("button", { name: "Copy link" }));
    expect(
      screen.getByRole("button", { name: /^Selected/ }),
    ).toBeInTheDocument();
    expect(screen.getByTestId("share-link")).toHaveFocus();
  });
});
