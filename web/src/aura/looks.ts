// Saved looks (pewpew.aura.looks), as the aura state carries them.
import { equalValue, readValue } from "../params/kinds";
import type { Param, ValueOf } from "../params/schema";
import type { ClientMessage } from "../wire/protocol";
import type { TriggersState } from "./triggers";

export interface LookItem {
  readonly name: string;
  /** Shuffle plays it (the idle cycle). */
  readonly cycle: boolean;
  /** Its own fade, in seconds: what a press at "fade: as saved" and shuffle take. */
  readonly fade: number;
}

export interface LooksState {
  /** In file order. */
  readonly items: readonly LookItem[];
  /** The favorites: the looks the deck's row shows, by name (pewpew.aura.book; the page sorts them). */
  readonly favorites: readonly string[];
  /** The look last recalled or saved. */
  readonly current: string | null;
  /** A layer, a param or a stored master has moved off `current`, or off the made look. */
  readonly changed: boolean;
  /** The look fading in. */
  readonly fading: string | null;
  /** How far `fading` has faded in, 0..1 in steps of 0.05; null between fades. */
  readonly progress: number | null;
  /** A recall waiting for the running fade to end. */
  readonly pending: string | null;
  /** The idle cycle is stepping. */
  readonly cycling: boolean;
  /** Seconds without input or unsaved edits before the idle cycle starts; null: it never does. */
  readonly idle: number | null;
  /** How long the idle cycle plays each look, in seconds: the shortest and the longest. */
  readonly dwell: readonly [number, number];
  /** The run keeps the idle cycle off whatever is set (a Gallery visit): `idle` is null and the page offers no
   * shuffle. */
  readonly idle_off: boolean;
  /** The engine time from which shuffle plays its next look, comparable with a frame's `t`; null while it will
   * not: off, no look in shuffle, ended, a cue holds a look, or unsaved edits hold its wait. */
  readonly next: number | null;
  /** The label of the look the engine made that plays unsaved ("surprise 7"). */
  readonly made: string | null;
  /** The name a save with none gives what plays (`saveOf`): a made look's label, a copy's name of the current
   * look, else "kept", counted past a name that is taken; null while a cue holds a look. */
  readonly offered: string | null;
  /** Each knob's value as `current` was last recalled or saved, or the made look started, by address,
   * as JSON: what a knob reverts to. Null with neither, and while a trigger holds a look. */
  readonly saved: Readonly<Record<string, unknown>> | null;
}

export interface LookStatus {
  /** In the room now: the look a trigger holds, else the current one. */
  readonly live: boolean;
  /** Current while a trigger holds another: the aura returns to it. */
  readonly returnsTo: boolean;
  /** Current, and the live state has moved off it since it was saved or recalled (`unsaved`). */
  readonly changed: boolean;
  /** How far the look has faded in, 0..1, while it fades in; else null. */
  readonly fading: number | null;
  readonly pending: boolean;
  /** A trigger holds it. */
  readonly held: boolean;
}

/** The look in the room now: the one a trigger holds, else the current one. */
export function liveLook(looks: LooksState | null, triggers: TriggersState | null): string | null {
  return triggers?.held?.look ?? looks?.current ?? null;
}

export function lookStatus(looks: LooksState, triggers: TriggersState | null, name: string): LookStatus {
  const current = name === looks.current;
  const held = triggers?.held?.look === name;
  return {
    live: name === liveLook(looks, triggers),
    returnsTo: current && !!triggers?.held && !held,
    changed: current && unsaved(looks),
    fading: name === looks.fading ? looks.progress : null,
    pending: name === looks.pending,
    held,
  };
}

/** Why "vary this" cannot vary what plays, or null: it varies a look, saved or made, and what to press
 * first. */
export function varyReason(looks: LooksState): string | null {
  if (looks.current !== null || looks.made !== null) return null;
  return `vary this needs a look playing: press ${looks.items.length ? "one, or surprise me," : "surprise me"} first`;
}

/** The most looks a looks file holds (pewpew.aura.book MAX_LOOKS). */
export const MAX_LOOKS = 64;

/** The most favorites (pewpew.aura.book MAX_FAVORITES). */
export const MAX_FAVORITES = 20;

const collator = new Intl.Collator(undefined, { numeric: true, sensitivity: "base" });

/** The one order looks show in: alphabetical, ignoring case, numbers by value ("surprise 2" before
 * "surprise 10"). */
