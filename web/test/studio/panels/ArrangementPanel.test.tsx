import { expect, test, vi } from "vitest";
import { userEvent } from "vitest/browser";
import { render } from "vitest-browser-react";
import { mockCatalog } from "../../../src/studio/mocks/catalog";
import { ArrangementPanel } from "../../../src/studio/panels/ArrangementPanel";
import { DEFAULT_ARRANGEMENT, useDoc } from "../../../src/studio/store/doc";
import { mockApi } from "../mockApi";

test("an import the server rejects is refused, and the page and the draft stay", async () => {
  mockApi();
  useDoc.getState().load(DEFAULT_ARRANGEMENT, { mode: "draft" });
  const alert = vi.spyOn(window, "alert").mockImplementation(() => {});
  const screen = await render(<ArrangementPanel catalog={mockCatalog} rig={null} rigIsCurrent={false} />);
  const input = screen.container.querySelector<HTMLInputElement>('input[type="file"]');
  if (!input) throw new Error("no file input");
  const body = JSON.stringify({ format: "pewpew.arrangement", version: 1, groups: [{ id: "g", preset: "array" }] });
  await userEvent.upload(input, new File([body], "bad.json", { type: "application/json" }));
  await vi.waitFor(() => expect(alert).toHaveBeenCalled());
  expect(alert.mock.calls[0]?.[0]).toMatch(/^bad\.json was not imported: /);
  expect(useDoc.getState().history.present).toBe(DEFAULT_ARRANGEMENT);
  await expect.element(screen.getByRole("button", { name: /^inner/ })).toBeInTheDocument();
  alert.mockRestore();
});
