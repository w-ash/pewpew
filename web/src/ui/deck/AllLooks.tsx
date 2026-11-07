import { useStandingAura } from "../../infra/wire/store";
import { DisclosureNote, useDisclosure } from "../common/Disclosure";
import { Panel } from "../common/Panel";
import { KEYS, LookTile } from "./Looks";

/** The id of the list of every look, which the deck's "all N ›" controls. */
export const ALL_LOOKS = "all-looks";

/** Every saved look, a row each in file order, in the side slot: the first nine with the key that plays
 * them (on a keyboard or a mouse), as the deck shows those nine. A press recalls a look as its tile does,
 * and the list stays open, so looks past the ninth play from here; its ✕ or Esc closes it. */
export function AllLooks({ onClose }: { onClose(): void }) {
  const aura = useStandingAura();
  const note = useDisclosure();
  const looks = aura?.looks;
  return (
    <Panel id={ALL_LOOKS} title="looks" onClose={onClose}>
      <DisclosureNote disclosure={note} live />
      <ul className="all-looks">
        {looks?.items.map((item, i) => (
          <li key={item.name}>
            <LookTile looks={looks} triggers={aura?.triggers ?? null} item={item} note={note} hotkey={KEYS[i]} flat>
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
