import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { mockCatalog } from "@/mocks/catalog";
import { DEFAULT_ARRANGEMENT, useDoc } from "@/store/doc";
import { ArrangementPanel } from "./ArrangementPanel";

describe("ArrangementPanel import", () => {
  afterEach(() => vi.restoreAllMocks());

  it("refuses a file the server rejects and keeps the page and the draft", async () => {
    useDoc.getState().load(DEFAULT_ARRANGEMENT, { mode: "draft" });
    const alert = vi.spyOn(window, "alert").mockImplementation(() => {});
    const { container } = render(
      <ArrangementPanel
        catalog={mockCatalog}
        rig={null}
        rigIsCurrent={false}
      />,
    );
    const input =
      container.querySelector<HTMLInputElement>('input[type="file"]');
    if (!input) throw new Error("no file input");
    const body = JSON.stringify({
      format: "pewpew.arrangement",
      version: 1,
      groups: [{ id: "g", preset: "array" }],
    });
    await userEvent.upload(
      input,
      new File([body], "bad.json", { type: "application/json" }),
    );
    await waitFor(() => expect(alert).toHaveBeenCalled());
    expect(alert.mock.calls[0][0]).toMatch(/^bad\.json was not imported: /);
    expect(useDoc.getState().history.present).toBe(DEFAULT_ARRANGEMENT);
    expect(screen.getByRole("button", { name: /^inner/ })).toBeInTheDocument();
  });
});
