import { useState } from "react";
import { Button } from "../design/Button";
import { Panel } from "../design/Panel";
import { Switch } from "../design/Switch";
import type { ExportedMessage } from "../wire/protocol";
import { useStandingAura, useWireContext } from "../wire/store";
import { askExport, postShare } from "./exporting";

/** What a visitor of the share can see, which the page says before it publishes. */
export const PUBLIC_NOTE = "This is public: anyone with the link sees this layout and these looks. Board addresses are removed.";

/** Publish in the slot (capability "publish"): pick the saved looks to share (at first the current look
 * and the favorites), then "next" asks the engine for the share; then the page says what becomes public
 * and where, and "publish" posts the share to the Gallery, which opens it in a new tab. A refused export
 * shows its reason here; "back" goes back to the picks. */
export default function PublishSlot({ onClose }: { onClose(): void }) {
  const wire = useWireContext();
  const looks = useStandingAura()?.looks ?? null;
  const [picked, setPicked] = useState<ReadonlySet<string> | null>(null);
  const [share, setShare] = useState<ExportedMessage | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [sent, setSent] = useState(false);
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
  return (
    <Panel title="publish" onClose={onClose}>
      {share && gallery ? (
        <div className="fields">
          <p>{PUBLIC_NOTE}</p>
          <p className="note">
            To the Gallery at {new URL(gallery).host}, with {chosenNames.length === 1 ? "1 look" : `${chosenNames.length} looks`}:{" "}
            {chosenNames.join(", ")}.
          </p>
          <div className="row wrap">
            <Button
              variant="primary"
              onPress={() => {
                postShare(gallery, share.file);
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
