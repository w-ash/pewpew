import { useEffect, useId, useRef, useState, type KeyboardEvent } from "react";
import { favoriteLooks, sortedLooks, type LooksState } from "../aura/looks";
import type { TriggersState } from "../aura/triggers";
import { DisclosureNote, useDisclosure } from "../design/Disclosure";
import { Icon } from "../design/Icon";
import { Panel } from "../design/Panel";
import { ALL_LOOKS, KEYS, LookTile, type PlayLook } from "./Looks";

/** Every look of `looks`, a row each, alphabetically (`byName`), in the side slot: favorites carry a ★, and
 * the first nine of them the key that plays them (on a keyboard or a mouse), as the deck shows those nine. A
 * press plays a look as its tile does, and the list stays open, so any look plays from here; its ✕ or Esc
 * closes it.
 *
 * Above the list a search box follows the combobox pattern: typing keeps the looks whose name has the text
 * (case aside), ↑ and ↓ move the highlight, Enter presses the highlighted look as a press on its row does,
 * and Esc clears the box before a second Esc closes the list. The box takes focus when the list opens. */
export function AllLooks({ looks, play, triggers, onClose }: { looks: LooksState | null; play: PlayLook; triggers: TriggersState | null; onClose(): void }) {
  const note = useDisclosure();
  const [query, setQuery] = useState("");
  const [at, setAt] = useState(0);
  const box = useRef<HTMLInputElement>(null);
  const id = useId();
  const all = looks ? sortedLooks(looks) : [];
  const needle = query.trim().toLowerCase();
  const shown = needle ? all.filter((item) => item.name.toLowerCase().includes(needle)) : all;
  const keys = new Map((looks ? favoriteLooks(looks) : []).slice(0, KEYS.length).map((item, i) => [item.name, KEYS[i]] as const));
  const active = shown.length ? Math.min(at, shown.length - 1) : -1;
  const rowId = (i: number) => `${id}-${i}`;
  const activeName = shown[active]?.name ?? null;
  // Scroll only when the highlight moves to another look, not on every aura message.
  useEffect(() => {
    if (activeName !== null) document.getElementById(rowId(active))?.scrollIntoView?.({ block: "nearest" });
    // oxlint-disable-next-line react-hooks/exhaustive-deps -- the row index follows the highlighted name
  }, [activeName]);
  const onKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "ArrowDown" || e.key === "ArrowUp") {
      e.preventDefault();
      if (shown.length) setAt((active + (e.key === "ArrowDown" ? 1 : -1) + shown.length) % shown.length);
    } else if (e.key === "Enter") {
      e.preventDefault();
      if (active >= 0) document.getElementById(rowId(active))?.querySelector("button")?.click();
    } else if (e.key === "Escape" && query) {
      e.preventDefault(); // the panel closes on an Esc nobody handled
      setQuery("");
      setAt(0);
    }
  };
  return (
    <Panel id={ALL_LOOKS} title="looks" onClose={onClose} focusRef={box}>
      <label className="all-looks-search">
        <Icon name="search" />
        <input
          ref={box}
          type="text"
          role="combobox"
          aria-label="search looks"
          aria-expanded="true"
          aria-controls={`${id}-list`}
          aria-autocomplete="list"
          aria-activedescendant={active >= 0 ? rowId(active) : undefined}
          placeholder="search looks"
          value={query}
          autoComplete="off"
          autoCapitalize="off"
          spellCheck={false}
          enterKeyHint="go"
          onChange={(e) => {
            setQuery(e.currentTarget.value);
            setAt(0);
          }}
          onKeyDown={onKeyDown}
        />
      </label>
      <DisclosureNote disclosure={note} live />
      {all.length > 0 && !shown.length && (
        <p className="note" role="status">
          no look matches
        </p>
      )}
      <ul id={`${id}-list`} className="all-looks">
        {looks &&
          shown.map((item, i) => (
            <li key={item.name} id={rowId(i)} data-active={i === active || undefined}>
              <LookTile looks={looks} play={play} triggers={triggers} item={item} note={note} hotkey={keys.get(item.name)} favorite={looks.favorites.includes(item.name)} flat>
                {keys.has(item.name) && (
                  <kbd className="key t-caption" aria-hidden="true">
                    {keys.get(item.name)}
                  </kbd>
                )}
              </LookTile>
            </li>
          ))}
      </ul>
    </Panel>
  );
}
