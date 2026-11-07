/**
 * A stand-in aura for the mock session: it runs no effect, but it keeps a
 * look's layers, knobs and modulators as the engine declares them, so the
 * look editor has something to edit. Each record is shaped after the real
 * ones in tests/goldens/wire.json (the zoo's float and int, a layer's mix)
 * and the add-layer cards are the golden's. Every number an op or a signal
 * is given becomes a knob; other args are kept, never knobs.
 */
import type { LookDocument } from "../api/types";

type Json = Record<string, unknown>;
type Message = { type: string } & Json;

interface Golden {
  greeting: Message[];
}

/** Read through a glob, so a build without tests/ (the Dockerfile's) passes. */
const found = import.meta.glob<Golden>("../../../../tests/goldens/wire.json", {
  eager: true,
  import: "default",
});

function golden(type: string): Message {
  const wire = Object.values(found)[0];
  const msg = wire?.greeting.find((m) => m.type === type);
  if (!msg) throw new Error(`no ${type} in tests/goldens/wire.json`);
  return msg;
}

function goldenParam(name: string): Json {
  const params = golden("declare").params as Json[];
  const record = params.find((p) => p.name === name);
  if (!record) throw new Error(`no ${name} in the golden's declare`);
  return record;
}

const label = (id: string) => id.charAt(0).toUpperCase() + id.slice(1);

/** A knob at `name` starting at `value`, after the golden's: an int for a whole number, else a float. */
function numberKnob(
  name: string,
  value: number,
  layer: string,
  node: string,
): Json {
  const hi = Math.max(2, Math.ceil(Math.abs(value) * 2));
  const own = {
    name,
    label: label(name.split(".").pop() ?? name),
    help: "",
    default: value,
    lo: value < 0 ? -hi : 0,
    hi,
    layer,
    node,
  };
  if (Number.isInteger(value))
    return { ...goldenParam("layers.base.zoo.bands"), ...own };
  return {
    ...goldenParam("layers.base.zoo.level"),
    ...own,
    step: hi / 200,
    sweet: [0, hi],
  };
}

/** Layer `id`'s mix knobs (opacity, blend, enabled), after the golden's base layer. */
function mixKnobs(id: string): Json[] {
  return ["opacity", "blend", "enabled"].map((knob) => ({
    ...goldenParam(`layers.base.${knob}`),
    name: `layers.${id}.${knob}`,
    layer: id,
  }));
}

interface Node {
  op: string;
  in?: string[];
  args?: Json;
}

interface Layer {
  id: string;
  nodes: Record<string, Node>;
  [field: string]: unknown;
}

/** The mock's running look and the values of its knobs. */
export class MockAura {
  layers: Layer[] = [];
  signals: Record<string, Node> = {};
  routes: Json[] = [];
  front: string[] = [];
  values: Json = {};
  master = 0.6;
  blackout = false;
  private records: Json[] = [];

  constructor(look: LookDocument) {
    this.play(look);
  }

  /** Run `look` whole, its knobs at the values it gives. */
  play(look: LookDocument) {
    const doc = look as Json;
    this.layers = (doc.layers as Layer[]).map((l) => ({ ...l }));
    this.signals = { ...((doc.signals as Record<string, Node>) ?? {}) };
    this.routes = (doc.routes as Json[]) ?? [];
    this.front = (doc.front as string[]) ?? [];
    if (typeof doc.master === "number") this.master = doc.master;
    this.declare(
      Object.fromEntries(
        this.layers.flatMap((l) => [
          [`layers.${l.id}.opacity`, l.opacity ?? 1],
          [`layers.${l.id}.blend`, l.blend ?? "normal"],
          [`layers.${l.id}.enabled`, true],
        ]),
      ),
    );
  }

