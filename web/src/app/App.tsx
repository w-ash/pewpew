import { Splitter } from "@ark-ui/react/splitter";
import { useEffect, useId, useState } from "react";
import { useWire } from "../wire/store";
import { onEngineHost } from "../design/engineHost";
import { Panel } from "../design/Panel";
import { StepStatus } from "../design/StepStatus";
import { ArmStatus } from "../design/press";
import { useShortcuts } from "../design/shortcuts";
import { disarmAll } from "../design/useArm";
import { useFocusKeeper } from "../design/useFocusKeeper";
import { FINE_POINTER, useMedia, WIDE } from "../design/useMedia";
import { AllLooks } from "../deck/AllLooks";
import { Deck } from "../deck/Deck";
import { LookPanel } from "../deck/LookPanel";
import { LayoutProvider, useLayoutMode } from "../layout/LayoutMode";
import { LayoutTools } from "../layout/LayoutTools";
import { LookSignals } from "../params/ParamPanel";
import { AddLayerPanel } from "../stack/AddLayer";
import { LayerList } from "../stack/LayerList";
import { ADD, useLayerSelection } from "../stack/selection";
import { usePlanImage } from "../stage/plan";
import { Stage, useCover } from "../stage/Stage";
import { BoardBanner } from "../status/BoardBanner";
import { HealthPanel } from "../status/HealthPanel";
import { ShortcutHelp } from "../status/ShortcutHelp";
import { StatusBar } from "../status/StatusBar";
import { TopBar } from "../status/TopBar";

export function App() {
  return (
    <LayoutProvider>
      <Shell />
    </LayoutProvider>
  );
}

/** Where focus goes when the look changes under it and its control is gone or waits: the note on a
 * cue's hold, else the look's heading, else the layers'. */
const FALLBACKS = [".held-note", ".slot :is(h2, h3)[tabindex]"];

/** How long the connection is lost before the laptop's banner says what to do. */
const LOST_HINT_MS = 5000;

/** The panel a top-bar or deck button opens in the slot, in place of the editor; null for none. */
type SlotPanel = "health" | "looks" | null;

/** What the banner says while the connection is lost: on the laptop pewpew runs on, pewpew stopped, and
 * once it has been `long`, what to do; elsewhere, maybe this device left the private Wi-Fi. */
function lostText(long: boolean): string {
  if (!onEngineHost()) return "Lost the pewpew laptop. Retrying… Is this device on the private Wi-Fi?";
  return `Lost pewpew. Retrying…${long ? " Stopped? Start the run again: this page reconnects on its own." : ""}`;
}

/** Phone: the canvas on top, a scrolling slot, the deck pinned at the bottom.
 * Wide: the canvas beside a side panel, the deck at the top of it over the
 * slot. The slot shows the editor (the look and its main knobs, the layers,
 * each open with its own knobs, the modulators), or in its place the health
 * panel, the list of every look, on a phone the layout tools, or the catalog
 * a layer is added from: no panel covers the deck. While the connection is lost every control is inert and dimmed, so
 * no tap is dropped silently, and a banner over the stage says so; the room
 * is fitted under it, as under the status bar. Focus that an aura message or a lost connection takes away comes back
 * (`useFocusKeeper`): to the same control once it is back, else to the look. */
