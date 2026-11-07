import { useEffect, useId, useRef, useState, type KeyboardEvent, type MouseEvent } from "react";
import { holdReason, pendingText, saveOf, type LooksState, type Save } from "../../domain/aura/looks";
import { nowOf } from "../../domain/aura/aura";
import { useRefusal, useSender, useStandingAura, useWire } from "../../infra/wire/store";
import { Badge } from "../common/Badge";
import { Button, IconButton } from "../common/Button";
import { ChangedMark } from "../common/ChangedMark";
import { DisclosureNote, useDisclosure } from "../common/Disclosure";
import { onEngineHost } from "../common/host";
import { pressable, useShortcuts } from "../common/shortcuts";
import { useHeightVar } from "../common/useHeightVar";
import { useOnChange } from "../common/useOnChange";
import { LookKnobs, usePanel } from "../params/ParamPanel";
import { failedText } from "../status/StatusBar";
import { LookEditor, LookSettings } from "./LookEditor";

type Open = "save" | "settings" | null;

/** What a save or a delete waits for: the line that says it went through, once the looks show it, else null. */
export type Awaited = (looks: LooksState) => string | null;

/** Why a run without a looks file cannot save. */
const NO_LOOKS = "this run can't keep looks";

/** The look in the room, first in the editor. Its header stays at the slot's top at every depth, its height
 * measured for what pins under it: its name, the only display text, whole, which gives way first on a narrow
 * screen, onto more lines; "· changed" while it is changed since saved, or ✦ draft while what plays is no
 * saved look (a made look, by its label, or a pattern picked, by the name a save gives it); then the
 * header's one primary, save, shown only while there is something to save (RA-27b §4 B): one press saves the
 * edits into the look, or keeps the draft under the name it offers, each keeping the look's own fade and its
 * choice of holding the brightness. With MAX_LOOKS saved, a draft's save is off, and a press says why under
 * the header. While a layer fails, save says so and takes two, as the save keeps what fails. Its ▾ opens
 * "save as new…" in place; the look's "⋯" opens its settings: its own fade, whether shuffle plays it, then
 * save as new…, revert (while changed) and delete. Each form opens in view, and Esc closes it, focus back on its
 * opener; "save as new…" takes focus to the name box, its text selected, and while it is open, keys on it or
 * its opener are typing, never shortcuts. `k` presses save, or, with nothing to save, says why under the
 * header. Once the engine has made a save, a revert or a delete, it is announced and the open form closes.
 * While a cue holds a look, or a recall waits for the running fade, the header says so and there is no save,
 * and what is under it waits, inert: edits there would be lost when the hold ends or the recall lands.
 * Without a looks file the header says the look cannot be saved, and on the laptop how to start a run that
 * can. Then the look's main knobs. Without a looks file or main knobs, there is no block. Across a reconnect
 * the last aura state stands in (`useStandingAura`), so an engine restart keeps the editor, its typed name and its
 * switches. Its title (`titleId`, given) names the region the editor is. */
