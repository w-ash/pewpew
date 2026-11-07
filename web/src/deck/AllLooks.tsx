import type { LooksState } from "../aura/looks";
import type { TriggersState } from "../aura/triggers";
import { DisclosureNote, useDisclosure } from "../design/Disclosure";
import { Panel } from "../design/Panel";
import { ALL_LOOKS, KEYS, LookTile, type PlayLook } from "./Looks";

/** Every look of `looks`, a row each in order, in the side slot: the first nine with the key that plays them
 * (on a keyboard or a mouse), as the deck shows those nine. A press plays a look as its tile does, and the
 * list stays open, so looks past the ninth play from here; its ✕ or Esc closes it. */
export function AllLooks({ looks, play, triggers, onClose }: { looks: LooksState | null; play: PlayLook; triggers: TriggersState | null; onClose(): void }) {
  const note = useDisclosure();
  return (
    <Panel id={ALL_LOOKS} title="looks" onClose={onClose}>
      <DisclosureNote disclosure={note} live />
      <ul className="all-looks">
        {looks?.items.map((item, i) => (
          <li key={item.name}>
            <LookTile looks={looks} play={play} triggers={triggers} item={item} note={note} hotkey={KEYS[i]} flat>
              {i < KEYS.length && (
                <kbd className="key t-caption" aria-hidden="true">
                  {KEYS[i]}
                </kbd>
              )}
            </LookTile>
          </li>
        ))}
      </ul>
    </Panel>
  );
}
