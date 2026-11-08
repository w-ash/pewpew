// The wire contract with the engine: tests/goldens/wire.json holds messages a
// real preview sent (tests/test_wire_contract.py). Each key list below is
// checked against its type by the compiler, and against the golden here, so a
// key renamed on either side fails.
import { expect, test } from "vitest";
import wire from "../../../tests/goldens/wire.json";
import type {
  AwakeHealth, BoardHealth, FoundBoard, HealthState, LoopHealth, ScanState,
} from "../../src/health/health";
import { chip, healthRows, scanNote } from "../../src/health/health";
import { decodeParam, readValue } from "../../src/params/kinds";
import { makeLayout, planUrl, roomOf, type RoomFixture, type RoomPlan, type RoomShape } from "../../src/room/layout";
import type { Held, LastEvent, TriggersState } from "../../src/aura/triggers";
import type { RigReport, Totals } from "../../src/rig/types.gen";
import { cueText, lastText } from "../../src/aura/triggers";
import type { LookItem, LooksState } from "../../src/aura/looks";
import { lookStatus } from "../../src/aura/looks";
import { nowOf } from "../../src/aura/aura";
import { newLayer, offReason, shelve, type BlendNote, type Card, type Example, type Shelf } from "../../src/stack/catalog";
import { frontFirst, isSignal, movedBy, sectionOf } from "../../src/stack/stack";
import type { LayerItem, NodeItem, RouteItem, SignalItem, StackState } from "../../src/stack/stack";
import {
  asServerMessage, encodeFrame, parseFrame, parseTyped, type ClientMessage, type Control, type RigController, type RigControllerSlice,
  type RigFixture, type RigIssue, type RigPlan, type RigShape, type RigSlice, type ServerMessage,
} from "../../src/wire/protocol";
import { canArrange, WireStore } from "../../src/wire/store";
import {
  first, GREETING, LATER, SESSION_EXPORTED, SESSION_GREETING, SESSION_POWER, SESSION_REFUSED,
} from "../fixtures/messages";

type Message<T extends ServerMessage["type"]> = Extract<ServerMessage, { type: T }>;

/** A key list for `T`: the compiler holds it to exactly `T`'s keys. */
const keys = <T>(r: Readonly<Record<keyof T, true>>): string[] => Object.keys(r).sort();

interface Shape {
  readonly keys: string[];
  /** Keys of `keys` a message may leave out. */
  readonly optional?: readonly string[];
  /** The shapes of fields that hold objects, or arrays of them. */
  readonly fields?: Readonly<Record<string, Shape>>;
}

const ROOM: Shape = {
  keys: keys<RoomShape>({ scale: true, fixtures: true, fixture_of: true, plan: true }),
  fields: {
    fixtures: { keys: keys<RoomFixture>({ id: true, pitch: true, start: true, end: true, input: true }) },
    plan: { keys: keys<Extract<RoomPlan, { url: string }>>({ corner: true, unit: true, url: true }) },
  },
};
const MAP = { n: true, total: true, positions: true, is3d: true, room: true, rig: true } as const;
const RIG: Shape = {
  keys: keys<RigShape>({
    catalog_digest: true, frame: true, scale: true, shift: true, plan: true, fixtures: true, types: true,
    controllers: true, slices: true, controller_slices: true, issues: true,
  }),
  fields: {
    plan: { keys: keys<Extract<RigPlan, { url: string }>>({ corner_m: true, meters_per_pixel: true, url: true }) },
    fixtures: {
      keys: keys<RigFixture>({
        id: true, type_id: true, base_type_id: true, group: true, matrix: true, pixel_start: true,
        pixel_count: true, controller: true, output: true, tags: true, dims: true, attachments: true,
        attachment_matrices: true,
      }),
    },
    controllers: { keys: keys<RigController>({ id: true, profile: true, host: true, port: true }) },
    slices: {
      keys: keys<RigSlice>({
        controller: true, output: true, chain: true, start: true, count: true, led_type: true, color_order: true,
      }),
    },
    controller_slices: { keys: keys<RigControllerSlice>({ controller: true, start: true, count: true }) },
    issues: { keys: keys<RigIssue>({ level: true, code: true, message: true, ref: true }) },
  },
};