function Shell() {
  const wide = useMedia(WIDE);
  const fine = useMedia(FINE_POINTER);
  const mode = useLayoutMode();
  const plan = usePlanImage(useWire((s) => s.map));
  const connected = useWire((s) => s.connected);
  const blackout = useWire((s) => !!s.aura?.blackout);
  const held = useWire((s) => !!s.aura?.triggers?.held || !!s.aura?.looks?.pending);
  const lost = useWire((s) => !s.connected && s.session > 0);
  // The health panel and the list of every look take the slot in turn: opening one closes the other.
  const [slotPanel, setSlotPanel] = useState<SlotPanel>(null);
  const toggle = (which: Exclude<SlotPanel, null>) => () => setSlotPanel(slotPanel === which ? null : which);
  const [helpOpen, setHelpOpen] = useState(false);
  const [adding, setAdding] = useState(false);
  const [lostLong, setLostLong] = useState(false);
  const selection = useLayerSelection();
  const lookTitle = useId();
  const [measureCover, cover] = useCover();
  useFocusKeeper(FALLBACKS, useWire((s) => s.aura), lost);
  useEffect(() => {
    setLostLong(false);
    if (!lost) return;
    disarmAll();
    const id = setTimeout(() => setLostLong(true), LOST_HINT_MS);
    return () => clearTimeout(id);
  }, [lost]);
  useShortcuts([
    { hotkey: "l", label: "layout tools on or off", action: () => mode.setOn(!mode.on) },
    { hotkey: "shift+?", label: "this list", keys: "?", action: () => setHelpOpen(true) },
    { hotkey: "Escape", label: "disarm a two-press button; close a panel, note or help", keys: "Esc", action: disarmAll },
  ]);
  const stage = (
    <div className="stage-area">
      <div className="stage-live" inert={lost}>
        <Stage plan={plan} cover={cover} />
        <StatusBar planNote={plan.note} coverRef={measureCover} />
        {blackout && (
          <p className="stage-cue t-eyebrow" aria-hidden="true">
            blackout
          </p>
        )}
        {!connected && !lost && (
          <p className="stage-note">
            Waiting for the pewpew laptop at {location.host}. Is pewpew running with --preview?
          </p>
        )}
      </div>
      {lost && (
        <p ref={measureCover} className="banner lost" role="alert">
          {lostText(lostLong)}
        </p>
      )}
    </div>
  );
  const panel = slotPanel === "health" ? (
    <HealthPanel onClose={() => setSlotPanel(null)} />
  ) : slotPanel === "looks" ? (
    <AllLooks onClose={() => setSlotPanel(null)} />
  ) : mode.on && !wide ? (
    <Panel title="layout" onClose={() => mode.setOn(false)}>
      <LayoutTools />
    </Panel>
  ) : adding ? (
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
  ) : null;
  // The editor stays mounted under a panel: a typed look name, its toggles
  // and a refusal that comes meanwhile are still there when it closes. While
  // a cue holds a look or a recall waits, its layers wait, inert, as its
  // knobs do (LookPanel). For assistive tech the look is one region, named by
  // its title, its blocks headed a level under it.
  const slot = (
    <>
      {panel}
      <div hidden={panel !== null}>
        <section className="look-region" aria-labelledby={lookTitle}>
          <LookPanel titleId={lookTitle} />
          <div className="rest" inert={held}>
            <LayerList selection={selection} onAdd={() => setAdding(true)} />
            <LookSignals />
          </div>
        </section>
      </div>
    </>
  );
  const deck = <Deck allOpen={slotPanel === "looks"} onAll={toggle("looks")} />;
  return (
    <div className="app" data-wide={wide || undefined}>
      <h1 className="sr-only">pewpew aura control</h1>
      <div className="head">
        <TopBar healthOpen={slotPanel === "health"} onHealth={toggle("health")} onHelp={() => setHelpOpen(true)} />
        {!lost && <BoardBanner onOpen={() => setSlotPanel("health")} />}
      </div>
      {wide ? (
        <Splitter.Root
          className="split"
          panels={[
            { id: "stage", minSize: 30 },
            { id: "side", minSize: 24 },
          ]}
          // A phone on its side needs the side panel at a phone's width for 44 px targets.
          defaultSize={fine ? [64, 36] : [50, 50]}
        >
          <Splitter.Panel id="stage" className="stage-panel">
            {stage}
            {mode.on && (
              <div inert={lost}>
                <LayoutTools />
              </div>
            )}
          </Splitter.Panel>
          <Splitter.ResizeTrigger id="stage:side" aria-label="resize the side panel" />
          <Splitter.Panel id="side" className="side" inert={lost}>
            <div className="side-col">
              {deck}
              <main className="slot">{slot}</main>
            </div>
          </Splitter.Panel>
        </Splitter.Root>
      ) : (
        <div className="stack">
          {stage}
          <main className="slot" inert={lost}>
            {slot}
          </main>
          <div className="deck-dock" inert={lost}>
            {deck}
          </div>
        </div>
      )}
      <ShortcutHelp open={helpOpen} onClose={() => setHelpOpen(false)} />
      <ArmStatus />
      <StepStatus />
    </div>
  );
}
