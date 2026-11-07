// The aura state (the `aura` message), and the pattern list.
import { percent } from "../params/format";
import type { StackState } from "../stack/stack";
import { liveLook, unsaved, type LooksState } from "./looks";
import type { TriggersState } from "./triggers";

export interface AuraState {
  /** The bottom layer's pattern name. */
  readonly pattern: string;
  /** The names a `pick` accepts. */
  readonly patterns: readonly string[];
  /** The running look's layers. */
  readonly stack: StackState;
  /** Whether a crossfade runs, whatever started it, and how far, in steps of 0.05 (null between fades). */
  readonly fading: boolean;
  readonly progress: number | null;
  readonly master: number;
  /** The master's cap, set at launch. */
  readonly cap: number;
  readonly blackout: boolean;
  /** Null without a looks file (`run --looks`). */
  readonly looks: LooksState | null;
  readonly triggers: TriggersState | null;
}

/** What the pattern list reads from the aura state. */
export type Patterns = Pick<AuraState, "pattern" | "patterns">;

export interface PatternEntry {
  readonly name: string;
  readonly current: boolean;
  /** False for a launch pattern given as a file, which a pick cannot name. */
  readonly pickable: boolean;
}

export function patternList(aura: Patterns): PatternEntry[] {
  const names = aura.patterns.includes(aura.pattern) ? aura.patterns : [aura.pattern, ...aura.patterns];
  return names.map((name) => ({ name, current: name === aura.pattern, pickable: aura.patterns.includes(name) }));
}

/** The pickable pattern `step` places after the current one, wrapping; null when there is none. */
export function neighbour(aura: Patterns, step: number): string | null {
  const names = aura.patterns;
  if (!names.length) return null;
  const i = names.indexOf(aura.pattern);
  const next = i < 0 ? (step > 0 ? 0 : names.length - 1) : (i + step + names.length) % names.length;
  const name = names[next] ?? null;
  return name === aura.pattern ? null : name;
}

/** What the room shows, for a glance. */
export interface Now {
  /** The live look; else, with a looks file, a draft: the made look by its label, which is new for each
   * look the run makes, or a pattern picked by the name a save gives it; else the pattern. */
  readonly name: string;
  /** The current look, changed since saved (`unsaved`). */
  readonly changed: boolean;
  /** What plays is no saved look (a made look, or a pattern picked), which a save keeps (`saveOf`). */
  readonly draft: boolean;
  /** The brightness (the master), as a percent. */
  readonly master: string;
}

export function nowOf(aura: AuraState): Now {
  const { looks, triggers } = aura;
  const live = liveLook(looks, triggers);
  const master = percent(aura.master);
  if (live !== null) return { name: live, changed: live === looks?.current && unsaved(looks), draft: false, master };
  const draft = looks?.made ?? looks?.offered ?? null;
  return { name: draft ?? aura.pattern, changed: false, draft: draft !== null, master };
}
