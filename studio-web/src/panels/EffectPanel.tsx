import { Variety } from "@pewpew/page/deck";
import {
  Block,
  DisclosureNote,
  Tile,
  TileRow,
  useDisclosure,
} from "@pewpew/page/design";
import { LookKnobs, LookSignals } from "@pewpew/page/params";
import {
  ADD,
  AddLayerPanel,
  LayerList,
  useLayerSelection,
} from "@pewpew/page/stack";
import { useSender, useStandingAura, useWire } from "@pewpew/page/wire";
import { useState } from "react";
import { useLooks } from "@/api/queries";
import type { LookDocument } from "@/api/types";
import { useSession } from "@/store/session";

/** The example looks (`GET /api/looks`), a tile each, in a row that is one tab stop: a press fades the
 * session to it over its own fade, and waits for the engine's answer. */
function ExampleLooks({ looks }: { looks: Record<string, LookDocument> }) {
  const sender = useSender();
  const connected = useWire((s) => s.connected);
  const [busy, setBusy] = useState<string | null>(null);
  const play = (name: string) => {
    const look = looks[name];
    if (!look || busy) return;
    setBusy(name);
    void sender
      .ask({ type: "look", look, fade: null })
      .finally(() => setBusy(null));
  };
  return (
    <TileRow className="looks" label="example looks">
      {Object.keys(looks).map((name, i) => (
        <Tile
          key={name}
          name={name}
          tabIndex={i === 0 ? 0 : -1}
          busy={busy === name}
          aria-disabled={
            !connected || (busy !== null && busy !== name) || undefined
          }
          onPress={() => play(name)}
        />
      ))}
    </TileRow>
  );
}

/**
 * The session's look, edited as the control page edits one: the example
 * looks, surprise me and vary this, then the look's main knobs, its layers,
 * each open with its own knobs, and its modulators. "+ layer" opens the cards
 * a layer is added from in the editor's place. Nothing is saved: the session
 * has no looks file.
 */
export function EffectPanel() {
  const aura = useStandingAura();
  const looks = useLooks();
  const watts = useSession((s) => s.watts);
  const selection = useLayerSelection();
  const [adding, setAdding] = useState(false);
  const made = useDisclosure();

  return (
    <div className="studio-panel">
      <Block className="fields" title="looks">
        {looks.data ? (
          <ExampleLooks looks={looks.data} />
        ) : (
          <p className="note">
            {looks.isError
              ? "The example looks could not be loaded."
              : "Loading the example looks…"}
          </p>
        )}
        {aura && (
          <div className="row made-row">
            <Variety aura={aura} looks={aura.looks} note={made} />
          </div>
        )}
        <DisclosureNote disclosure={made} live />
        {watts !== null && (
          <p className="note">
            <span className="t-value readout" data-testid="effect-watts">
              {watts.toFixed(1)} W
            </span>{" "}
            now
          </p>
        )}
      </Block>

      {adding && (
        <AddLayerPanel
          above={selection.id}
          onClose={() => {
            setAdding(false);
            selection.focusOn(ADD);
          }}
          onAdded={(id) => {
            setAdding(false);
            selection.select(id);
            selection.focusOn(id);
          }}
        />
      )}
      {/* The editor stays mounted under the cards, so what is open in it stays open. */}
      <div hidden={adding}>
        {aura ? (
          <section className="look-region" aria-label="Look editor">
            <LookKnobs />
            <div className="rest">
              <LayerList selection={selection} onAdd={() => setAdding(true)} />
              <LookSignals />
            </div>
          </section>
        ) : (
          <p className="note">Connecting to the engine…</p>
        )}
      </div>
    </div>
  );
}
