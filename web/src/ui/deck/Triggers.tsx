import { useEffect, useState } from "react";
import { armable, cueDoes, lastText, type Outcome, type TriggersState } from "../../domain/aura/triggers";
import { useSender } from "../../infra/wire/store";
import { ToggleButton } from "../common/Button";
import { DisclosureButton, DisclosureNote, useDisclosure } from "../common/Disclosure";
import { Icon } from "../common/Icon";
import { FINE_POINTER, useMedia } from "../common/useMedia";
import { useOnChange } from "../common/useOnChange";
import { Cues } from "./Cues";

/** What the cues are, for the deck's "⋯", by the toggle that turns them on. */
export const CUES_ABOUT = "cues: a cue plays a look briefly, then comes back; room events (buttons, sensors) fire them";

/** What the deck's "⋯" says of the cues: what they are, and while on, what the buttons do. */
export function cuesAbout(triggers: TriggersState): string {
  return `${CUES_ABOUT}${triggers.armed ? "; each cue button fires one" : ""}`;
}

/** "cues on", behind the deck's "⋯": a toggle that turns the cues on in one press and off in two, amber
 * while on. Absent when there are no cues. The top bar says while they are on. */
export function CuesOn({ triggers }: { triggers: TriggersState | null }) {
  const sender = useSender();
  if (!armable(triggers)) return null;
  const { armed } = triggers;
  return (
    <ToggleButton
      className="trigger-arm"
      tone="accent"
      pressed={armed}
      confirmOff="again to turn off"
      disarmOn={armed}
      onPressedChange={(on) => sender.send({ type: "arm", on })}
    >
      cues on
    </ToggleButton>
  );
}

/** What the cues do, a line each, for the cues' note on touch. */
export function cuesDo(triggers: TriggersState): readonly string[] {
  return triggers.names.map((name) => cueDoes(name, triggers.cues));
}

/** How long a cue's outcome stands in place of what the cues do. */
const OUTCOME_MS = 4000;

const SILENT: Outcome = { text: "", tick: false };

/** While cues are on, a row of them: a button per cue, then what each does, wrapping, on its line; an
 * event judged while the row shows puts its outcome there for OUTCOME_MS, in the same room, so it moves
 * nothing; an outcome from before the row showed never does. On touch, where the line is short, what each
 * does waits behind its "?", in a note under the row, and a fire that went through is its name and a ✓. */
export function CuesRow({ triggers }: { triggers: TriggersState | null }) {
  const fine = useMedia(FINE_POINTER);
  const about = useDisclosure();
  const [said, setSaid] = useState(SILENT);
  // The store keeps an event as it was until another is judged (`share`).
  const last = triggers?.last ?? null;
  useOnChange(last, () => setSaid(lastText(last, !fine, triggers?.cues)));
  useOnChange(triggers?.armed, () => setSaid(SILENT));
  useEffect(() => {
    if (!said.text) return;
    const id = setTimeout(() => setSaid(SILENT), OUTCOME_MS);
    return () => clearTimeout(id);
  }, [said, last]);
  if (!triggers?.armed) return null;
  const does = cuesDo(triggers);
  return (
    <div className="cues-group">
      <div className="row cues">
        <Cues triggers={triggers} />
        <span className="note last" title={does.join(" · ") || undefined}>
          {fine && (
            <span className="cue-does" aria-hidden="true" data-out={!!said.text || undefined}>
              {does.join(" · ")}
            </span>
          )}
          <span role="status">
            {said.text}
            {said.tick && (
              <>
                <Icon name="check" />
                <span className="sr-only"> fired</span>
              </>
            )}
          </span>
        </span>
        {!fine && <DisclosureButton disclosure={about} label="about the cues" />}
      </div>
      {!fine && (
        <DisclosureNote disclosure={about}>
          {does.map((line) => (
            <p key={line}>{line}</p>
          ))}
        </DisclosureNote>
      )}
    </div>
  );
}