const SHAPES: { readonly [T in ServerMessage["type"]]: Shape } = {
  hello: {
    keys: keys<Message<"hello">>({ type: true, ...MAP, display_gamma: true, build: true, capabilities: true }),
    fields: { room: ROOM, rig: RIG },
  },
  layout: { keys: keys<Message<"layout">>({ type: true, ...MAP }), fields: { room: ROOM, rig: RIG } },
  status: { keys: keys<Message<"status">>({ type: true, error: true, source: true, path: true }) },
  declare: { keys: keys<Message<"declare">>({ type: true, params: true }) },
  params: { keys: keys<Message<"params">>({ type: true, values: true }) },
  mod: { keys: keys<Message<"mod">>({ type: true, values: true }) },
  aura: {
    keys: keys<Message<"aura">>({
      type: true, stack: true, fading: true, progress: true, master: true, cap: true,
      blackout: true, looks: true, triggers: true,
    }),
    fields: {
      stack: {
        keys: keys<StackState>({ layers: true, signals: true, routes: true, front: true, dims: true }),
        fields: {
          layers: {
            keys: keys<LayerItem>({ id: true, nodes: true }),
            fields: { nodes: { keys: keys<NodeItem>({ id: true, op: true, label: true, in: true }) } },
          },
          signals: { keys: keys<SignalItem>({ id: true, op: true, label: true, in: true, range: true }) },
          routes: { keys: keys<RouteItem>({ source: true, path: true, depth: true }) },
        },
      },
      looks: {
        keys: keys<LooksState>({
          items: true, favorites: true, current: true, changed: true, fading: true, progress: true, pending: true, cycling: true, idle: true, dwell: true,
          made: true, offered: true, saved: true,
        }),
        fields: { items: { keys: keys<LookItem>({ name: true, cycle: true, fade: true }) } },
      },
      triggers: {
        keys: keys<TriggersState>({ armed: true, names: true, cues: true, held: true, last: true }),
        fields: {
          held: { keys: keys<Held>({ trigger: true, look: true, until: true }) },
          last: { keys: keys<LastEvent>({ name: true, fired: true, reason: true, error: true }) },
        },
      },
    },
  },
  health: {
    keys: keys<Message<"health">>({ type: true, level: true, boards: true, sent_fps: true, loop: true, awake: true, scan: true }),
    fields: {
      boards: {
        keys: keys<BoardHealth>({
          host: true, board: true, address: true, mac: true, lost: true, fix: true, level: true, reasons: true, live: true,
          lip: true, from_us: true, fps: true, count: true, expected: true, rssi: true, channel: true, uptime: true,
          freeheap: true, ver: true, reboots: true, reset_reason: true,
        }),
      },
      loop: { keys: keys<LoopHealth>({ level: true, fps: true, target: true, skips: true, watchdog: true, fix: true }) },
      awake: { keys: keys<AwakeHealth>({ level: true, requested: true, held: true, detail: true, fix: true }) },
      scan: {
        keys: keys<ScanState>({ running: true, subnet: true, found: true, error: true }),
        fields: {
          found: {
            keys: keys<FoundBoard>({
              address: true, mac: true, name: true, ver: true, live: true, lm: true, lip: true, board: true, at: true,
            }),
          },
        },
      },
    },
  },
  catalog: {
    keys: keys<Message<"catalog">>({ type: true, cards: true, blends: true }),
    fields: {
      cards: {
        keys: keys<Card>({
          kind: true, name: true, label: true, summary: true, sig: true, dims: true, fix: true, examples: true,
        }),
        fields: { examples: { keys: keys<Example>({ py: true, json: true, dims: true }) } },
      },
      blends: { keys: keys<BlendNote>({ name: true, label: true, doc: true, black: true }) },
    },
  },
  power: { keys: keys<Message<"power">>({ type: true, watts: true, uncapped_watts: true }) },
  // The arrangement is the file's own JSON, which the engine checks (rig/models.py).
  arrangement: { keys: keys<Message<"arrangement">>({ type: true, arrangement: true, base: true }) },
  report: {
    keys: keys<Message<"report">>({ type: true, issues: true, report: true }),
    fields: {
      issues: RIG.fields!.issues!,
      report: {
        keys: keys<RigReport>({
          target_fps: true, limits: true, totals: true, controllers: true, outputs: true, hops: true, feeds: true,
          psus: true, bom: true, basis: true, notes: true,
        }),
        fields: {
          totals: {
            keys: keys<Totals>({
              fixtures: true, pixels: true, worst_w: true, worst_a: true, rgb_worst_w: true, rgb_worst_a: true,
              capped_w: true, capped_a: true, controllers: true, psus: true, feeds: true,
            }),
          },
        },
      },
    },
  },
  refused: {
    keys: keys<Required<Message<"refused">>>({
      type: true, control: true, name: true, id: true, reason: true, issues: true, arrangement: true, base: true,
    }),
    optional: ["issues", "arrangement", "base"],
    fields: { issues: RIG.fields!.issues! },
  },
  ack: { keys: keys<Message<"ack">>({ type: true, id: true, control: true }) },
  exported: { keys: keys<Message<"exported">>({ type: true, id: true, file: true, gallery: true }) },
};

