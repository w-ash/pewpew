import { expect, test, vi } from "vitest";
import { WireStore } from "../../src/wire/store";
import { OPS } from "../fixtures/describe";
import { board, greeting, health, hello, refused, AURA } from "../fixtures/messages";

function storeWithZoo() {
  const store = new WireStore();
  for (const msg of greeting()) store.receive(msg);
  const p = (name: string) => store.getState().params.find((x) => x.name === name)!;
  return { store, p };
}

test("the greeting brings the map, the display gamma, the params and their values", () => {
  const { store, p } = storeWithZoo();
  const s = store.getState();
  expect(s.connected).toBe(true);
  expect(s.gamma).toBe(2.2);
  expect(s.params.map((x) => x.kind)).toEqual(["float", "int", "bool", "choice", "color", "palette"]);
  expect(store.value(p("color"))).toEqual({ h: 120, s: 1, v: 1 });
  expect(store.value(p("palette"))).toMatchObject({ label: "ember" });
  expect(s.map?.n).toBe(2);
});

test("a hello drops what the last connection said", () => {
  const { store, p } = storeWithZoo();
  const color = p("color");
  store.receive({ type: "status", error: "boom", source: "render", path: "layers.base.zoo" });
  store.receive(hello());
  expect(store.getState()).toMatchObject({ params: [], aura: null, error: null, session: 2 });
  expect(store.value(color)).toBeUndefined();
});

test("a page whose server sends no hello opens the state itself, on its own gamma and no map", () => {
  const { store } = storeWithZoo();
  store.opened({ gamma: 2.2, map: null });
  expect(store.getState()).toMatchObject({ connected: true, gamma: 2.2, map: null, params: [], aura: null, session: 2 });
});

test("an echo wakes only the params whose value changed, by kind", () => {
  const { store, p } = storeWithZoo();
  const color = vi.fn(), level = vi.fn();
  store.subscribeParam("color", color);
  store.subscribeParam("level", level);
  const before = store.value(p("color"));
  store.receive({ type: "params", values: { level: 0.5, color: { h: 120, s: 1, v: 1 } } });
  expect(color).not.toHaveBeenCalled();
  expect(level).not.toHaveBeenCalled();
  expect(store.value(p("color"))).toBe(before);
  store.receive({ type: "params", values: { level: 0.7, color: { h: 120, s: 1, v: 1 } } });
  expect(level).toHaveBeenCalledTimes(1);
  expect(color).not.toHaveBeenCalled();
  expect(store.value(p("level"))).toBe(0.7);
});

test("a value the param cannot hold is ignored", () => {
  const { store, p } = storeWithZoo();
  store.receive({ type: "params", values: { shape: "nope", bands: 2.5 } });
  expect(store.value(p("shape"))).toBe("ramp");
  expect(store.value(p("bands"))).toBe(2);
});

test("a declare keeps the values of the params it keeps", () => {
  const { store } = storeWithZoo();
  store.receive({ type: "params", values: { level: 0.9 } });
  const records = (OPS.zoo_test ?? []).filter((r) => r.name !== "invert");
  store.receive({ type: "declare", params: records });
  const params = store.getState().params;
  expect(params.map((x) => x.name)).not.toContain("invert");
  expect(store.value(params.find((x) => x.name === "level")!)).toBe(0.9);
});

test("refusals are routed by control, and a set's by name", () => {
  const { store } = storeWithZoo();
  store.receive(refused("set", "level must be within 0.0..1.0, got 2.0", "level"));
  store.receive(refused("recall", "no look named x"));
  const s = store.getState();
  expect(s.refusals.set).toMatchObject({ name: "level", seq: 1 });
  expect(s.refusals.recall).toMatchObject({ name: null, seq: 2, reason: "no look named x" });
  expect(s.paramRefusals.level).toBe(s.refusals.set);
});

test("a status, an aura and a health replace their state whole", () => {
  const { store } = storeWithZoo();
  store.receive({ type: "status", error: "boom", source: "render", path: "layers.base.zoo" });
  expect(store.getState().error).toEqual({ text: "boom", source: "render", path: "layers.base.zoo" });
  store.receive({ type: "status", error: null, source: null, path: null });
  expect(store.getState().error).toBeNull();
  store.receive({ type: "aura", ...AURA, master: 0.1 });
  expect(store.getState().aura?.master).toBe(0.1);
  store.receive({ type: "health", ...health([board({})]) });
  store.receive({ type: "health", ...health([]) });
  expect(store.getState().health?.boards).toEqual([]);
});

test("a close drops the engine's error, health and frame clock", () => {
  const { store } = storeWithZoo();
  store.receive({ type: "status", error: "boom", source: "reload", path: null });
  store.receiveFrame({ t: 1, seq: 1, rgb: new Uint8Array(6) }, 123);
  store.disconnected();
  expect(store.getState()).toMatchObject({ connected: false, error: null, health: null });
  expect(store.lastFrameAt).toBe(0);
});

test("a layout replaces the map and drops the old frame", () => {
  const { store } = storeWithZoo();
  store.receiveFrame({ t: 1, seq: 1, rgb: new Uint8Array(6) }, 1);
  store.receive({ type: "layout", n: 1, total: 1, positions: [[0, 0, 0]], is3d: false, room: null });
  expect(store.getState().map?.n).toBe(1);
  expect(store.getFrame()).toBeNull();
});

test("a mod wakes only the knobs whose live value changed, came or went, and a hello drops them", () => {
  const { store } = storeWithZoo();
  const level = vi.fn(), hue = vi.fn();
  store.subscribeMod("level", level);
  store.subscribeMod("color.h", hue);
  store.receive({ type: "mod", values: { level: 0.5, "color.h": 30 } });
  store.receive({ type: "mod", values: { level: 0.6, "color.h": 30 } });
  expect([level.mock.calls.length, hue.mock.calls.length]).toEqual([2, 1]);
  expect([store.mod("level"), store.mod("color.h")]).toEqual([0.6, 30]);
  store.receive({ type: "mod", values: { level: 0.6 } });
  expect([level.mock.calls.length, hue.mock.calls.length, store.mod("color.h")]).toEqual([2, 2, undefined]);
  store.receive(hello());
  expect([level.mock.calls.length, store.mod("level")]).toEqual([3, undefined]);
});
