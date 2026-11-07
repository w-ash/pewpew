// What the engine last said, as React reads it. Each message is absolute
// state, so the last write wins on every tab.
import { createContext, useContext, useEffect, useState, useSyncExternalStore } from "react";
import { frameGap, type HealthState } from "../../domain/health/health";
import { decodeParam, equalValue, readValue } from "../../domain/params/kinds";
import type { Param, ValueOf } from "../../domain/params/schema";
import type { MapShape } from "../../domain/room/layout";
import { offSaved } from "../../domain/aura/looks";
import type { AuraState } from "../../domain/aura/aura";
import type { Catalog } from "../../domain/stack/catalog";
import type { LayerItem } from "../../domain/stack/stack";
import type { Control, ErrorSource, Frame, Sender, ServerMessage } from "./protocol";

export interface Refusal {
  readonly control: Control;
  readonly name: string | null;
  readonly reason: string;
  /** Counts refusals, so the same reason twice is still news. */
  readonly seq: number;
}

export interface EngineError {
  readonly text: string;
  readonly source: ErrorSource | null;
  /** The path of the part that raised, for a render error. */
  readonly path: string | null;
}

export interface WireState {
  readonly connected: boolean;
  /** The engine's display gamma, from the hello; null before one. */
  readonly gamma: number | null;
  /** The positions, replaced whole by a hello or a layout. */
  readonly map: MapShape | null;
  readonly params: readonly Param[];
  readonly aura: AuraState | null;
  readonly health: HealthState | null;
  /** What a layer can run; null before the engine sends it. */
  readonly catalog: Catalog | null;
  /** The engine's error, which outlives a refusal. */
  readonly error: EngineError | null;
  /** The latest refusal per control, and per param for a refused `set`. */
  readonly refusals: Readonly<Partial<Record<Control, Refusal>>>;
  readonly paramRefusals: Readonly<Record<string, Refusal>>;
  /** Counts hellos: state a page held for the last connection is dropped on a new one. */
  readonly session: number;
}

type Listener = () => void;

const INITIAL: WireState = {
  connected: false, gamma: null, map: null, params: [], aura: null, health: null, catalog: null,
  error: null, refusals: {}, paramRefusals: {}, session: 0,
};

/** `next`, reusing every part of `prev` that is equal to it, so a message
 * that changes one field leaves the identity of the others alone. */
function share<T>(prev: T, next: T): T {
  if (Object.is(prev, next) || typeof prev !== "object" || typeof next !== "object" || !prev || !next) return next;
  if (Array.isArray(prev) !== Array.isArray(next)) return next;
  const p = prev as Record<string, unknown>, n = next as Record<string, unknown>;
  const out = (Array.isArray(next) ? [] : {}) as Record<string, unknown>;
  const keys = Object.keys(n);
  let same = keys.length === Object.keys(p).length;
  for (const k of keys) {
    out[k] = share(p[k], n[k]);
    same &&= Object.is(out[k], p[k]);
  }
  return (same ? prev : out) as T;
}

/** Add `l` to the listeners of `name` in `map`; returns the unsubscribe. */
function listen(map: Map<string, Set<Listener>>, name: string, l: Listener): () => void {
  let set = map.get(name);
  if (!set) map.set(name, (set = new Set()));
  set.add(l);
  return () => set.delete(l);
}

export class WireStore {
  private state = INITIAL;
  private readonly listeners = new Set<Listener>();
  private readonly paramListeners = new Map<string, Set<Listener>>();
  private readonly modListeners = new Map<string, Set<Listener>>();
  private readonly frameListeners = new Set<Listener>();
  /** The decoded value of each param, replaced only when it changes by its kind's `equal`. */
  private readonly values = new Map<string, unknown>();
  /** The live value of each knob a route moves, by address, as the last `mod` said. */
  private readonly mods = new Map<string, number>();
  /** The JSON last received for each param, read again when the declarations change. */
  private readonly wire = new Map<string, unknown>();
  private frame: Frame | null = null;
  private seq = 0;
  /** performance.now() of the last frame, or 0 since a connection opened. */
  lastFrameAt = 0;

  getState = (): WireState => this.state;
  getFrame = (): Frame | null => this.frame;

  subscribe = (l: Listener): (() => void) => {
    this.listeners.add(l);
    return () => this.listeners.delete(l);
  };

  subscribeFrame = (l: Listener): (() => void) => {
    this.frameListeners.add(l);
    return () => this.frameListeners.delete(l);
  };

  subscribeParam(name: string, l: Listener): () => void {
    return listen(this.paramListeners, name, l);
  }

  subscribeMod(name: string, l: Listener): () => void {
    return listen(this.modListeners, name, l);
  }

