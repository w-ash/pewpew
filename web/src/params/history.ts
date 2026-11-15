// This page's look edits, for undo and redo. Each set and colorway the page sends goes through
// `EditHistory.sender`, which records it as a step: one gesture on one knob, one colorway press, or the
// sets sent in one go ("reset to defaults"). Undo and redo send the values a step holds as they are.
import { useSyncExternalStore } from "react";
import { percent } from "./format";
import { equalValue, formatValue } from "./kinds";
import { caption, type Param, type ValueOf } from "./schema";
import { isOpacity } from "../stack/stack";
import type { ClientMessage, Sender } from "../wire/protocol";
import { useWireContext, type WireStore } from "../wire/store";

/** How long after a set of a knob a set of the same knob joins its step, unless its control let go first. */
export const GROUP_MS = 1000;
/** How many steps undo goes back. */
export const MAX_STEPS = 200;

/** A knob a step changed: its address, and its value before the step and after it. */
export interface Change {
  readonly name: string;
  readonly from: unknown;
  readonly to: unknown;
}

/** One undo step. `colorway` names the colorway a press set, else null. */
export interface Step {
  readonly changes: readonly Change[];
  readonly colorway: string | null;
}

/** What the page sends that ends the history: another look (or the same one again: a revert), a save. */
const ENDS: ReadonlySet<ClientMessage["type"]> = new Set(["recall", "save", "keep", "look", "surprise", "vary"]);

/** `v` as the control of `p` shows it: a layer's opacity and a color's levels as percents, a
 * choice in lower case. */
export function shownValue<P extends Param>(p: P, v: ValueOf<P>): string {
  if (isOpacity(p) && typeof v === "number") return percent(v);
  const text = formatValue(p, v);
  return p.kind === "choice" ? text.toLowerCase() : text;
}

/** The look edits of this page, past and undone. A step is kept only when it changed a value. The
 * history ends on a recall, a save or a revert this page sends, and when the look's layers, its name or
 * the made look change (another tab, the idle cycle). */
export class EditHistory {
  /** The page's sender: it records each `set` and `colorway`, then sends it. */
  readonly sender: Sender;
  private readonly store: WireStore;
  private readonly raw: Sender;
  private readonly now: () => number;
  private past: Step[] = [];
  private future: Step[] = [];
  /** The knob whose step a further set joins, and when it was last set; null once its control lets go. */
  private open: { readonly name: string; at: number } | null = null;
  /** Set while the current task sends: its sets of other knobs join the same step. */
  private burst = false;
  /** A colorway press whose step waits for the engine's echo: each knob's value before it. */
  private pressed: { readonly name: string; readonly before: ReadonlyMap<string, unknown> } | null = null;
  /** The look, its layers and the made look, as last seen: when it changes, the history ends. */
  private look: string | null = null;
  /** The knobs as last seen: a knob that goes takes its steps with it. */
  private params: unknown = null;
  private readonly listeners = new Set<() => void>();

  constructor(store: WireStore, raw: Sender, now: () => number = () => performance.now()) {
    this.store = store;
    this.raw = raw;
    this.now = now;
    this.sender = {
      send: (msg) => {
        this.record(msg);
        raw.send(msg);
      },
      sendLatest: (msg) => {
        this.record(msg);
        raw.sendLatest(msg);
      },
      ask: (msg) => {
        this.record(msg);
        return raw.ask(msg);
      },
    };
    store.subscribe(this.watch);
    this.watch();
  }

  subscribe = (l: () => void): (() => void) => {
    this.listeners.add(l);
    return () => this.listeners.delete(l);
  };

  /** Whether undo (or redo) has a step to take: one whose knobs, some of them, are still there. */
  can(undo: boolean): boolean {
    if (undo && this.pressed) return true;
    return (undo ? this.past : this.future).some((step) => this.live(step).length > 0);
  }

  /** The control of knob `name` let go: its next set starts a new step. */
  seal(name: string): void {
    if (this.open?.name === name) this.close();
  }

  /** Put back the values before the last step; returns it, or null when there is none. */
  undo(): Step | null {
    return this.take(this.past, this.future, true);
  }

  /** Set again the values of the last step undone; returns it, or null when there is none. */
  redo(): Step | null {
    return this.take(this.future, this.past, false);
  }

  /** What undo or redo of `step` did, in words: "undid stripes · wave_a, back to 3.2". */
  told(step: Step, undo: boolean): string {
    const verb = undo ? "undid" : "redid";
    if (step.colorway !== null) return `${verb} colorway ${step.colorway}`;
    const live = this.live(step);
    const only = live.length === 1 ? live[0]! : null;
    const p = only && this.param(only.name);
    if (!only || !p) return `${verb} ${live.length} knobs`;
    // Its step, else its layer, after its caption: "stripes · wave_a", "opacity · base".
    const knob = [caption(p).toLowerCase(), p.node || p.layer].filter(Boolean).join(" · ");
    return `${verb} ${knob}, ${undo ? "back to" : "to"} ${shownValue(p, (undo ? only.from : only.to) as never)}`;
  }

