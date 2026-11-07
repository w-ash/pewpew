import { AllLooks } from "../../deck/AllLooks";
import { LooksGroup } from "../../deck/Looks";
import { listedLooks } from "../../aura/looks";
import { MadeRow } from "../../deck/Variety";
import { useDisclosure } from "../../design/Disclosure";
import { LookKnobs, LookSignals } from "../../params/ParamPanel";
import { ADD, useLayerSelection } from "../../stack/selection";
import { AddLayerPanel } from "../../stack/AddLayer";
import { LayerList } from "../../stack/LayerList";
import type { ClientMessage, Sender } from "../../wire/protocol";
import { useStandingAura, useWire, WireContext } from "../../wire/store";
import { useContext, useState } from "react";
import { useLooks } from "../api/queries";
import { useSession } from "../store/session";
import { formatW } from "./ReportPanel";

/** The look each session starts in (docs/studio/contracts.md, "WebSocket"). */
const FIRST = "tide";

/**
 * The session's look, edited as the control page edits one: the example
 * looks as the deck shows saved looks, the first nine as tiles and "all N ›"
 * to the rest; surprise me and vary this; then the look's main knobs, its
 * layers, each open with its own knobs, and its modulators. The list of
 * every look and the cards a layer is added from open in the editor's place.
 * A press on an example sends it whole, over its own fade. The example last
 * started is marked as playing, `tide` on each new session, until a surprise
 * or a variation plays. Nothing is saved: the session has no looks file.
 */
export function EffectPanel() {
  const wire = useContext(WireContext);
  if (!wire) throw new Error("no WireContext");
  const { store, sender } = wire;
  const aura = useStandingAura();
  const examples = useLooks();
  const watts = useSession((s) => s.watts);
  const session = useWire((s) => s.session);
  const selection = useLayerSelection();
  const [adding, setAdding] = useState(false);
  const [allOpen, setAllOpen] = useState(false);
  const [pending, setPending] = useState<string | null>(null);
  const [marked, setMarked] = useState({
    session,
    name: FIRST as string | null,
  });
  const looksNote = useDisclosure();
  const current = marked.session === session ? marked.name : FIRST;

  /** Whether the engine took `msg`, once `asked` settles: no refusal of its kind came meanwhile. */
  const took = async (msg: ClientMessage, asked: Promise<void>) => {
    const before = store.getState().refusals[msg.type]?.seq;
    await asked;
    return store.getState().refusals[msg.type]?.seq === before;
  };
  const mark = (name: string | null) =>
    setMarked({ session: store.getState().session, name });
  const play = (name: string) => {
    const look = examples.data?.[name];
    if (!look || pending) return;
    setPending(name);
    const msg: ClientMessage = { type: "look", look, fade: null };
    void took(msg, sender.ask(msg))
      .then((ok) => ok && mark(name))
      .finally(() => setPending(null));
  };
  // Surprise me and vary this, which drop the mark once what they made plays.
  const making: Sender = {
    send: (msg) => sender.send(msg),
    sendLatest: (msg) => sender.sendLatest(msg),
    ask: (msg) => {
      const asked = sender.ask(msg);
      void took(msg, asked).then((ok) => ok && mark(null));
      return asked;
    },
  };
  const looks = listedLooks(Object.keys(examples.data ?? {}), current, pending);

  return (
    <div className="studio-panel">
      <div className="fields">
        {examples.data ? (
          <LooksGroup
            looks={looks}
            play={play}
            triggers={null}
            note={looksNote}
            allOpen={allOpen}
            onAll={() => setAllOpen(!allOpen)}
          />
        ) : (
          <p className="note">
            {examples.isError
              ? "The example looks could not be loaded."
              : "Loading the example looks…"}
          </p>
        )}
        {aura && (
          <WireContext.Provider value={{ store, sender: making }}>
            <MadeRow aura={aura} looks={aura.looks} />
          </WireContext.Provider>
        )}
        {watts !== null && (
          <p className="note">
            <span className="t-value readout" data-testid="effect-watts">
              {formatW(watts)}
            </span>{" "}
            now
          </p>
        )}
      </div>

      {allOpen && (
        <AllLooks
          looks={looks}
          play={play}
          triggers={null}
          onClose={() => setAllOpen(false)}
        />
      )}
      {adding && !allOpen && (
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
      {/* The editor stays mounted under a panel, so what is open in it stays open. */}
      <div hidden={adding || allOpen}>
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