  /** The records of every knob, the values in `set` replacing their own. */
  private declare(set: Json = {}) {
    const args = (prefix: string, layer: string, id: string, node: Node) =>
      Object.entries(node.args ?? {}).flatMap(([arg, v]) =>
        typeof v === "number"
          ? [numberKnob(`${prefix}.${id}.${arg}`, v, layer, id)]
          : [],
      );
    this.records = [
      ...this.layers.flatMap((l) => [
        ...Object.entries(l.nodes).flatMap(([id, node]) =>
          args(`layers.${l.id}`, l.id, id, node),
        ),
        ...mixKnobs(l.id),
      ]),
      ...Object.entries(this.signals).flatMap(([id, node]) =>
        args("signals", "", id, node),
      ),
    ];
    const old = this.values;
    this.values = Object.fromEntries(
      this.records.map((r) => {
        const name = r.name as string;
        return [
          name,
          name in set ? set[name] : name in old ? old[name] : r.default,
        ];
      }),
    );
    this.front = this.front.filter((p) => p in this.values);
  }

  /** Why `value` cannot be set at `name`, or null once it is. */
  set(name: unknown, value: unknown): string | null {
    const r = this.records.find((x) => x.name === name);
    if (!r) return `no knob ${String(name)}`;
    const ok =
      r.kind === "float" || r.kind === "int"
        ? typeof value === "number" &&
          value >= (r.lo as number) &&
          value <= (r.hi as number) &&
          (r.kind === "float" || Number.isInteger(value))
        : r.kind === "bool"
          ? typeof value === "boolean"
          : (r.options as Json[]).some((o) => o.value === value);
    if (!ok) return `${String(name)} cannot take ${JSON.stringify(value)}`;
    this.values = { ...this.values, [name as string]: value };
    return null;
  }

  /** Add a layer of the looks file's form under `below`, or on top; null once added, else why not. */
  add(layer: Json, below: unknown): string | null {
    const nodes = layer.nodes as Record<string, Node> | undefined;
    if (!nodes || typeof layer.out !== "string")
      return "a layer needs nodes and an out";
    let id = layer.out;
    for (let k = 2; this.layers.some((l) => l.id === id); k++)
      id = `${layer.out}${k}`;
    const at = this.layers.findIndex((l) => l.id === below);
    this.layers.splice(at < 0 ? this.layers.length : at, 0, {
      ...layer,
      id,
      nodes,
    });
    this.declare();
    return null;
  }

  remove(lid: unknown): string | null {
    if (this.layers.length < 2) return "the last layer stays";
    const at = this.layers.findIndex((l) => l.id === lid);
    if (at < 0) return `no layer ${String(lid)}`;
    this.layers.splice(at, 1);
    this.declare();
    return null;
  }

  move(lid: unknown, to: unknown): string | null {
    const at = this.layers.findIndex((l) => l.id === lid);
    if (at < 0 || typeof to !== "number" || to < 0 || to >= this.layers.length)
      return `cannot move ${String(lid)} there`;
    const [layer] = this.layers.splice(at, 1);
    this.layers.splice(to, 0, layer!);
    return null;
  }

  /** The per-frame states, in the order the engine sends them. */
  states(): Message[] {
    const graph = (id: string, node: Node) => ({
      id,
      op: node.op,
      label: label(node.op),
      in: node.in ?? [],
    });
    return [
      { type: "status", error: null, source: null, path: null },
      { type: "declare", params: this.records },
      { type: "params", values: this.values },
      {
        type: "aura",
        stack: {
          layers: this.layers.map((l) => ({
            id: l.id,
            nodes: Object.entries(l.nodes).map(([id, n]) => graph(id, n)),
          })),
          signals: Object.entries(this.signals).map(([id, n]) => ({
            ...graph(id, n),
            range: [-1, 1],
          })),
          routes: this.routes,
          front: this.front,
          dims: 3,
        },
        fading: false,
        progress: null,
        master: this.master,
        cap: 1,
        blackout: this.blackout,
        looks: null,
        triggers: null,
      },
      golden("catalog"),
    ];
  }
}