type Fields<K extends Control> = Readonly<Record<Exclude<keyof Extract<ClientMessage, { type: K }>, "type">, true>>;

const CONTROLS: { readonly [K in Control]: Fields<K> } = {
  set: { name: true, value: true },
  add_layer: { layer: true, below: true },
  remove_layer: { lid: true },
  move_layer: { lid: true, to: true },
  front: { paths: true },
  master: { value: true },
  blackout: { on: true },
  recall: { name: true, fade: true },
  look: { look: true, fade: true },
  surprise: { seed: true },
  vary: { strength: true, seed: true },
  keep: {},
  save: { name: true, fade: true, master: true },
  delete: { name: true },
  rename: { name: true, to: true },
  cycle: { name: true, on: true },
  favorite: { name: true, on: true },
  fade: { name: true, fade: true },
  arm: { on: true },
  fire: { name: true, value: true },
  scan: {},
  rebind: { board: true, address: true },
  blink: { fixture: true },
  arrange: { arrangement: true, base: true },
  export: { looks: true, share: true },
  pause: {},
  resume: {},
};

/** The controls only a Gallery session takes, which the engine's golden does not list. */
const GALLERY_ONLY: readonly Control[] = ["pause", "resume"];

/** Where `value` has other keys than `shape`, recording each shape a value reached in `seen`. */
function mismatches(where: string, value: unknown, shape: Shape, seen: Set<Shape>): string[] {
  if (value === null || value === undefined) return [];
  if (Array.isArray(value)) return value.flatMap((v, i) => mismatches(`${where}[${i}]`, v, shape, seen));
  seen.add(shape);
  const record = value as Record<string, unknown>;
  const found = Object.keys(record).sort();
  const expected = shape.keys.filter((k) => Object.hasOwn(record, k) || !shape.optional?.includes(k));
  const out = found.join() === expected.join() ? [] : [`${where} has ${found.join(", ")}; the page reads ${shape.keys.join(", ")}`];
  for (const [key, sub] of Object.entries(shape.fields ?? {})) out.push(...mismatches(`${where}.${key}`, record[key], sub, seen));
  return out;
}

function allShapes(shape: Shape): Shape[] {
  return [shape, ...Object.values(shape.fields ?? {}).flatMap(allShapes)];
}

/** The Gallery session's messages the golden has (session.json). */
const SESSION = [...SESSION_GREETING, SESSION_POWER, ...Object.values(SESSION_REFUSED), SESSION_EXPORTED];

test("every message in wire.json and the session's power and export has the keys the page's types give, and every shape is in it", () => {
  const messages = [...GREETING, ...LATER, SESSION_POWER, SESSION_EXPORTED];
  const seen = new Set<Shape>();
  const found = messages.flatMap((msg, i) => mismatches(`${msg.type}#${i}`, msg, SHAPES[msg.type], seen));
  expect(found).toEqual([]);
  const types = new Set(messages.map((m) => m.type));
  expect(Object.keys(SHAPES).filter((t) => !types.has(t as ServerMessage["type"]))).toEqual([]);
  expect(Object.values(SHAPES).flatMap(allShapes).filter((s) => !seen.has(s))).toEqual([]);
});

