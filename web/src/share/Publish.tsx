import { useState } from "react";
import { Button } from "../design/Button";
import { Panel } from "../design/Panel";
import { Switch } from "../design/Switch";
import type { ExportedMessage } from "../wire/protocol";
import { useStandingAura, useWireContext } from "../wire/store";
import { askExport, postShare } from "./exporting";

/** What a visitor of the share can see, which the page says before it publishes. */
export const PUBLIC_NOTE = "This is public: anyone with the link sees this layout and these looks. Board addresses are removed.";

/** Over the confirmation: whose call it is. */
export const YOUR_CALL = "Read what this share makes public. What is right to make public is yours to decide, share by share.";

/** `value` when it is text, else "". */
const text = (value: unknown): string => (typeof value === "string" ? value : "");

/** The share `file` as it goes out: without its arrangement's public notes unless `notes`. The internal notes
 * never reach a share (pewpew.share). */
export function outgoing(file: Readonly<Record<string, unknown>>, notes: boolean): Readonly<Record<string, unknown>> {
  if (notes) return file;
  const { public_notes: _, ...arrangement } = (file.arrangement ?? {}) as Record<string, unknown>;
  return { ...file, arrangement };
}

/** Publish in the slot (capability "publish"): pick the saved looks to share (at first the current look
 * and the favorites), then "next" asks the engine for the share; then the page shows, as plain text,
 * everything the share makes public (the layout's name, its public notes, with a switch to leave them out,
 * and the looks' names) and where it goes, and "publish" posts the share to the Gallery, which opens it in
 * a new tab. A refused export shows its reason here; "back" goes back to the picks. */
export default function PublishSlot({ onClose }: { onClose(): void }) {
  const wire = useWireContext();
  const looks = useStandingAura()?.looks ?? null;
  const [picked, setPicked] = useState<ReadonlySet<string> | null>(null);
  const [share, setShare] = useState<ExportedMessage | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [sent, setSent] = useState(false);
  const [withNotes, setWithNotes] = useState(true);
  const names = looks?.items.map((item) => item.name) ?? [];
  const chosen = picked ?? new Set(names.filter((n) => n === looks?.current || looks?.favorites.includes(n)));
  const chosenNames = names.filter((n) => chosen.has(n));
  const pick = (name: string, on: boolean) => {
    const next = new Set(chosen);
    if (on) next.add(name);
    else next.delete(name);
    setPicked(next);
  };
  const next = async () => {
    setBusy(true);
    setError(null);
    const answer = await askExport(wire, chosenNames, true);
    setBusy(false);
    if (typeof answer === "string") setError(answer);
    else if (!answer.gallery) setError("The engine named no Gallery to publish to.");
    else setShare(answer);
  };
  const gallery = share?.gallery ?? null;
  const arrangement = (share?.file.arrangement ?? {}) as Record<string, unknown>;
  const name = text(arrangement.name);
  const publicNotes = text(arrangement.public_notes);
  // The looks the share holds, as the engine wrote it.
  const shared = Object.keys(((share?.file.looks ?? {}) as { looks?: object }).looks ?? {});
  return (
    <Panel title="publish" onClose={onClose}>
      {share && gallery ? (
        <div className="fields">
          <p>{YOUR_CALL}</p>
          <p className="note">the layout's name</p>
          <p>{name || "(none)"}</p>
          {publicNotes && (
            <>
              <p className="note">its public notes</p>
              <p style={{ whiteSpace: "pre-wrap" }}>{withNotes ? publicNotes : "(left out of this share)"}</p>
              <Switch checked={withNotes} onChange={setWithNotes}>
                share the public notes
              </Switch>
            </>
          )}
          <p className="note">{shared.length === 1 ? "the look" : `the ${shared.length} looks`}</p>
          <p>{shared.join(", ")}</p>
          <p>{PUBLIC_NOTE}</p>
          <p className="note">To the Gallery at {new URL(gallery).host}.</p>
          <div className="row wrap">
            <Button
              variant="primary"
              onPress={() => {
                postShare(gallery, outgoing(share.file, withNotes));
                setSent(true);
              }}
            >
              publish
            </Button>
            <Button
              variant="tertiary"
              onPress={() => {
                setShare(null);
                setSent(false);
                setWithNotes(true);
              }}
            >
              back
            </Button>
          </div>
          {sent && (
            <p className="note" role="status">
              Sent: the Gallery opens the share in a new tab.
            </p>
          )}
        </div>
      ) : (
        <div className="fields">
          <p className="note">The looks to share with this layout:</p>
          {names.length ? (
            names.map((name) => (
              <Switch key={name} checked={chosen.has(name)} onChange={(on) => pick(name, on)}>
                {name}
              </Switch>
            ))
          ) : (
            <p className="note">No saved looks yet: save one to share it.</p>
          )}
          <div className="row wrap">
            <Button variant="secondary" busy={busy} disabled={!chosenNames.length} onPress={() => void next()}>
              next
            </Button>
          </div>
          {error && (
            <p className="note" role="alert">
              {error}
            </p>
          )}
        </div>
      )}
    </Panel>
  );
}
