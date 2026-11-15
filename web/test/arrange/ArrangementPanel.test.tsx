import { expect, test, vi } from "vitest";
import { userEvent } from "vitest/browser";
import { render } from "vitest-browser-react";
import { useDoc } from "../../src/arrange/doc";
import { DocPanel, RINGS as DEFAULT_ARRANGEMENT } from "./fixtures";
import type { Arrangement } from "../../src/arrange/types";
import type { CompiledFixture, CompiledRig } from "../../src/rig/types.gen";
import { partsCatalog, threeBarRig } from "../rig3d/rig";

test("an import its check refuses is refused, and the page and the draft stay", async () => {
  useDoc.getState().load(DEFAULT_ARRANGEMENT);
  const alert = vi.spyOn(window, "alert").mockImplementation(() => {});
  const check = vi.fn(async () => "groups[0]: no type");
  const screen = await render(<DocPanel catalog={partsCatalog} rig={null} rigIsCurrent={false} checkImport={check} />);
  const input = screen.container.querySelector<HTMLInputElement>('input[type="file"]');
  if (!input) throw new Error("no file input");
  const body = JSON.stringify({ format: "pewpew.arrangement", version: 1, groups: [{ id: "g", preset: "array" }] });
  await userEvent.upload(input, new File([body], "bad.json", { type: "application/json" }));
  await vi.waitFor(() => expect(alert).toHaveBeenCalled());
  expect(alert.mock.calls[0]?.[0]).toBe("bad.json was not imported: groups[0]: no type.");
  expect(check).toHaveBeenCalledOnce();
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
  useDoc.getState().load(aimed);
  useDoc.getState().select({ kind: "fixture", id: "a" });
  const rig: CompiledRig = { ...threeBarRig, fixtures: [{ ...threeBarRig.fixtures[1]!, id: "a", group: null }] };
  const screen = await render(<DocPanel catalog={partsCatalog} rig={rig} rigIsCurrent={false} />);
  await expect.element(screen.getByRole("button", { name: "Flip" })).toBeDisabled();
  await expect.element(screen.getByText(/This fixture's rotation is an/)).toBeInTheDocument();
  await screen.rerender(<DocPanel catalog={partsCatalog} rig={rig} rigIsCurrent />);
  await expect.element(screen.getByRole("button", { name: "Flip" })).toBeEnabled();
  await expect.element(screen.getByRole("spinbutton", { name: "y" })).toHaveValue("1.2000");
});

test("a group explodes into the members the compile names by id, with or without their group field", async () => {
  useDoc.getState().load(DEFAULT_ARRANGEMENT);
  useDoc.getState().select({ kind: "group", id: "inner" });
  const { group: _group, ...member } = threeBarRig.fixtures[0]!;
  // A fixture of a rig from before the group field.
  const rig: CompiledRig = { ...threeBarRig, fixtures: [{ ...member, id: "inner/0" } as CompiledFixture] };
  const screen = await render(<DocPanel catalog={partsCatalog} rig={rig} rigIsCurrent />);
  await screen.getByRole("button", { name: "Explode" }).click();
  const present = useDoc.getState().history.present;
  expect(present.groups.map((g) => g.id)).toEqual(["outer"]);
  expect(present.fixtures.map((f) => f.id)).toEqual(["inner-0"]);
});

test("without a check, an imported arrangement is an edit like any other, which undo takes back", async () => {
  useDoc.getState().load(DEFAULT_ARRANGEMENT);
  const screen = await render(<DocPanel catalog={partsCatalog} rig={null} rigIsCurrent={false} />);
  const input = screen.container.querySelector<HTMLInputElement>('input[type="file"]');
  if (!input) throw new Error("no file input");
  const body = JSON.stringify({ format: "pewpew.arrangement", version: 1, fixtures: [{ id: "x", type: "t" }] });
  await userEvent.upload(input, new File([body], "one.json", { type: "application/json" }));
  await vi.waitFor(() => expect(useDoc.getState().history.present.fixtures.map((f) => f.id)).toEqual(["x"]));
  await screen.getByRole("button", { name: "Undo" }).click();
  expect(useDoc.getState().history.present).toBe(DEFAULT_ARRANGEMENT);
});

test("picking a fixture from a long list brings its form into view", async () => {
  const many: Arrangement = {
    ...DEFAULT_ARRANGEMENT,
    groups: [],
    fixtures: Array.from({ length: 60 }, (_, i) => ({ id: `f${i + 1}`, type: "clen-rgbw-bar-1m" })),
  };
  useDoc.getState().load(many);
  useDoc.getState().select(null);
  const screen = await render(
    <div className="scroller" style={{ height: 400, overflow: "auto" }} data-testid="slot">
      <DocPanel catalog={partsCatalog} rig={null} rigIsCurrent={false} />
    </div>,
  );
  const slot = screen.getByTestId("slot").element();
  await screen.getByRole("button", { name: /^f60/ }).click();
  const form = screen.getByRole("heading", { name: "Selected · f60" }).element().getBoundingClientRect();
  const box = slot.getBoundingClientRect();
  expect(form.top).toBeGreaterThanOrEqual(box.top - 1);
  expect(form.top).toBeLessThan(box.bottom);
});

test("Add › Bar puts the new bar in the plane of a flat rig, not upright at the origin", async () => {
  const flat: Arrangement = {
    ...DEFAULT_ARRANGEMENT,
    groups: [],
    fixtures: [{ id: "a", type: "clen-rgbw-bar-1m", pose: { aim: { axis: [1, 0, 0] } } }],
  };
  useDoc.getState().load(flat);
  const along = { ...threeBarRig.fixtures[0]!, id: "a", group: null, matrix: [0, -1, 0, 0, 1, 0, 0, 0, 0, 0, 1, 0, 2, 0, -1, 1] };
  const rig: CompiledRig = { ...threeBarRig, fixtures: [along] };
  const screen = await render(<DocPanel catalog={partsCatalog} rig={rig} rigIsCurrent />);
  await screen.getByRole("button", { name: "Bar" }).click();
  const added = useDoc.getState().history.present.fixtures.at(-1)!;
  expect(added.pose?.position_m).toEqual([2, 0, -1.1]);
});