test("every message of a Gallery session has the keys the page's types give, and its hello asks for the Gallery's page", () => {
  const found = SESSION.flatMap((msg, i) => mismatches(`${msg.type}#${i}`, msg, SHAPES[msg.type], new Set()));
  expect(found).toEqual([]);
  expect(Object.values(SESSION_REFUSED).map((r) => r.control)).toEqual(["session", "message", "look"]);
  const hello = SESSION_GREETING[0];
  expect(hello?.type === "hello" && hello.capabilities).toEqual(expect.arrayContaining(["export", "pause", "gallery"]));
  expect(hello?.type === "hello" && hello.capabilities).not.toContain("arrange");
  expect(hello?.type === "hello" && hello.rig).toBeTruthy();
  expect(SESSION.map((m) => m.type)).not.toEqual(expect.arrayContaining(["health"]));
  const looks = SESSION_GREETING.find((m) => m.type === "aura");
  expect(looks?.type === "aura" && looks.looks).toBeTruthy();
});

test("an export is answered with the file, a share with the Gallery to post it to, and the store keeps the answer", () => {
  const exported = SESSION_EXPORTED;
  expect(exported.gallery).toBeNull();
  expect(exported.file).toMatchObject({ version: 4 });
  const store = new WireStore();
  store.receive(asServerMessage(parseTyped(JSON.stringify(exported)))!);
  expect(store.exported).toEqual(exported);
  const share = first("exported", LATER);
  expect(share.gallery).toMatch(/^https?:\/\/[^/]+$/);
  expect(share.file).toMatchObject({ format: "pewpew.share", version: 1 });
});

test("a frame's bytes are the <fI header, little-endian, then the RGB the wire reads", () => {
  const frame = parseFrame(encodeFrame(2.25, 0x01020304, new Uint8Array([1, 2, 3, 4, 5, 6])));
  expect(frame.t).toBe(2.25);
  expect(frame.seq).toBe(0x01020304);
  expect([...frame.rgb]).toEqual([1, 2, 3, 4, 5, 6]);
});

test("every control the engine takes is a message the page can send, with the same fields", () => {
  const engines = Object.entries(CONTROLS).filter(([name]) => !GALLERY_ONLY.includes(name as Control));
  const page = Object.fromEntries(engines.map(([name, fields]) => [name, Object.keys(fields).sort()]));
  const engine = Object.fromEntries(Object.entries(wire.controls).map(([name, fields]) => [name, [...fields].sort()]));
  expect(page).toEqual(engine);
});

