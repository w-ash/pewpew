import { expect, test, vi } from "vitest";
import { userEvent } from "vitest/browser";
import { render } from "vitest-browser-react";
import { mockCatalog } from "../../../src/studio/mocks/catalog";
import { ArrangementPanel } from "../../../src/studio/panels/ArrangementPanel";
import { DEFAULT_ARRANGEMENT, useDoc } from "../../../src/studio/store/doc";
import type { Arrangement, CompiledRig } from "../../../src/studio/api/types";
import { threeBarRig } from "../fixtures/rig";
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

test("an aimed fixture's pose comes from the compile of this arrangement only, never an older one", async () => {
  const aimed: Arrangement = {
    ...DEFAULT_ARRANGEMENT,
    groups: [],
    fixtures: [{ id: "a", type: "clen-rgbw-bar-1m", pose: { aim: { axis: [1, 0, 0] } } }],
  };
  useDoc.getState().load(aimed, { mode: "draft" });
  useDoc.getState().select({ kind: "fixture", id: "a" });
  const rig: CompiledRig = { ...threeBarRig, fixtures: [{ ...threeBarRig.fixtures[1]!, id: "a", group: null }] };
  const screen = await render(<ArrangementPanel catalog={mockCatalog} rig={rig} rigIsCurrent={false} />);
  await expect.element(screen.getByRole("button", { name: "Flip" })).toBeDisabled();
  await expect.element(screen.getByText(/This fixture's rotation is an/)).toBeInTheDocument();
  await screen.rerender(<ArrangementPanel catalog={mockCatalog} rig={rig} rigIsCurrent />);
  await expect.element(screen.getByRole("button", { name: "Flip" })).toBeEnabled();
  await expect.element(screen.getByRole("spinbutton", { name: "y" })).toHaveValue("1.2000");
});

test("a group explodes into the members the compile names by id, with or without their group field", async () => {
  useDoc.getState().load(DEFAULT_ARRANGEMENT, { mode: "draft" });
  useDoc.getState().select({ kind: "group", id: "inner" });
  const { group: _group, ...member } = threeBarRig.fixtures[0]!;
  const rig: CompiledRig = { ...threeBarRig, fixtures: [{ ...member, id: "inner/0" }] };
  const screen = await render(<ArrangementPanel catalog={mockCatalog} rig={rig} rigIsCurrent />);
  await screen.getByRole("button", { name: "Explode" }).click();
  const present = useDoc.getState().history.present;
  expect(present.groups.map((g) => g.id)).toEqual(["outer"]);
  expect(present.fixtures.map((f) => f.id)).toEqual(["inner-0"]);
});
