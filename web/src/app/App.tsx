import { Splitter } from "@ark-ui/react/splitter";
import { lazy, Suspense, useEffect, useId, useState, type ReactNode } from "react";
import { canArrange, useOffers, useStandingAura, useWire } from "../wire/store";
import { Banner } from "../design/Banner";
import { Button } from "../design/Button";
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
import { forgetParts } from "../rig/loadParts";
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
// The layout editor and the report load only when one first opens.
const ArrangeSlot = lazy(() => import("../arrange/console").then((m) => ({ default: m.ArrangeSlot })));
const ReportSlot = lazy(() => import("../arrange/console").then((m) => ({ default: m.ReportSlot })));
// What the hello offers beyond the Console's own, loaded only when one is offered: the
// Gallery's banner and idle pause, and the looks' export (the layout panel loads Publish).
const Share = lazy(() => import("../share/Share"));

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

/** The panel in the slot, in place of the editor; null for none. A top-bar or deck button opens one;
 * "arrange" shows while layout mode is on, on a run that takes layout edits. */
type SlotPanel = "health" | "looks" | "report" | "arrange" | null;

/** A panel loaded on demand, with a note while it loads and one if it does not. */
function Loaded({ children }: { children: ReactNode }) {
  return (
    <ErrorBoundary fallback={<p className="note" role="alert">this panel did not load; reload the page</p>}>
      <Suspense fallback={<p className="note">loading…</p>}>{children}</Suspense>
    </ErrorBoundary>
  );
}

/** Phone: the canvas on top, a scrolling slot, the deck pinned at the bottom.
 * Wide: the canvas beside a side panel, the deck at the top of it over the
 * slot. The slot shows the editor (the look and its main knobs, the layers,
 * each open with its own knobs, the modulators), or in its place the health
 * panel, the list of every look, the layout panel (the layout tools and, on a
 * run that takes layout edits, the arrangement editor; else on a phone the
 * layout tools alone), the rig's report, or the catalog a layer is added
 * from: no panel covers the deck. What the hello offers says what shows: the Gallery's page has no
 * layout mode, and has its banner and the 3D view first; export and Publish show only where they work.
 * While the connection is lost every control is inert and dimmed, so
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
  const arranges = useWire(canArrange);
  const gallery = !mode.offered;
  const exports = useOffers("export");
  // The Gallery shows a rig in 3D first; the Console, flat.
  const [chosenView, setStageView] = useState<StageView | null>(null);
  const stageView = chosenView ?? (gallery ? "3d" : "2d");
  const in3d = hasRig && stageView === "3d";
  // A new value tries the 3D view again after it failed to load.
  const [tries3d, setTries3d] = useState(0);
  // The health panel, the list of every look and the report take the slot in turn: opening one closes the
  // others. Closed, the slot shows the layout panel while layout mode is on.
  const [opened, setSlotPanel] = useState<Exclude<SlotPanel, "arrange">>(null);
  const toggle = (which: "health" | "looks") => () => setSlotPanel(opened === which ? null : which);
  const slotPanel: SlotPanel = opened ?? (mode.on && arranges ? "arrange" : null);
  const openReport = hasRig ? () => setSlotPanel("report") : undefined;
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
    { hotkey: "shift+?", label: "this list", keys: "?", action: () => setHelpOpen(true) },
    { hotkey: "Escape", label: "disarm a two-press button; close a panel, note or help", keys: "Esc", action: disarmAll },
    // Last, so its going moves no other shortcut's place: the Gallery has no layout mode (LayoutMode.tsx).
    ...(gallery ? [] : [{ hotkey: "l", label: "layout tools on or off", action: () => mode.setOn(!mode.on) }]),
  ]);
  const stage = (
    <div className="stage-area">
      <div className="stage-live" inert={lost}>
        {in3d ? (
          <ErrorBoundary
            resetKey={tries3d}
            fallback={
              <p className="stage-note" role="alert">
                The 3D view did not load.{" "}
                <Button
                  variant="tertiary"
                  onPress={() => {
                    forgetParts();
                    setTries3d((n) => n + 1);
                  }}
                >
                  Retry
                </Button>
              </p>
            }
          >
            <Suspense fallback={<p className="stage-note">loading the 3D view…</p>}>
              <Stage3D editing={slotPanel === "arrange"} />
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
          {connectionText(link, gallery ? "status" : "stage", lostLong)}
        </Banner>
      )}
    </div>
  );
  const panel = slotPanel === "health" ? (
    <HealthPanel onClose={() => setSlotPanel(null)} />
  ) : slotPanel === "looks" ? (
    <BookLooks onClose={() => setSlotPanel(null)} />
  ) : slotPanel === "report" ? (
    <Loaded>
      <ReportSlot onClose={() => setSlotPanel(null)} />
    </Loaded>
  ) : slotPanel === "arrange" ? (
    <Loaded>
      <ArrangeSlot onClose={() => mode.setOn(false)} onReport={() => setSlotPanel("report")} />
    </Loaded>
  ) : mode.on && !wide ? (
    <Panel title="layout" onClose={() => mode.setOn(false)}>
      <LayoutTools onReport={openReport} />
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
  const deck = (
    <Deck
      allOpen={slotPanel === "looks"}
      onAll={toggle("looks")}
      exporter={
        exports && (
          <Suspense>
            <Share part="export" />
          </Suspense>
        )
      }
    />
  );
  return (
    <div className="app" data-wide={wide || undefined}>
      <h1 className="sr-only">{gallery ? "pewpew Gallery" : "pewpew Console"}</h1>
      <div className="head">
        <TopBar healthOpen={slotPanel === "health"} onHealth={toggle("health")} onHelp={() => setHelpOpen(true)} />
        {!lost && <BoardBanner onOpen={() => setSlotPanel("health")} />}
        {gallery && (
          <Suspense>
            <Share part="gallery" />
          </Suspense>
        )}
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
            {mode.on && !arranges && (
              <div inert={lost}>
                <LayoutTools onReport={openReport} />
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
