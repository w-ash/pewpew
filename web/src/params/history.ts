// This page's look edits, for undo and redo. Each set and colorway the page sends goes through
// `EditHistory.sender`, which records it as a step: one gesture on one knob, one colorway press, or the
// sets sent in one go ("reset to defaults"). Undo and redo send the values a step holds as they are.
import { useSyncExternalStore } from "react";
import { SETTLE_MS } from "../design/useDraft";
import { percent } from "./format";
import { equalValue, formatValue } from "./kinds";
import { caption, type Param, type ValueOf } from "./schema";
import { isOpacity } from "../stack/stack";
import type { ClientMessage, Sender } from "../wire/protocol";
import { useWireContext, type WireStore } from "../wire/store";

/** How long after a set of a knob a set of the same knob joins its step: in a drag, until its control lets
 * go; after a press (a key step, − or +), when it is a press too (`seal`). */
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

/** What the page sends that ends the history: another look, or the same one again (a revert). */
const ENDS: ReadonlySet<ClientMessage["type"]> = new Set(["recall", "look", "surprise", "vary"]);

/** `v` as the control of `p` shows it: a layer's opacity and a color's levels as percents, a
 * choice in lower case. */
export function shownValue<P extends Param>(p: P, v: ValueOf<P>): string {
  if (isOpacity(p) && typeof v === "number") return percent(v);
  const text = formatValue(p, v);
  return p.kind === "choice" ? text.toLowerCase() : text;
}

/** The look edits of this page, past and undone. A step is kept only when it changed a value. The
 * history ends on a recall, a revert, a surprise or a vary this page sends. A step whose knobs are gone
 * goes, and undo and redo skip a knob that changed since this page set it (another page, a drift, an
 * engine restart, another look). */
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
  /** Set from a set to the end of its task: a let go before then is a press's. */
  private fresh = false;
  /** The last press of a knob: its step, which its next press within GROUP_MS joins. */
  private run: { readonly name: string; readonly step: Step; readonly at: number } | null = null;
  /** The value this page last sent for each knob, and when: until SETTLE_MS later it stands for the
   * engine's echo, which may still be on the way. */
  private readonly sent = new Map<string, { readonly value: unknown; readonly at: number }>();
  /** A colorway press whose step waits for the engine's echo: each knob's value before it. */
  private pressed: { readonly name: string; readonly before: ReadonlyMap<string, unknown> } | null = null;
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

  /** The control of knob `name` let go: its next set starts a new step. A let go in the task of its set
   * is a press (a key step, − or +; a drag lets go in a later task): its step joins the step of the press
   * of the knob before it, when that came less than GROUP_MS before. */
  seal(name: string): void {
    const open = this.open;
    if (open?.name !== name) return;
    const top = this.past.at(-1), prev = this.past.at(-2), run = this.run;
    this.run = null;
    if (this.fresh && top?.changes.length === 1) {
      if (run && run.step === prev && run.name === name && open.at - run.at < GROUP_MS) {
        this.past.splice(-2, 2, { changes: [{ ...top.changes[0]!, from: prev.changes[0]!.from }], colorway: null });
      }
      this.run = { name, step: this.past.at(-1)!, at: open.at };
    }
    this.close();
  }

  /** Put back the values before the last step; returns what it did, in words, or null when there is none. */
  undo(): string | null {
    return this.take(this.past, this.future, true);
  }

  /** Set again the values of the last step undone; returns what it did, in words, or null when there is none. */
  redo(): string | null {
    return this.take(this.future, this.past, false);
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
    const change = { name, from: k < 0 ? this.shown(p) : step.changes[k]!.from, to };
    this.past[this.past.length - 1] = { ...step, changes: k < 0 ? [...step.changes, change] : step.changes.with(k, change) };
    this.sent.set(name, { value: to, at });
    this.open = { name, at };
    if (!this.burst) {
      this.burst = true;
      queueMicrotask(() => (this.burst = false));
    }
    // A control may let go in a microtask after its set (the slider's keys do).
    if (!this.fresh) {
      this.fresh = true;
      setTimeout(() => (this.fresh = false), 0);
    }
    this.changed();
  }

  private press(name: string): void {
    // The active colorway: its every value is held now, so the press changes nothing.
    if (this.store.getState().aura?.stack.colorway === name) return;
    this.settle();
    this.future = [];
    this.pressed = { name, before: new Map(this.store.getState().params.map((p) => [p.name, this.shown(p)])) };
    // The press sets the knobs: the engine's echo of it is their value.
    this.sent.clear();
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

  /** Undo or redo the last step of `from`, which then goes to `to`. A knob that no longer holds the value
   * this page left it at keeps its value, and the step is dropped. A step of knobs that are gone is dropped. */
  private take(from: Step[], to: Step[], undo: boolean): string | null {
    this.settle();
    this.run = null;
    for (let step = from.pop(); step; step = from.pop()) {
      const live = this.live(step);
      if (!live.length) continue;
      const at = this.now();
      const done: Change[] = [], skipped: Change[] = [];
      for (const c of live) {
        const p = this.param(c.name)!;
        if (!equalValue(p, this.shown(p) as never, (undo ? c.to : c.from) as never)) {
          skipped.push(c);
          continue;
        }
        const value = undo ? c.from : c.to;
        this.raw.send({ type: "set", name: c.name, value });
        this.sent.set(c.name, { value, at });
        done.push(c);
      }
      if (!skipped.length) to.push(step);
      this.changed();
      return this.told(step, done, skipped, undo);
    }
    this.changed();
    return null;
  }

  /** What undo or redo of `step` did, in words: "undid stripes · wave_a, back to 3.2", and which knobs it
   * skipped. A palette's value is not said. */
  private told(step: Step, done: readonly Change[], skipped: readonly Change[], undo: boolean): string {
    const verb = undo ? "undid" : "redid";
    const only = done.length === 1 ? done[0]! : null;
    const p = only && this.param(only.name);
    const did = !done.length ? null
      : step.colorway !== null ? `${verb} colorway ${step.colorway}`
      : !only || !p ? `${verb} ${done.length} knobs`
      : p.kind === "palette" ? `${verb} ${this.knob(p)}`
      : `${verb} ${this.knob(p)}, ${undo ? "back to" : "to"} ${shownValue(p, (undo ? only.from : only.to) as never)}`;
    const one = skipped.length === 1 ? this.param(skipped[0]!.name) : undefined;
    const not = !skipped.length ? null
      : `${one ? `${this.knob(one)} was` : `${skipped.length} knobs were`} changed elsewhere: not ${undo ? "undone" : "redone"}`;
    return [did, not].filter(Boolean).join("; ");
  }

  /** Knob `p` in words: its step, else its layer, after its caption ("stripes · wave_a", "opacity · base"). */
  private knob(p: Param): string {
    return [caption(p).toLowerCase(), p.node || p.layer].filter(Boolean).join(" · ");
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
    // The engine's echo of the press: the values it set have come.
    if (this.pressed && aura?.stack.colorway === this.pressed.name) this.settle();
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

  /** The value of `p` on this page: the value it last sent, while the engine's echo may be on the way. */
  private shown(p: Param): unknown {
    const mine = this.sent.get(p.name);
    return mine && this.now() - mine.at < SETTLE_MS ? mine.value : this.value(p);
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
