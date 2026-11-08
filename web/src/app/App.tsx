import { Splitter } from "@ark-ui/react/splitter";
import { lazy, Suspense, useEffect, useId, useState } from "react";
import { useStandingAura, useWire } from "../wire/store";
import { Banner } from "../design/Banner";
import { ErrorBoundary } from "../design/ErrorBoundary";
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
import { useRecall } from "../deck/Looks";
import { LayoutProvider, useLayoutMode } from "../layout/LayoutMode";
import { LayoutTools } from "../layout/LayoutTools";
import { AddLayerPanel } from "../stack/AddLayer";
import { ADD, useLayerSelection } from "../stack/selection";
import { usePlanImage } from "../stage/plan";
import { Stage, useCover } from "../stage/Stage";
import { StageControls, type StageView } from "../stage/StageControls";
import { BoardBanner } from "../status/BoardBanner";
import { connectionText, linkOf } from "../status/connection";
import { HealthPanel } from "../status/HealthPanel";
import { ShortcutHelp } from "../status/ShortcutHelp";
import { StatusBar } from "../status/StatusBar";
import { TopBar } from "../status/TopBar";
import { Slot } from "./Slot";

// three.js and the 3D view load only when the stage first shows 3D.
const Stage3D = lazy(() => import("../rig3d/Stage3D"));

export function App() {
  return (
    <LayoutProvider>
      <Shell />
    </LayoutProvider>
  );
}

/** Every look of the looks file, which a press recalls. */
function BookLooks({ onClose }: { onClose(): void }) {
  const aura = useStandingAura();
  const recall = useRecall();
  return <AllLooks looks={aura?.looks ?? null} play={recall} triggers={aura?.triggers ?? null} onClose={onClose} />;
}

/** Where focus goes when the look changes under it and its control is gone or waits: the note on a
 * cue's hold, else the look's heading, else the layers'. */
const FALLBACKS = [".held-note", ".slot :is(h2, h3)[tabindex]"];

/** How long the connection is lost before the laptop's banner says what to do. */
const LOST_HINT_MS = 5000;

/** The panel a top-bar or deck button opens in the slot, in place of the editor; null for none. */
type SlotPanel = "health" | "looks" | null;

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
  const link = useWire(linkOf);
  const blackout = useWire((s) => !!s.aura?.blackout);
  const held = useWire((s) => !!s.aura?.triggers?.held || !!s.aura?.looks?.pending);
  const lost = link === "lost";
  // Only an arrangement run has a rig to draw in 3D; any other map draws flat.
  const hasRig = useWire((s) => !!s.map?.rig);
  const [stageView, setStageView] = useState<StageView>("2d");
  const in3d = hasRig && stageView === "3d";
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
    // oxlint-disable-next-line react/set-state-in-effect -- clears the hint on every change of `lost` before the timer sets it again
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
        {in3d ? (
          <ErrorBoundary fallback={<p className="stage-note">The 3D view did not load. Reload the page to try again.</p>}>
            <Suspense fallback={<p className="stage-note">loading the 3D view…</p>}>
              <Stage3D />
            </Suspense>
          </ErrorBoundary>
        ) : (
          <Stage plan={plan} cover={cover} />
        )}
        {hasRig && <StageControls view={stageView} onChange={setStageView} />}
        <StatusBar planNote={plan.note} coverRef={measureCover} />
        {blackout && (
          <p className="stage-cue t-eyebrow" aria-hidden="true">
            blackout
          </p>
        )}
        {link === "waiting" && <p className="stage-note">{connectionText(link, "stage")}</p>}
      </div>
      {lost && (
        <Banner tone="lost" ref={measureCover}>
          {connectionText(link, "stage", lostLong)}
        </Banner>
      )}
    </div>
  );
  const panel = slotPanel === "health" ? (
    <HealthPanel onClose={() => setSlotPanel(null)} />
  ) : slotPanel === "looks" ? (
    <BookLooks onClose={() => setSlotPanel(null)} />
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
  // While a cue holds a look or a recall waits, the layers wait, inert, as the knobs do (LookPanel).
  const slot = (
    <Slot
      panel={panel}
      head={<LookPanel titleId={lookTitle} />}
      labelledBy={lookTitle}
      held={held}
      selection={selection}
      onAdd={() => setAdding(true)}
    />
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