export function byName(a: string, b: string): number {
  return collator.compare(a, b);
}

/** Every look in the page's order (`byName`). */
export function sortedLooks(looks: LooksState): LookItem[] {
  return [...looks.items].sort((a, b) => byName(a.name, b.name));
}

/** The favorites as items in the page's order: the deck's tiles, of which the first nine have keys. */
export function favoriteLooks(looks: LooksState): LookItem[] {
  return sortedLooks(looks).filter((item) => looks.favorites.includes(item.name));
}

/** Why look `name` cannot become a favorite, or null: the row holds `MAX_FAVORITES`. */
export function favoriteReason(looks: LooksState, name: string): string | null {
  return looks.favorites.length >= MAX_FAVORITES && !looks.favorites.includes(name)
    ? `${MAX_FAVORITES} looks are favorites already; unfavorite one first`
    : null;
}

/** What the look header's one save does now (RA-27b §4 B, the save states): `over`, the edits into the
 * current look, changed since saved; `draft`, what plays and no saved look is (a made look), kept
 * under the name it offers, or, at MAX_LOOKS, off and `full` says why; else `none`, and
 * `why`, which `k` says. */
export type Save =
  | { readonly kind: "over"; readonly name: string }
  | { readonly kind: "draft"; readonly name: string; readonly full: string | null }
  | { readonly kind: "none"; readonly why: string };

export function saveOf(looks: LooksState, triggers: TriggersState | null): Save {
  const waits = holdReason(triggers, "save") ?? pendingText(looks);
  if (waits) return { kind: "none", why: waits };
  if (looks.current !== null) return looks.changed ? { kind: "over", name: looks.current } : { kind: "none", why: `${looks.current} is saved` };
  if (!looks.offered) return { kind: "none", why: "nothing to save" };
  const full = looks.items.length >= MAX_LOOKS ? `there are already ${MAX_LOOKS} looks; delete one first` : null;
  return { kind: "draft", name: looks.offered, full };
}

/** Why a save or a delete waits, or null: a cue holds a look, which is not the operator's to save,
 * and the aura returns from it. */
export function holdReason(triggers: TriggersState | null, verb: string): string | null {
  const held = triggers?.held;
  return held ? `${held.trigger} is playing ${held.look}: ${verb} when it ends` : null;
}

/** Why look `name` cannot be deleted, or null: a cue plays it, and only the looks file can change that
 * (pewpew.aura.looks delete). */
export function deleteReason(triggers: TriggersState | null, name: string): string | null {
  return cueBlock(triggers, name, "delete");
}

function cueBlock(triggers: TriggersState | null, name: string, verb: string): string | null {
  const cues = Object.entries(triggers?.cues ?? {}).filter(([, cue]) => cue.look === name).map(([cue]) => cue);
  return cues.length ? `${cues.join(", ")} plays ${name}: change the looks file to ${verb} it` : null;
}

/** Why look `name` cannot be renamed, or null: a cue plays it, and only the looks file can change that
 * (pewpew.aura.looks rename). */
export function renameReason(triggers: TriggersState | null, name: string): string | null {
  return cueBlock(triggers, name, "rename");
}

/** What waits while a recall waits for the running fade to end, or null: the look that comes next. The
 * editor waits too, as under a cue's hold: edits now would be lost when the recall lands. */
export function pendingText(looks: LooksState | null): string | null {
  return looks?.pending ? `${looks.pending} next, when this fade ends` : null;
}

/** Whether the live state holds edits a recall or a made look would lose: the current look, or the
 * made look that plays, changed, and no recall waits to replace it (which a cue's end can leave over the
 * held look's layers). */
export function unsaved(looks: LooksState | null): boolean {
  return !!(looks?.current ?? looks?.made) && looks!.changed && !looks!.pending;
}

/** Whether a knob of `ps`, at `value`, is off `saved` (each knob's value as the look was saved, by
 * address, as JSON), or, given `prefix`, a knob under it came or went since: a part of the look that
 * a save would change. */
export function offSaved(ps: readonly Param[], value: <P extends Param>(p: P) => ValueOf<P> | undefined, saved: Readonly<Record<string, unknown>>, prefix = ""): boolean {
  const off = ps.some((p) => {
    if (!(p.name in saved)) return !!prefix;
    const was = readValue(p, saved[p.name]), now = value(p);
    return was !== undefined && now !== undefined && !equalValue(p, now, was);
  });
  if (off || !prefix) return off;
  const names = new Set(ps.map((p) => p.name));
  return Object.keys(saved).some((name) => name.startsWith(prefix) && !names.has(name));
}

