// Room-event triggers and cues (pewpew.aura.triggers), as the aura state carries them.

export interface Held {
  readonly trigger: string;
  readonly look: string;
  /** Engine seconds, comparable with a frame's `t`; null while the look waits for a fade. */
  readonly until: number | null;
}

/** The last event judged. */
export interface LastEvent {
  readonly name: string;
  readonly fired: boolean;
  /** Why it was dropped (pewpew.aura.triggers lists the reasons); null when it fired. */
  readonly reason: string | null;
  /** Why a fired event's look could not be held. */
  readonly error: string | null;
}

/** What a cue fires: the look it holds, for `hold` seconds; null: the event only reaches the running look. */
export interface Cue {
  readonly look: string | null;
  readonly hold: number;
}

export interface TriggersState {
  readonly armed: boolean;
  /** The names a `fire` accepts, in file order. */
  readonly names: readonly string[];
  /** What each name fires. */
  readonly cues: Readonly<Record<string, Cue>>;
  /** The look a trigger holds as an override. */
  readonly held: Held | null;
  readonly last: LastEvent | null;
}

/** The arm switch is usable when a trigger exists, or while armed so it can be disarmed. */
export function armable(tr: TriggersState | null): tr is TriggersState {
  return !!tr && (tr.names.length > 0 || tr.armed);
}

/** A cue button's text: its name, and while it holds a look the seconds left at engine time `t`. */
export function cueText(name: string, held: Held | null, t: number): string {
  if (held?.trigger !== name) return name;
  return held.until === null ? `${name} · …` : `${name} · ${Math.max(0, Math.ceil(held.until - t))}s`;
}

/** What became of an event, in words, and whether a page draws a ✓ after them. */
export interface Outcome {
  readonly text: string;
  readonly tick: boolean;
}

/** The engine's reasons an event was dropped, where the page's words differ (pewpew.aura.triggers). */
const DROPPED: Readonly<Record<string, string>> = { disarmed: "cues off" };

/** What became of the last event: fired, or why not; one that holds no look was sent, to the running
 * look alone. `short`, a fire that went through is its name and a ✓. */
export function lastText(last: LastEvent | null, short = false, cues: TriggersState["cues"] = {}): Outcome {
  if (!last) return { text: "", tick: false };
  if (!last.fired) return { text: `${last.name}: ${DROPPED[last.reason ?? ""] ?? last.reason ?? "dropped"}`, tick: false };
  if (last.error) return { text: `${last.name} fired, but ${last.error}`, tick: false };
  if (short) return { text: last.name, tick: true };
  return { text: `${last.name} ${cues[last.name]?.look === null ? "sent" : "fired"}`, tick: false };
}

/** What cue `name` does, in a few words: `cue1 → depth-charge for 20 s`, or `door → tells the look,
 * no look change`. */
export function cueDoes(name: string, cues: TriggersState["cues"]): string {
  const cue = cues[name];
  if (!cue) return name;
  return `${name} → ${cue.look === null ? "tells the look, no look change" : `${cue.look} for ${cue.hold} s`}`;
}
