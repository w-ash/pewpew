import { useRef, type CSSProperties, type KeyboardEvent, type ReactNode, type Ref } from "react";
import { edited, fadeSeconds, liveLook, lookStatus, unsaved, type LookItem, type LooksState } from "../../domain/aura/looks";
import type { TriggersState } from "../../domain/aura/triggers";
import { useSender } from "../../infra/wire/store";
import type { Disclosure } from "../common/Disclosure";
import { Icon, type IconName } from "../common/Icon";
import { Tile } from "../common/Tile";
import { useInView } from "../common/useInView";
import { pressable, useShortcuts } from "../common/shortcuts";
import { useFade } from "./fade";

/** Which looks a ↻ marks, when some are left out of shuffle: the fewer, those in it ("in") or those left
 * out ("out", the ↻ slashed); null when every look is in it, or none. */
export function cycleMarks(looks: LooksState): "in" | "out" | null {
  const out = looks.items.filter((item) => !item.cycle).length;
  const n = looks.items.length;
  return out === 0 || out === n ? null : out < n - out ? "out" : "in";
}

/** A sign the looks show, and what it means. */
export interface Mark {
  readonly icon: IconName;
  readonly slashed?: boolean;
  readonly text: string;
}

/** What the signs the looks show now mean, for the deck's "⋯": ↻ while some are left out of shuffle, ↩
 * while a cue holds another look. */
export function looksAbout(looks: LooksState, triggers: TriggersState | null): readonly Mark[] {
  const cyc = cycleMarks(looks);
  const now = looks.current ? lookStatus(looks, triggers, looks.current) : null;
  const marks: Mark[] = [];
  if (cyc === "in") marks.push({ icon: "cycle", text: "in shuffle" });
  if (cyc === "out") marks.push({ icon: "cycle", slashed: true, text: "not in shuffle" });
  if (now?.returnsTo) marks.push({ icon: "return", text: "returns here after the cue" });
  return marks;
}

/** A sign, slashed when it says "not". */
export function MarkSign({ mark }: { mark: Pick<Mark, "icon" | "slashed"> }) {
  return (
    <span className="cyc" data-out={mark.slashed || undefined} aria-hidden="true">
      <Icon name={mark.icon} />
    </span>
  );
}

/** The keys that press the first nine looks, in file order: the deck shows those nine. */
export const KEYS = ["1", "2", "3", "4", "5", "6", "7", "8", "9"];

const MOVES: Readonly<Record<string, (i: number, n: number) => number>> = {
  ArrowRight: (i, n) => (i + 1) % n,
  ArrowDown: (i, n) => (i + 1) % n,
  ArrowLeft: (i, n) => (i - 1 + n) % n,
  ArrowUp: (i, n) => (i - 1 + n) % n,
  Home: () => 0,
  End: (_, n) => n - 1,
};

/** What a second press of `pressed` (a look's name, or surprise me) does over unsaved edits: drops them.
 * Empty when there are none. */
export function dropLine(pressed: string, looks: LooksState): string {
  const look = edited(looks);
  if (!unsaved(looks) || !look) return "";
  if (pressed === looks.current) return `press ${pressed} again to drop its edits`;
  return `press ${pressed} again to drop ${looks.current ? `the edits to ${look}` : `${look} and its edits`}`;
}

interface LookTileProps {
  readonly looks: LooksState;
  readonly triggers: TriggersState | null;
  readonly item: LookItem;
  /** Where a first press over unsaved edits says what the second drops. */
  readonly note: Disclosure;
  /** A row of a list, not a tile of the deck. */
  readonly flat?: boolean;
  readonly tabIndex?: number;
  /** The key that plays it, 1–9, for assistive tech. */
  readonly hotkey?: string | undefined;
  readonly ref?: Ref<HTMLButtonElement> | undefined;
  /** Signs after the ones a look has: its key, in the list. */
  readonly children?: ReactNode;
}

