// The aura state (the `aura` message), and what the room shows.
import { percent } from "../params/format";
import type { StackState } from "../stack/stack";
import { liveLook, unsaved, type LooksState } from "./looks";
import type { TriggersState } from "./triggers";

export interface AuraState {
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

/** What the room shows, for a glance. */
export interface Now {
  /** The live look; else, with a looks file, a draft: the made look by its label, which is new for each
   * look the run makes, or the name a save gives it; else "". */
  readonly name: string;
  /** The current look, changed since saved (`unsaved`). */
  readonly changed: boolean;
  /** What plays is no saved look (a made look), which a save keeps (`saveOf`). */
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
  return { name: draft ?? "", changed: false, draft: draft !== null, master };
}
