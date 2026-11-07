import { useRef, useState } from "react";
import { edited, unsaved, varyReason, type LooksState } from "../aura/looks";
import { nowOf, type AuraState } from "../aura/aura";
import type { ClientMessage } from "../wire/protocol";
import { useSender } from "../wire/store";
import { Button } from "../design/Button";
import type { Disclosure } from "../design/Disclosure";
import type { IconName } from "../design/Icon";
import { useOnChange } from "../design/useOnChange";
import { dropLine } from "./Looks";

/** One of the two buttons: its words and sign, its key and the key's line in the `?` list, what it sends,
 * why it cannot be pressed now, or null, and over unsaved edits what a first press shows and what its note
 * says the second does: surprise me drops the edits, vary this varies them. */
interface Ask {
  readonly text: string;
  readonly icon: IconName;
  readonly hotkey: string;
  readonly label: string;
  readonly message: ClientMessage;
  reason(looks: LooksState): string | null;
  readonly confirm: string;
  cost(text: string, looks: LooksState): string;
}

/** What a second press of vary this does over unsaved edits: varies what plays, edits and all. */
function varyLine(text: string, looks: LooksState): string {
  const look = edited(looks);
  if (!unsaved(looks) || !look) return "";
  return `press ${text} again to vary what plays; save first to keep these edits in ${look}`;
}

/** Each request asks for the engine's own next seed, and the default strength. */
const ASKS: readonly Ask[] = [
  {
    text: "surprise me", icon: "dice", hotkey: "s", label: "surprise me: a new look", message: { type: "surprise", seed: null },
    reason: () => null, confirm: "again to drop", cost: dropLine,
  },
  {
    text: "vary this", icon: "approx", hotkey: "m", label: "vary this: a look like the one playing",
    message: { type: "vary", strength: null, seed: null }, reason: varyReason, confirm: "again to vary", cost: varyLine,
  },
];

interface Props {
  readonly aura: AuraState;
  /** Null without a looks book: no edit is then kept, so no press takes two. */
  readonly looks: LooksState | null;
  /** The note under their row: why one is off, or what a second press does. */
  readonly note: Disclosure;
}

/** The make actions, on their own row under the saved looks: "surprise me", a new look for the room's map,
 * and "vary this", a look like the one playing, each fading in unsaved, a draft the look's header saves.
 * Over a look with unsaved edits, saved or made, each takes two presses, and the first opens `note` on what
 * the second does: surprise me drops the edits, vary this varies them, the saved look staying as saved. A
 * make takes the engine a second or more: the button pressed says so and both wait for the answer, keeping
 * focus, and the look that then plays is announced; a refusal goes to the status bar. A press on one that
 * cannot be pressed now says why in `note`. */
export function Variety({ aura, looks, note }: Props) {
  const sender = useSender();
  const [busy, setBusy] = useState<Ask | null>(null);
  const [told, setTold] = useState("");
  // Set at once, so a second press before the page draws the busy state sends nothing.
  const asking = useRef(false);
  const made = useRef(false);
  const playing = nowOf(aura).name;
  useOnChange(playing, () => {
    if (!made.current) return;
    made.current = false;
    setTold(`now playing ${playing}`);
  });
  const make = (ask: Ask) => {
    if (asking.current) return;
    asking.current = true;
    made.current = true;
    setBusy(ask);
    setTold("");
    void sender.ask(ask.message).finally(() => {
      asking.current = false;
      setBusy(null);
    });
  };
  return (
    <div className="variety" role="group" aria-label="make a look" aria-busy={busy !== null}>
      {ASKS.map((ask) => (
        <Button
          key={ask.hotkey}
          icon={ask.icon}
          confirm={ask.confirm}
          twoPress={busy === null && !!looks && unsaved(looks)}
          cost={looks ? ask.cost(ask.text, looks) : ""}
          disarmOn={busy}
          shortcut={{ hotkey: ask.hotkey, label: ask.label }}
          busy={busy === ask}
          aria-disabled={(busy !== null && busy !== ask) || undefined}
          reason={busy === null && looks ? ask.reason(looks) : null}
          note={note}
          onPress={() => make(ask)}
        >
          {busy === ask ? "making…" : ask.text}
        </Button>
      ))}
      <p className="sr-only" role="status">
        {told}
      </p>
    </div>
  );
}