test("every message decodes through the wire and the store, and reads through the domain", () => {
  const store = new WireStore();
  for (const msg of [...GREETING, ...LATER, SESSION_POWER]) {
    const parsed = asServerMessage(parseTyped(JSON.stringify(msg)));
    expect(parsed).toEqual(msg);
    store.receive(parsed!);
  }
  const declared = first("declare").params.map(decodeParam);
  expect(store.getState().params).toEqual(declared);
  const values = first("params").values;
  for (const p of declared) expect(store.value(p)).toEqual(readValue(p, values[p.name]));

  const aura = store.getState().aura!;
  expect(aura.stack.layers.map((l) => [l.id, l.nodes.map((n) => [n.op, n.label])])).toEqual([["base", [["zoo_test", "Zoo"]]]]);
  expect(declared.map((p) => p.name)).toContain("layers.base.opacity");
  const { stack } = first("aura"); // the greeting's look, before the held trigger's
  expect(stack.signals.map((n) => [n.label, n.range])).toEqual([["LFO", [-1, 1]], ["Macro", [0, 1]]]);
  expect(frontFirst(declared, stack.front).front.map((p) => p.name)).toEqual(stack.front);
  expect(movedBy(stack.routes, "layers.base.zoo.color", undefined, stack.signals)).toBe("modulated by ‘macro’ on h +60");
  expect(movedBy(stack.routes, "layers.base.zoo.level", undefined, stack.signals)).toBe("modulated by ‘breath’ ±0.2");
  expect(store.mod("layers.base.zoo.level")).toBe(first("mod").values["layers.base.zoo.level"]);
  expect(declared.filter(isSignal).map((p) => sectionOf(p, stack.layers, stack.signals)?.title)).toEqual([
    "breath · LFO", "breath · LFO", "breath · LFO", "macro · macro",
  ]);
  expect(nowOf(aura)).toEqual({ name: "cool", changed: false, draft: false, master: "80%" });
  expect(lookStatus(aura.looks!, aura.triggers, "warm")).toMatchObject({ returnsTo: true, held: false });
  expect(cueText("door", aura.triggers!.held, 0)).toBe("door · 9s");
  expect(lastText(aura.triggers!.last).text).toBe("door fired");
  expect(store.getState().error).toEqual({
    text: "layers.base.render raised: RuntimeError: boom", source: "render", path: "layers.base",
  });
  expect(store.getState().refusals.set).toMatchObject({
    name: "layers.base.zoo.level", reason: "layers.base.zoo.level must be within 0.0..1.0, got 3.0",
  });
  expect(store.getState().power).toEqual({ watts: SESSION_POWER.watts, uncapped_watts: SESSION_POWER.uncapped_watts });
  expect(store.getState().refusals.look).toMatchObject({ name: "layers.base.osc.freq" });
  expect(store.getState().refusals.add_layer).toMatchObject({ name: "layers.osc.osc.freq" });
  // The last arrange refusal is of a stale file: it carries the engine's arrangement, which the store takes.
  const arrangeRefusals = LATER.filter((m) => m.type === "refused" && m.control === "arrange");
  expect(arrangeRefusals.map((m) => m.type === "refused" && m.issues?.map((i) => i.code))).toEqual([["unresolved_ref"], undefined]);
  expect(store.getState().refusals.arrange).toMatchObject({ reason: "the layout changed; showing the current one" });
  expect(store.getState().capabilities).toContain("arrange");
  expect(store.getState().arrangement).toEqual(first("arrangement").arrangement);
  expect(store.getState().report?.report?.totals.pixels).toBe(2);
  expect(canArrange(store.getState())).toBe(true); // the later layout is a rig
  expect(store.getState().arrangementBase).toBe(first("arrangement").base);
  // A room map file saved over the arrangement: the engine offers no layout to edit.
  store.receive({ type: "arrangement", arrangement: null, base: null });
  expect(canArrange(store.getState())).toBe(false);

  const catalog = store.getState().catalog!;
  const shelfOf = (c: Card): Shelf | undefined => [...shelve(catalog.cards)].find(([, held]) => held.some((h) => h.card === c))?.[0];
  expect(catalog.cards.map((c) => [c.name, shelfOf(c), offReason(c, stack.dims)])).toEqual([
    ["osc", "sources", null], ["kaleid", "space", "a strip has no plane to fold; use mirror along the strip"],
  ]);
  expect(newLayer(catalog.cards[0]!.examples[0]!)).toMatchObject({ out: "osc", blend: "screen", opacity: 0.7 });

  const health = store.getState().health as HealthState;
  expect(chip(health, 0).text).toBe("1 ok");
  expect(healthRows(health, 0, null)[0]!.name).toBe("A · 192.168.1.50");
  expect(scanNote(health.scan)).toBe("2 WLED boards in 192.168.1.0/24");

  const map = store.getState().map!;
  expect(planUrl(roomOf(map))).toBe("/plan?v=1");
  expect(makeLayout(map, { width: 400, height: 400, dpr: 1 }, null).fixtures.map((f) => f.id)).toEqual(["a", "b"]);
});

test("a refusal that comes before the hello survives it, and one from the last connection does not", () => {
  const store = new WireStore();
  store.receive({ type: "refused", control: "session", name: null, id: null, reason: "server full" });
  for (const msg of SESSION_GREETING) store.receive(msg);
  expect(store.getState().refusals.session).toMatchObject({ reason: "server full" });
  store.receive({ type: "refused", control: "message", name: null, id: null, reason: "too large" });
  store.disconnected();
  for (const msg of SESSION_GREETING) store.receive(msg);
  expect(store.getState().refusals).toEqual({});
});