/** `seconds` in words: `40 s`, `1 min`, `90 s`, `1 h`. */
export function span(seconds: number): string {
  if (seconds >= 3600 && seconds % 3600 === 0) return `${seconds / 3600} h`;
  return seconds >= 60 && seconds % 60 === 0 ? `${seconds / 60} min` : `${seconds} s`;
}

/** How long shuffle plays each look, in words: `2 min`, or a file's range `40–90 s`. */
export function eachText(looks: LooksState): string {
  const [lo, hi] = looks.dwell;
  if (lo === hi) return span(lo);
  const [a, b] = [span(lo), span(hi)];
  const unit = (text: string) => text.slice(text.indexOf(" "));
  return unit(a) === unit(b) ? `${a.slice(0, a.indexOf(" "))}–${b}` : `${a}–${b}`;
}

/** Shuffle is on: the looks in it change by themselves, one each turn (the idle cycle's `idle` is set). Off,
 * the lights stay on the look. */
export function shuffleOn(looks: LooksState): boolean {
  return looks.idle !== null;
}

/** Shuffle starts right away: it waits no longer than a turn, so after a touch the look plays at most one
 * turn and shuffle goes on (pewpew.aura.book). Else it waits `idle` seconds untouched. */
export function rightAway(looks: LooksState): boolean {
  return looks.idle !== null && looks.idle <= looks.dwell[0];
}

/** How long each look plays that the page offers, in seconds. */
export const EACH_SECONDS: readonly number[] = [30, 60, 120, 300, 600, 1800];

/** How long shuffle waits untouched before it starts that the page offers, in seconds, past right away. */
export const WAIT_SECONDS: readonly number[] = [60, 120, 300, 600, 1800];

/** The shortest time the engine takes for either (pewpew.aura.book MIN_CYCLE_TIME). */
const MIN_TIME = 1;

/** The value of "right away" among the starts. */
export const RIGHT_AWAY = "now";

/** The request that turns shuffle on, right away at the turn it has, or off. */
export function shuffleSwitch(looks: LooksState, on: boolean): ClientMessage {
  return { type: "idle_cycle", idle: on ? Math.max(MIN_TIME, looks.dwell[0]) : null };
}

/** The request that makes each look play `seconds`; right away stays right away, its wait one turn. */
export function eachRequest(looks: LooksState, seconds: number): ClientMessage {
  return rightAway(looks) ? { type: "idle_cycle", idle: seconds, each: seconds } : { type: "idle_cycle", each: seconds };
}

/** The request for the start `value` (`startItems`): right away, or seconds untouched. */
export function startRequest(looks: LooksState, value: string): ClientMessage {
  return { type: "idle_cycle", idle: value === RIGHT_AWAY ? Math.max(MIN_TIME, looks.dwell[0]) : Number(value) };
}

/** The turns the page offers, as a list names them (`each look: 2 min`), with the book's own when it is none
 * of them (a range, or a time set in the file); the value of a range is "range". */
export function eachItems(looks: LooksState): { items: { value: string; label: string }[]; value: string } {
  const [lo, hi] = looks.dwell;
  const value = lo === hi ? String(lo) : "range";
  const own = lo === hi ? (EACH_SECONDS.includes(lo) ? [] : [lo]) : [];
  const items = [...EACH_SECONDS, ...own].sort((a, b) => a - b).map((s) => ({ value: String(s), label: `each look: ${span(s)}` }));
  if (lo !== hi) items.unshift({ value, label: `each look: ${eachText(looks)}` });
  return { items, value };
}

/** The starts the page offers (`starts: right away`, `starts: after 5 min untouched`), with the book's own
 * wait when it is none of them. */
export function startItems(looks: LooksState): { items: { value: string; label: string }[]; value: string } {
  const idle = looks.idle;
  const value = idle === null || rightAway(looks) ? RIGHT_AWAY : String(idle);
  const own = idle !== null && !rightAway(looks) && !WAIT_SECONDS.includes(idle) ? [idle] : [];
  const waits = [...WAIT_SECONDS, ...own].sort((a, b) => a - b).map((s) => ({ value: String(s), label: `starts: after ${span(s)} untouched` }));
  return { items: [{ value: RIGHT_AWAY, label: "starts: right away" }, ...waits], value };
}

