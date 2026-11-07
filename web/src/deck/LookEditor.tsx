import { Field } from "@ark-ui/react/field";
import { useRef, useState } from "react";
import { cycleText, deleteReason, FADE_SECONDS, findLook, freeName, holdReason, nameHint, ownFadeText, type LooksState } from "../aura/looks";
import type { TriggersState } from "../aura/triggers";
import { useRefusal, useSender, type Refusal } from "../wire/store";
import { Button } from "../design/Button";
import { DisclosureButton, DisclosureNote, useDisclosure } from "../design/Disclosure";
import { Icon } from "../design/Icon";
import { Select } from "../design/Select";
import { Switch } from "../design/Switch";
import { disarmAll } from "../design/useArm";
import { useOnChange } from "../design/useOnChange";
import type { Awaited } from "./LookPanel";

/** The engine's latest `refusal`, shown until the list of looks or `key` changes. */
function useShown(refusal: Refusal | null, looks: LooksState, key: unknown): Refusal | null {
  const [shown, setShown] = useState<Refusal | null>(null);
  useOnChange(refusal, () => setShown(refusal));
  // A save, delete or cycle that went through changes the list: the refusal is over.
  useOnChange(looks.items, () => setShown(null));
  useOnChange(key, () => setShown(null));
  return shown;
}

/** "save as new…": a new name for what plays, one no look has (`tide 2`), unless someone is typing in the
 * box; it says what a name needs as it is typed. "save as new" saves it under the name; a name a look has
 * makes it "overwrite", in two presses; Enter in the box presses it, and `onSave` gets what the save waits
 * for. Whether the look holds the brightness (`master`) goes with it. While what plays is a draft (a made
 * look), the box starts empty, the name it offers shown in it, and an empty box keeps it
 * under that name, as the header's save does. It is the header's form, so its button is secondary: save
 * stays the header's one primary. While a cue holds a look, a save waits and says why: what plays is not
 * the operator's. */
export function LookEditor({ looks, triggers, master, onSave }: { looks: LooksState; triggers: TriggersState | null; master: string; onSave(done: Awaited): void }) {
  const sender = useSender();
  const following = looks.current ? freeName(looks, looks.current) : "";
  const [name, setName] = useState(following);
  const [typing, setTyping] = useState(false);
  const [withMaster, setWithMaster] = useState(true);
  const save = useRef<HTMLButtonElement>(null);
  useOnChange(following, () => {
    if (!typing) setName(following);
  });
  const trimmed = name.trim();
  const refusal = useRefusal("save");
  const shown = useShown(refusal, looks, name);
  const item = findLook(looks, name);
  const hint = nameHint(trimmed);
  const held = holdReason(triggers, "save");
  return (
    <Field.Root className="look-editor fields look-form" aria-label="save as new" invalid={shown !== null || hint !== null}>
      <div className="row wrap">
        <Field.Input
          className="look-name"
          value={name}
          maxLength={32}
          placeholder={looks.offered ?? "look name"}
          autoComplete="off"
          autoCapitalize="off"
          spellCheck={false}
          aria-label="look name"
          enterKeyHint="done"
          onFocus={() => setTyping(true)}
          onBlur={() => setTyping(false)}
          onChange={(e) => {
            disarmAll();
            setName(e.currentTarget.value);
          }}
          onKeyDown={(e) => {
            if (e.key !== "Enter") return;
            e.preventDefault();
            save.current?.click();
          }}
        />
        <Button
          ref={save}
          disabled={(!trimmed && !looks.offered) || hint !== null || held !== null}
          confirm="again to overwrite"
          twoPress={!!item}
          disarmOn={refusal}
          onPress={() => {
            onSave((l) => (l.current !== null && (!trimmed || l.current === trimmed) && !l.changed ? `${l.current} saved` : null));
            sender.send({ type: "save", name: trimmed || null, fade: null, master: withMaster });
          }}
        >
          {item ? "overwrite" : "save as new"}
        </Button>
      </div>
      <Switch checked={withMaster} onChange={setWithMaster}>
        include brightness {master}
      </Switch>
      {held && <p className="note">{held}</p>}
      <Field.ErrorText>{shown?.reason ?? hint}</Field.ErrorText>
    </Field.Root>
  );
}

/** The current look's settings, behind its "⋯": its own fade, which a press at "fade: as saved" and shuffle
 * take into it, whether shuffle plays it (the "?" after its words says what shuffle is and its timings), then
 * its actions on one row:
 * "save as new…" (`onSaveAs`), and at the column's edge revert, the saved look again with no fade, while it
 * is changed, and delete, last; each of those two in two presses. The fade, shuffle and delete act at once on the file alone, leaving unsaved edits unsaved;
 * while a cue holds a look, they wait and say why. Delete is off while a cue plays the look, and a press
 * says why at once. A revert or a delete gives `onDone` what it waits for. A refusal, or why delete is off,
 * is an alert: focus stays on what was pressed. */
export function LookSettings({ looks, triggers, onSaveAs, onDone }: { looks: LooksState; triggers: TriggersState | null; onSaveAs(): void; onDone(done: Awaited): void }) {
  const sender = useSender();
  const current = findLook(looks, looks.current ?? "");
  const refusal = useRefusal("fade", "delete", "cycle");
  const shown = useShown(refusal, looks, looks.current);
  const [told, setTold] = useState<string | null>(null);
  const about = useDisclosure();
  useOnChange(looks.current, () => setTold(null));
  if (!current) return null;
  const { name } = current;
  const held = holdReason(triggers, "change it");
  const cued = deleteReason(triggers, name);
  const reason = told ?? shown?.reason;
  const fades = FADE_SECONDS.includes(current.fade) ? FADE_SECONDS : [...FADE_SECONDS, current.fade].sort((a, b) => a - b);
  return (
    <div className="look-editor fields look-settings" role="group" aria-label={`${name} settings`}>
      <Select
        items={fades.map((s) => ({ value: String(s), label: ownFadeText(s) }))}
        value={String(current.fade)}
        disabled={held !== null}
        onChange={(s) => sender.send({ type: "fade", name, fade: Number(s) })}
        label={`${name}'s own fade`}
      />
      <Switch
        checked={current.cycle}
        disabled={held !== null}
        onChange={(on) => sender.send({ type: "cycle", name, on })}
        after={<DisclosureButton disclosure={about} label="about shuffle" />}
      >
        <Icon name="cycle" /> {name} in shuffle
      </Switch>
      <DisclosureNote disclosure={about}>{cycleText(looks)}</DisclosureNote>
      <div className="row wrap look-lossy">
        <Button variant="tertiary" onPress={onSaveAs}>
          save as new…
        </Button>
        {looks.changed && (
          <Button
            variant="tertiary"
            confirm="again to revert"
            onPress={() => {
              onDone((l) => (l.current === name && !l.changed ? `${name} reverted` : null));
              sender.send({ type: "recall", name, fade: 0 });
            }}
          >
            revert
          </Button>
        )}
        <Button
          variant="tertiary"
          tone="danger"
          className="delete"
          disabled={held !== null}
          aria-disabled={cued !== null || undefined}
          confirm="again to delete"
          twoPress={cued === null}
          disarmOn={refusal}
          onPress={() => {
            if (cued) return setTold(cued);
            onDone((l) => (findLook(l, name) ? null : `${name} deleted`));
            sender.send({ type: "delete", name });
          }}
        >
          delete
        </Button>
      </div>
      {held && <p className="note">{held}</p>}
      {reason && (
        <p className="refusal" role="alert">
          {reason}
        </p>
      )}
    </div>
  );
}