/** One saved look: a press recalls it over the chosen fade. The one playing is amber with a ●. Over unsaved
 * edits a recall takes two presses, as it would lose them, and the first opens `note` on what the second
 * does, until it disarms. A look fading in fills a bar along its foot. While a cue holds a look, that one is
 * held, and ↩ marks the current one, which the aura returns to, in its corner: neither moves it. When some
 * are left out of shuffle, ↻ marks the fewer: those it plays, or, slashed, those it leaves out. */
export function LookTile({ looks, triggers, item, note, flat, tabIndex, hotkey, ref, children }: LookTileProps) {
  const sender = useSender();
  const [fade] = useFade();
  const st = lookStatus(looks, triggers, item.name);
  const marks = cycleMarks(looks);
  const marked = (marks === "in" && item.cycle) || (marks === "out" && !item.cycle);
  const edits = unsaved(looks);
  return (
    <Tile
      ref={ref}
      flat={flat}
      // Confirming, the look keeps its name: the note says what the second press drops.
      confirm="again to drop edits"
      twoPress={edits}
      disarmOn={edits}
      cost={dropLine(item.name, looks)}
      note={note}
      tabIndex={tabIndex}
      aria-keyshortcuts={hotkey}
      live={st.live}
      held={st.held}
      busy={st.pending}
      aria-pressed={st.live}
      data-fading={st.fading !== null || undefined}
      data-returns={st.returnsTo || undefined}
      style={{ "--progress": `${Math.round((st.fading ?? 0) * 100)}%` } as CSSProperties}
      aria-label={[item.name, marked && (item.cycle ? "in shuffle" : "not in shuffle"), st.returnsTo && "returns here after the cue"].filter(Boolean).join(", ")}
      onPress={() => sender.send({ type: "recall", name: item.name, fade: fadeSeconds(fade) })}
      name={item.name}
    >
      {marked && <MarkSign mark={{ icon: "cycle", slashed: !item.cycle }} />}
      {st.returnsTo && (
        <span className="returns" aria-hidden="true">
          <Icon name="return" />
        </span>
      )}
      {children}
    </Tile>
  );
}

/** The first nine saved looks, in file order, as tiles (`LookTile`), under the deck's "looks" caption
 * (`labelledBy`); the list of every look holds the rest. The row is a toolbar, one tab stop: the arrow keys,
 * Home and End move between its looks. 1–9 press a look as a tap does. */
export function Looks({ looks, triggers, note, labelledBy }: { looks: LooksState; triggers: TriggersState | null; note: Disclosure; labelledBy: string }) {
  const row = useRef<HTMLDivElement>(null);
  const liveName = liveLook(looks, triggers);
  const live = useInView<HTMLButtonElement>(liveName);
  const tiles = () => [...(row.current?.querySelectorAll<HTMLButtonElement>(":scope > button") ?? [])];
  useShortcuts(
    KEYS.map((key, i) => ({
      hotkey: key,
      label: i === 0 ? "play one of the first nine looks (press twice to drop edits)" : "",
      keys: "1–9",
      action: () => tiles()[i]?.click(),
      enabled: () => i < looks.items.length && pressable(row.current),
    })),
  );
  if (!looks.items.length) return <p className="scroller empty note">No looks yet. Surprise me, then save one you like.</p>;
  const shown = looks.items.slice(0, KEYS.length);
  const stop = Math.max(shown.findIndex((item) => item.name === liveName), 0);
  const roam = (e: KeyboardEvent<HTMLDivElement>) => {
    const move = MOVES[e.key];
    const buttons = tiles();
    const at = buttons.indexOf(document.activeElement as HTMLButtonElement);
    if (!move || at < 0) return;
    e.preventDefault();
    buttons[move(at, buttons.length)]?.focus();
  };
  return (
    <div ref={row} className="scroller looks" role="toolbar" aria-labelledby={labelledBy} onKeyDown={roam}>
      {shown.map((item, i) => (
        <LookTile
          key={item.name}
          ref={item.name === liveName ? live : undefined}
          looks={looks}
          triggers={triggers}
          item={item}
          note={note}
          tabIndex={i === stop ? 0 : -1}
          hotkey={KEYS[i]}
        />
      ))}
    </div>
  );
}