/** `seconds` as a countdown, minutes and seconds: `1:24`, `0:05`; an hour or more `1:02:05`. */
export function countdown(seconds: number): string {
  const s = Math.max(0, Math.ceil(seconds));
  const two = (n: number) => String(n).padStart(2, "0");
  const h = Math.floor(s / 3600), m = Math.floor((s % 3600) / 60);
  return h ? `${h}:${two(m)}:${two(s % 60)}` : `${m}:${two(s % 60)}`;
}

/** What shuffle is doing at engine time `t`, in a few words, while it is on: when the next look comes
 * (`next in 1:24`), or when it starts after its wait (`starts in 4:12`), or why it waits (unsaved edits, a cue)
 * and the fix; empty while it is off. */
export function shuffleStatus(looks: LooksState, triggers: TriggersState | null, t: number): string {
  if (!shuffleOn(looks)) return "";
  if (!looks.items.some((item) => item.cycle)) return "no looks in shuffle: add one from its ⋯";
  if (triggers?.held) return `waits for ${triggers.held.trigger} to end`;
  if (looks.next === null) return unsaved(looks) ? "waits: save or revert to go on" : "ended";
  return `${looks.cycling || rightAway(looks) ? "next in" : "starts in"} ${countdown(looks.next - t)}`;
}

/** What shuffle does, by the book's settings, for the "?" notes: how long each look plays, when it starts,
 * and that a touch waits it again; or, off, that the lights stay on the look. */
export function cycleText(looks: LooksState): string {
  if (!shuffleOn(looks)) return "shuffle is off: the lights stay on the look";
  const wait = rightAway(looks) ? "after a touch, the look plays its whole turn" : `starts after ${span(looks.idle!)} untouched`;
  return `shuffle: the looks in shuffle play at random, ${eachText(looks)} each; ${wait}`;
}

/** The look whose edits `unsaved` counts: the current one, else the made one. */
export function edited(looks: LooksState): string | null {
  return looks.current ?? looks.made;
}

const NAME = /^[A-Za-z0-9][A-Za-z0-9 _-]{0,31}$/;

/** What a look name needs, or null when `name` is one: the engine's rule (pewpew.aura.book.check_name). */
export function nameHint(name: string): string | null {
  return !name || NAME.test(name) ? null : "letters, digits, space, _ or -";
}

/** A name no look has for a copy of `stem`: `stem` when free, else counted on as the engine counts a
 * save's offered name (pewpew.aura.looks offered): a name that ends in a number by that number (`surprise 4`),
 * another by one put after it (`tide 2`). */
export function freeName(looks: LooksState, stem: string): string {
  const taken = new Set(looks.items.map((item) => item.name));
  if (!taken.has(stem)) return stem;
  const counted = /^(.*\D) (\d{1,3})$/.exec(stem);
  const base = counted ? counted[1]! : stem.slice(0, 28);
  for (let k = counted ? Number(counted[2]) + 1 : 2; ; k++) if (!taken.has(`${base} ${k}`)) return `${base} ${k}`;
}

/** A look's own fade in words, as its settings show it: `own fade: 4 s`. */
export function ownFadeText(seconds: number): string {
  return `own fade: ${fadeText(seconds)}`;
}

/** The look a typed name means (trimmed), or undefined. */
export function findLook(looks: LooksState | null, name: string): LookItem | undefined {
  const key = name.trim();
  return looks?.items.find((item) => item.name === key);
}

/** The fades a look can take, in seconds. */
export const FADE_SECONDS: readonly number[] = [0, 0.5, 1, 2, 3, 5, 10, 30];

/** A fade in words: `instant`, `2 s`. */
export function fadeText(seconds: number): string {
  return seconds === 0 ? "instant" : `${seconds} s`;
}

/** The fade a press on a look takes: "stored" uses each look's own, as saved. Each names what it sets,
 * short, since a native list is as wide as its widest choice. */
export const FADES: readonly { readonly value: string; readonly label: string }[] = [
  { value: "stored", label: "fade: as saved" },
  ...FADE_SECONDS.map((s) => ({ value: String(s), label: `fade: ${fadeText(s)}` })),
];

export function fadeSeconds(choice: string): number | null {
  return choice === "stored" ? null : Number(choice);
}