export function LookPanel({ titleId: given }: { titleId?: string }) {
  const aura = useStandingAura();
  const sender = useSender();
  const [open, setOpen] = useState<Open>(null);
  const [saving, setSaving] = useState(false);
  const [awaited, setAwaited] = useState<Awaited | null>(null);
  const [said, setSaid] = useState("");
  const why = useDisclosure();
  // Whether the form opened last takes the name box first, and what opened it, which Esc goes back to.
  const naming = useRef(false);
  const opener = useRef<HTMLElement | null>(null);
  const saveButton = useRef<HTMLButtonElement>(null);
  const forms = useRef<HTMLDivElement>(null);
  const head = useHeightVar("--head-h");
  const ownTitle = useId();
  const titleId = given ?? ownTitle;
  const saveId = useId();
  const settingsId = useId();
  const { view } = usePanel(null);
  const failing = useWire((s) => failedText(s.error, s.aura?.stack.layers ?? []));
  const refusal = useRefusal("save");
  const looks = aura?.looks ?? null;
  const save: Save = looks ? saveOf(looks, aura?.triggers ?? null) : { kind: "none", why: NO_LOOKS };
  // Once made, a save, revert or delete closes the open form: what opened it (a draft's ▾) may be gone.
  useOnChange(looks, () => {
    const line = looks && awaited?.(looks);
    if (!line) return;
    setAwaited(null);
    setSaid(line);
    setOpen(null);
  });
  useOnChange(useRefusal("save", "delete"), () => setAwaited(null));
  // A refusal of the header's save (64 looks, a file that cannot be written) shows under it; the form says
  // its own.
  useOnChange(refusal, () => {
    if (refusal && open !== "save") why.show(refusal.reason);
  });
  useShortcuts([
    {
      hotkey: "k",
      label: "save the look playing",
      action: () => (save.kind !== "none" && pressable(saveButton.current) ? saveButton.current!.click() : why.toggle(save.kind === "none" ? save.why : "")),
    },
  ]);
  useEffect(() => {
    if (!open) return;
    // Only the slot scrolls, never the page around it: the form starts under the pinned header.
    const el = forms.current, slot = el?.closest<HTMLElement>(".slot");
    if (el && slot) slot.scrollTop += el.getBoundingClientRect().top - slot.getBoundingClientRect().top - (parseFloat(getComputedStyle(slot).scrollPaddingTop) || 0);
    if (!naming.current) return;
    const box = forms.current?.querySelector<HTMLInputElement>(".look-name");
    box?.focus({ preventScroll: true });
    box?.select();
  }, [open]);
  if (!aura) return null;
  const { triggers } = aura;
  if (!looks && !view.front.length && !view.signals.length) return null;
  const now = nowOf(aura);
  const current = looks?.current ?? null;
  const held = holdReason(triggers, "edit") ?? pendingText(looks);
  // Opens `which` from the button pressed, closing it when it is open; "save as new…" goes into the name box.
  const toggle = (which: Exclude<Open, null>) => (click?: MouseEvent<HTMLButtonElement>) => {
    opener.current = click?.currentTarget ?? opener.current;
    naming.current = which === "save";
    setOpen(open === which ? null : which);
  };
  const expect = (done: Awaited) => {
    setSaid("");
    setAwaited(() => done);
  };
  // A form's save, revert or delete: the form goes once the engine has made it, so focus waits on what
  // opened the forms.
  const settled = (done: Awaited) => {
    opener.current?.focus();
    expect(done);
  };
  const press = () => {
    if (save.kind === "none") return;
    why.close();
    if (save.kind === "over") {
      const { name } = save;
      expect((l) => (l.current === name && !l.changed ? `${name} saved` : null));
      sender.send({ type: "save", name, fade: null, master: null });
      return;
    }
    // A draft: the engine names it, as it offers, and answers once it is saved.
    setSaving(true);
    expect((l) => (l.current !== null ? `${l.current} saved` : null));
    void sender.ask({ type: "save", name: null, fade: null, master: null }).finally(() => setSaving(false));
  };
  const esc = (e: KeyboardEvent) => {
    if (e.key !== "Escape" || !open) return;
    e.stopPropagation();
    opener.current?.focus();
    setOpen(null);
  };
  const typing = open === "save" || undefined;
  return (
    <>
      <div ref={head} className="block-head look-head" onKeyDown={esc}>
        <h2 id={titleId} className="look-title t-display" tabIndex={-1}>
          <span className="look-name-text">{now.name}</span>
          {now.changed && <ChangedMark />}
          {now.draft && (
            <Badge icon="sparkle">
              <span className="sr-only">, </span>draft
            </Badge>
          )}
        </h2>
        {looks ? (
          <div className="look-actions">
            {save.kind !== "none" && (
              <div className="split-button" role="group" aria-label="save">
                <Button
                  ref={saveButton}
                  variant="primary"
                  // Only while a layer fails: the confirm's words would widen it at rest.
                  confirm={failing ? "again to save failing" : undefined}
                  say={failing ? `save failing? ${failing}; press again to save ${save.name} as it is` : undefined}
                  busy={saving}
                  reason={save.kind === "draft" ? save.full : null}
                  note={why}
                  title={save.kind === "over" ? `save the edits into ${save.name}` : `keep ${save.name}`}
                  onPress={press}
                >
                  save
                </Button>
                <IconButton
                  variant="primary"
                  icon="caret"
                  label="save as new…"
                  aria-expanded={open === "save"}
                  aria-controls={saveId}
                  data-own-keys={typing}
                  onPress={toggle("save")}
                />
              </div>
            )}
            {current !== null && (
              <IconButton
                icon="more"
                label="look settings"
                aria-expanded={open === "settings"}
                aria-controls={settingsId}
                onPress={toggle("settings")}
              />
            )}
          </div>
        ) : (
          <span className="note">not saved: {NO_LOOKS}{onEngineHost() && " (start it with --looks)"}</span>
        )}
        {held && (
          <p className="note held-note" role="status" tabIndex={-1}>
            {held}
          </p>
        )}
        <DisclosureNote disclosure={why} live />
      </div>
      <div className="block look-block" inert={!!held} onKeyDown={esc}>
        <div ref={forms} className="look-forms" data-own-keys={typing}>
          {looks && (
            <div id={saveId} hidden={open !== "save"}>
              <LookEditor
                looks={looks}
                triggers={triggers}
                master={now.master}
                onSave={settled}
              />
            </div>
          )}
          {looks && current !== null && (
            <div id={settingsId} hidden={open !== "settings"}>
              <LookSettings
                looks={looks}
                triggers={triggers}
                onSaveAs={() => {
                  naming.current = true;
                  setOpen("save");
                }}
                onDone={settled}
              />
            </div>
          )}
        </div>
        <LookKnobs />
      </div>
      <p className="sr-only" role="status">
        {said}
      </p>
    </>
  );
}