  private record(msg: ClientMessage): void {
    if (msg.type === "set") this.set(msg.name, msg.value);
    else if (msg.type === "colorway") this.press(msg.name);
    else if (ENDS.has(msg.type)) this.clear();
  }

  private set(name: string, to: unknown): void {
    const p = this.param(name);
    if (!p) return;
    const at = this.now();
    const top = this.past.at(-1);
    const joins =
      top !== undefined && this.open !== null &&
      (this.burst || (top.changes.length === 1 && this.open.name === name && at - this.open.at < GROUP_MS));
    if (!joins) {
      this.settle();
      this.past.push({ changes: [], colorway: null });
      this.past.splice(0, this.past.length - MAX_STEPS);
      this.future = [];
    }
    const step = this.past.at(-1)!;
    const k = step.changes.findIndex((c) => c.name === name);
    const change = { name, from: k < 0 ? this.value(p) : step.changes[k]!.from, to };
    this.past[this.past.length - 1] = { ...step, changes: k < 0 ? [...step.changes, change] : step.changes.with(k, change) };
    this.open = { name, at };
    if (!this.burst) {
      this.burst = true;
      queueMicrotask(() => (this.burst = false));
    }
    this.changed();
  }

  private press(name: string): void {
    // The active colorway: its every value is held now, so the press changes nothing.
    if (this.store.getState().aura?.stack.colorway === name) return;
    this.settle();
    this.future = [];
    this.pressed = { name, before: new Map(this.store.getState().params.map((p) => [p.name, this.value(p)])) };
    this.changed();
  }

  /** The colorway press waiting becomes a step of the knobs it changed, and the open step closes. */
  private settle(): void {
    this.close();
    const pressed = this.pressed;
    if (!pressed) return;
    this.pressed = null;
    const changes = this.store.getState().params.flatMap((p) => {
      const from = pressed.before.get(p.name), to = this.value(p);
      return from === undefined || equalValue(p, from as never, to) ? [] : [{ name: p.name, from, to }];
    });
    if (changes.length) this.past.push({ changes, colorway: pressed.name });
    this.past.splice(0, this.past.length - MAX_STEPS);
    this.changed();
  }

  /** The open step closes; a step that put every value back as it was (a drag the browser took) goes. */
  private close(): void {
    if (!this.open) return;
    this.open = null;
    const top = this.past.at(-1);
    if (top && this.live(top).every((c) => equalValue(this.param(c.name)!, c.from as never, c.to as never))) this.past.pop();
    this.changed();
  }

  private take(from: Step[], to: Step[], undo: boolean): Step | null {
    this.settle();
    for (let step = from.pop(); step; step = from.pop()) {
      // A step of knobs that are gone is dropped.
      const live = this.live(step);
      if (!live.length) continue;
      for (const c of live) this.raw.send({ type: "set", name: c.name, value: undo ? c.from : c.to });
      to.push(step);
      this.changed();
      return step;
    }
    this.changed();
    return null;
  }

  private clear(): void {
    if (!this.past.length && !this.future.length && !this.pressed && !this.open) return;
    this.past = [];
    this.future = [];
    this.open = null;
    this.pressed = null;
    this.changed();
  }

  private readonly watch = (): void => {
    const { params, aura } = this.store.getState();
    if (params !== this.params) {
      this.params = params;
      this.changed();
    }
    if (!aura) return;
    const look = JSON.stringify([aura.looks?.current ?? null, aura.looks?.made ?? null, aura.stack.layers.map((l) => l.id)]);
    if (this.look !== null && look !== this.look) this.clear();
    this.look = look;
    // The engine's echo of the press: the values it set have come.
    if (this.pressed && aura.stack.colorway === this.pressed.name) this.settle();
  };

  private live(step: Step): readonly Change[] {
    return step.changes.filter((c) => this.param(c.name));
  }

  private param(name: string): Param | undefined {
    return this.store.getState().params.find((p) => p.name === name);
  }

  private value(p: Param): unknown {
    return this.store.value(p) ?? p.default;
  }

  private changed(): void {
    for (const l of this.listeners) l();
  }
}

/** The page's edit history, and whether undo and redo have a step to take. */
export function useEdits(): { readonly edits: EditHistory; readonly canUndo: boolean; readonly canRedo: boolean } {
  const { edits } = useWireContext();
  const canUndo = useSyncExternalStore(edits.subscribe, () => edits.can(true));
  const canRedo = useSyncExternalStore(edits.subscribe, () => edits.can(false));
  return { edits, canUndo, canRedo };
}