  /** The engine's value of `p`, or undefined before it has sent one. */
  value<P extends Param>(p: P): ValueOf<P> | undefined {
    return this.values.get(p.name) as ValueOf<P> | undefined;
  }

  /** The live value of the knob at address `name` that a route moves, or undefined when none does. */
  mod(name: string): number | undefined {
    return this.mods.get(name);
  }

  /** New live values: each knob whose value changed, came or went is told. */
  private setMods(values: Readonly<Record<string, number>>): void {
    const changed = Object.entries(values).filter(([name, v]) => this.mods.get(name) !== v).map(([name]) => name);
    const gone = [...this.mods.keys()].filter((name) => !Object.hasOwn(values, name));
    for (const name of gone) this.mods.delete(name);
    for (const name of changed) this.mods.set(name, values[name]!);
    for (const name of [...changed, ...gone]) for (const l of this.modListeners.get(name) ?? []) l();
  }

  private update(patch: Partial<WireState>): void {
    this.state = { ...this.state, ...patch };
    for (const l of this.listeners) l();
  }

  /** New declarations: every value is read again from its JSON, and every param listener told. */
  private declare(records: readonly unknown[]): readonly Param[] {
    const params = records.map(decodeParam);
    const names = new Set(params.map((p) => p.name));
    for (const name of [...this.wire.keys()]) if (!names.has(name)) this.wire.delete(name);
    this.values.clear();
    for (const p of params) {
      const v = this.wire.has(p.name) ? readValue(p, this.wire.get(p.name)) : undefined;
      if (v !== undefined) this.values.set(p.name, v);
    }
    for (const set of this.paramListeners.values()) for (const l of set) l();
    return params;
  }

  private setValues(json: Readonly<Record<string, unknown>>): void {
    for (const p of this.state.params) {
      if (!Object.hasOwn(json, p.name)) continue;
      this.wire.set(p.name, json[p.name]);
      const v = readValue(p, json[p.name]);
      const old = this.values.get(p.name);
      if (v === undefined || (old !== undefined && equalValue(p, old, v))) continue;
      this.values.set(p.name, v);
      for (const l of this.paramListeners.get(p.name) ?? []) l();
    }
  }

  receive(msg: ServerMessage): void {
    switch (msg.type) {
      case "hello": {
        // A new connection: what the last one said is dropped, and the rest follows.
        const { type: _, display_gamma, ...map } = msg;
        this.wire.clear();
        this.setMods({});
        this.clearFrame();
        this.update({
          connected: true, gamma: display_gamma, map, params: this.declare([]), aura: null, catalog: null,
          error: null, refusals: {}, paramRefusals: {}, session: this.state.session + 1,
        });
        break;
      }
      case "layout": {
        const { type: _, ...map } = msg;
        this.clearFrame();
        this.update({ map });
        break;
      }
      case "status":
        this.update({ error: msg.error ? { text: msg.error, source: msg.source, path: msg.path } : null });
        break;
      case "declare":
        this.update({ params: this.declare(msg.params) });
        break;
      case "params":
        this.setValues(msg.values);
        break;
      case "mod":
        this.setMods(msg.values);
        break;
      case "aura": {
        const { type: _, ...aura } = msg;
        this.update({ aura: share(this.state.aura, aura) });
        break;
      }
      case "health": {
        const { type: _, ...health } = msg;
        this.update({ health: share(this.state.health, health) });
        break;
      }
      case "catalog": {
        const { type: _, ...catalog } = msg;
        this.update({ catalog: share(this.state.catalog, catalog) });
        break;
      }
      case "refused": {
        if (msg.control === null) break; // a request whose `type` is not text, which this page never sends
        const refusal: Refusal = { control: msg.control, name: msg.name ?? null, reason: msg.reason, seq: ++this.seq };
        const { paramRefusals } = this.state;
        this.update({
          refusals: { ...this.state.refusals, [msg.control]: refusal },
          paramRefusals: msg.control === "set" && msg.name ? { ...paramRefusals, [msg.name]: refusal } : paramRefusals,
        });
        break;
      }
      case "ack": // the socket settles the `ask` it answers
        break;
      default:
        msg satisfies never;
    }
  }

  /** The frame drawn on the last positions is meaningless on new ones. */
  private clearFrame(): void {
    this.frame = null;
    for (const l of this.frameListeners) l();
  }

  receiveFrame(frame: Frame, now: number): void {
    this.frame = frame;
    this.lastFrameAt = now;
    for (const l of this.frameListeners) l();
  }

  /** The socket closed: the engine's error and health died with it, and the next engine sends its own. */
  disconnected(): void {
    this.lastFrameAt = 0;
    this.update({ connected: false, error: null, health: null });
  }
}

