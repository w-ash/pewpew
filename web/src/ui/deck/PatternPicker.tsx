import { ToggleGroup } from "@ark-ui/react/toggle-group";
import { useId, useRef, useState } from "react";
import { unsaved } from "../../domain/aura/looks";
import { patternLabels } from "../../domain/stack/catalog";
import { neighbour, patternList, type Patterns } from "../../domain/aura/aura";
import { useRefusal, useSender, useWire } from "../../infra/wire/store";
import { Select } from "../common/Select";
import { Tile } from "../common/Tile";
import { pressable, useShortcuts } from "../common/shortcuts";
import { FINE_POINTER, useMedia, WIDE } from "../common/useMedia";
import { useOnChange } from "../common/useOnChange";

interface Props extends Patterns {
  /** The layer a pick runs on; null for the bottom one. */
  readonly layer?: string | null;
  /** A list even wide with a mouse: for a narrow place. */
  readonly narrow?: boolean;
  /** Whether [ and ] step through the patterns: for a lone pattern, which a pick replaces as it is. */
  readonly keys?: boolean;
  /** Take focus once shown (`Select`). */
  readonly autoFocus?: boolean;
}

/** The patterns a pick can run on `layer`, each at its defaults with no fade, each by what the page calls
 * it (`patternLabels`; its file's name in its tooltip), under their label,
 * the running one's line from the catalog after them, or for a file of the author's own, that. A
 * pick waits for the engine's swap and shows as busy until then. Wide with a mouse, a row of
 * tiles, the running one pressed, which the arrow keys move between and Enter or Space
 * picks; elsewhere a list, so a pick on touch takes a deliberate second tap. With `keys`, [ and ] pick the one before or after, except
 * over a look with unsaved edits, which a key would lose. */
export function PatternPicker({ pattern, patterns, layer, narrow, keys, autoFocus }: Props) {
  const labelId = useId();
  const gist = useWire((s) => s.catalog?.cards.find((c) => c.kind === "pattern" && c.name === pattern)?.summary ?? "");
  const cards = useWire((s) => s.catalog?.cards);
  const sender = useSender();
  const edited = useWire((s) => unsaved(s.aura?.looks ?? null));
  const wide = useMedia(WIDE);
  const fine = useMedia(FINE_POINTER);
  const buttons = useRef<HTMLDivElement>(null);
  const list = useRef<HTMLDivElement>(null);
  const [pending, setPending] = useState<string | null>(null);
  useOnChange(useRefusal("pick"), () => setPending(null));
  useOnChange(useWire((s) => s.session), () => setPending(null));
  if (pending === pattern) setPending(null);
  const pick = (name: string | null) => {
    if (!name || name === pattern) return;
    setPending(name);
    sender.send({ type: "pick", name, layer: layer ?? null });
  };
  const enabled = () => !edited && pressable(buttons.current ?? list.current);
  useShortcuts(
    keys
      ? [
          { hotkey: "[", label: "previous pattern (not over unsaved edits)", action: () => pick(neighbour({ pattern, patterns }, -1)), enabled },
          { hotkey: "]", label: "next pattern (not over unsaved edits)", action: () => pick(neighbour({ pattern, patterns }, 1)), enabled },
        ]
      : [],
  );
  const labels = patternLabels(cards ?? []);
  const entries = patternList({ pattern, patterns }).map((e) => ({ ...e, label: labels.get(e.name) ?? e.name }));
  const own = !gist && pattern !== "custom" && !patterns.includes(pattern);
  const line = (gist || own) && <p className="note">{own ? "your own file, not in the gallery" : gist.replace(/\.$/, "")}</p>;
  if (narrow || !wide || !fine) {
    return (
      <div ref={list} className="pattern-pick">
        <span id={labelId} className="field-label">
          pattern
        </span>
        <Select
          items={entries.map((e) => ({ value: e.name, label: e.label, disabled: !e.pickable }))}
          value={pending ?? pattern}
          busy={pending !== null}
          onChange={pick}
          label="pattern"
          autoFocus={autoFocus}
        />
        {line}
      </div>
    );
  }
  return (
    <div className="pattern-pick">
      <span id={labelId} className="field-label">
        pattern
      </span>
      <ToggleGroup.Root
        ref={buttons}
        className="scroller"
        aria-labelledby={labelId}
        multiple
        value={[pattern]}
        onValueChange={(d) => pick(d.value.find((v) => v !== pattern) ?? null)}
        // Tab into the row lands on the pressed one, not the first (Zag's root focus).
        onFocusCapture={(e) => {
          const checked = e.currentTarget.querySelector<HTMLElement>('[aria-pressed="true"]:not(:disabled)');
          if (e.target !== e.currentTarget || !checked) return;
          e.stopPropagation();
          checked.focus();
        }}
      >
        {entries.map((e) => (
          <ToggleGroup.Item key={e.name} value={e.name} disabled={!e.pickable} asChild>
            <Tile name={e.label} title={e.label === e.name ? undefined : e.name} selected={e.name === pattern} busy={e.name === pending} />
          </ToggleGroup.Item>
        ))}
      </ToggleGroup.Root>
      {line}
    </div>
  );
}