export interface Wire {
  readonly store: WireStore;
  readonly sender: Sender;
}

export const WireContext = createContext<Wire | null>(null);

export function useWireContext(): Wire {
  const wire = useContext(WireContext);
  if (!wire) throw new Error("no WireContext");
  return wire;
}

/** A slice of the wire state. `select` must return a part of the state, not a new object. */
export function useWire<T>(select: (s: WireState) => T): T {
  const { store } = useWireContext();
  return useSyncExternalStore(store.subscribe, () => select(store.getState()));
}

/** The aura state; while a new connection waits for its own, a moment after its hello, the last one, so
 * a reconnect or an engine restart keeps what the page shows, and the focus in it. */
export function useStandingAura(): AuraState | null {
  const live = useWire((s) => s.aura);
  const [last, setLast] = useState(live);
  if (live && live !== last) setLast(live);
  return live ?? last;
}

const NO_LAYERS: readonly LayerItem[] = [];

/** The running look's layers, bottom first; none before the engine sends the aura state. */
export function useLayers(): readonly LayerItem[] {
  return useWire((s) => s.aura?.stack.layers ?? NO_LAYERS);
}

export function useSender(): Sender {
  return useWireContext().sender;
}

/** The engine's value of `p`, else its default. Re-renders only when that one value changes. */
export function useParamValue<P extends Param>(p: P): ValueOf<P> {
  const { store } = useWireContext();
  const value = useSyncExternalStore(
    (l) => store.subscribeParam(p.name, l),
    () => store.value(p),
  );
  return value ?? p.default;
}

/** Whether a knob of `ps` is off the look as saved, or, given `prefix`, one under it came or went
 * since (`offSaved`): false with no saved look, and while a recall waits to replace it. */
export function useOffSaved(ps: readonly Param[], prefix = ""): boolean {
  const { store } = useWireContext();
  return useSyncExternalStore(
    (l) => {
      const offs = [store.subscribe(l), ...ps.map((p) => store.subscribeParam(p.name, l))];
      return () => {
        for (const off of offs) off();
      };
    },
    () => {
      const looks = store.getState().aura?.looks;
      return !!looks?.saved && !looks.pending && offSaved(ps, (p) => store.value(p), looks.saved, prefix);
    },
  );
}

/** Whether the engine's value of each param of `ps` is its default. Re-renders only when that
 * changes. */
export function useAtDefaults(ps: readonly Param[]): boolean {
  const { store } = useWireContext();
  return useSyncExternalStore(
    (l) => {
      const offs = ps.map((p) => store.subscribeParam(p.name, l));
      return () => {
        for (const off of offs) off();
      };
    },
    () =>
      ps.every((p) => {
        const v = store.value(p);
        return v === undefined || equalValue(p, v, p.default);
      }),
  );
}

/** The live value of the knob at address `name` that a route moves, or null when none does.
 * Re-renders only when that one value changes. */
export function useMod(name: string): number | null {
  const { store } = useWireContext();
  return useSyncExternalStore((l) => store.subscribeMod(name, l), () => store.mod(name)) ?? null;
}

/** A value read from the newest frame. Re-renders only when it changes, so
 * select something that changes less often than every frame where you can. */
export function useFrameValue<T>(select: (f: Frame | null) => T): T {
  const { store } = useWireContext();
  return useSyncExternalStore(store.subscribeFrame, () => select(store.getFrame()));
}

function latest(s: WireState, pick: (c: Control) => boolean): Refusal | null {
  let found: Refusal | null = null;
  for (const r of Object.values(s.refusals)) if (r && pick(r.control) && (!found || r.seq > found.seq)) found = r;
  return found;
}

/** The latest refusal of any of `controls`, or null. */
export function useRefusal(...controls: Control[]): Refusal | null {
  return useWire((s) => latest(s, (c) => controls.includes(c)));
}

/** The latest refusal of any control but `controls`, or null. */
export function useRefusalExcept(...controls: Control[]): Refusal | null {
  return useWire((s) => latest(s, (c) => !controls.includes(c)));
}

/** The latest refused `set` of the param `name`, or null. */
export function useParamRefusal(name: string): Refusal | null {
  return useWire((s) => s.paramRefusals[name] ?? null);
}

/** Seconds since the last frame once frames are stale, else 0; checked every second. */
export function useFrameGap(): number {
  const { store } = useWireContext();
  const [gap, setGap] = useState(0);
  useEffect(() => {
    const id = setInterval(() => setGap(frameGap(performance.now(), store.lastFrameAt)), 1000);
    return () => clearInterval(id);
  }, [store]);
  return gap;
}
