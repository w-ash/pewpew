import { Accordion } from "@ark-ui/react/accordion";
import { Slider } from "@ark-ui/react/slider";
import { useEffect, useId, useLayoutEffect, useRef, useState, type KeyboardEvent, type ReactNode } from "react";
import { percent } from "../params/format";
import type { BoolParam, ChoiceParam, Param } from "../params/schema";
import { blendsAbout, showsBlack, type BlendNote } from "./catalog";
import { liveLook } from "../aura/looks";
import { chainSaysMore, isPattern, layerOf, mixAddress, moveTo, runs, summaryOf, type LayerItem } from "./stack";
import { setParam } from "../wire/protocol";
import { useAtDefaults, useLayers, useOffSaved, useParamValue, useRefusal, useSender, useWire } from "../wire/store";
import { Badge } from "../design/Badge";
import { Button, IconButton } from "../design/Button";
import { ChangedMark } from "../design/ChangedMark";
import { DisclosureNote, useDisclosure } from "../design/Disclosure";
import { Icon } from "../design/Icon";
import { SliderBody } from "../design/SliderBody";
import { SizedName } from "../design/Tile";
import { useDraft } from "../design/useDraft";
import { FINE_POINTER, useMedia } from "../design/useMedia";
import { useOnChange } from "../design/useOnChange";
import { PatternPicker } from "../deck/PatternPicker";
import { ParamField } from "../params/ParamField";
import { DefaultsButton, LayerKnobList, useLayerKnobs } from "../params/ParamPanel";
import { ADD, type LayerSelection } from "./selection";

const NO_NAMES: readonly string[] = [];
const NO_BLENDS: readonly BlendNote[] = [];
const TRIGGER = '[data-part="item-trigger"]';
/** The most layers a look holds (pewpew.aura.control MAX_LAYERS). */
export const MAX_LAYERS = 16;

/** The control a move came from, which takes focus again in the row's new place. */
type Mover = "up" | "down" | "row";

/** The slot `el` scrolls in. */
const slotOf = (el: Element) => el.closest<HTMLElement>(".slot");

/** How long a row opened by hand is kept in view while its body takes its height. */
const OPEN_MS = 600;

/** The running look's layers. A look of one layer has no layer chrome (`LoneLayer`). Of more, under
 * "layers" and "+ layer", a row each, the top one first: its id, what it makes in a few words, its mix at
 * a glance and its on switch, the glances of every row in columns. Its opacity has one home: with a mouse
 * its row's slider, on touch its open row (`MixGlance`). The picked row opens under its name, its knobs
 * starting where the name does: ▲ ▼ (Alt+↑ ↓ on the row) and remove, its blend, what it runs (its wiring,
 * when that says more than the row does, or its pattern pick; a program's behind "replace with
 * pattern…"), its own knobs, and defaults. The rows start closed, so the stack reads at a glance. A row
 * opened by hand scrolls up to under the look's header when it would run past the slot's bottom. A control
 * an edit takes away hands focus on: a moved row's to its new place, which stays where it was in the slot,
 * a removed row's to the next; a move says where it put the layer, and a remove which it took, for
 * assistive tech. At MAX_LAYERS, a press on "+ layer" says why it is off, in a note under it. */
export function LayerList({ selection, onAdd }: { selection: LayerSelection; onAdd(): void }) {
  const layers = useLayers();
  const pattern = useWire((s) => s.aura?.pattern ?? "");
  const patterns = useWire((s) => s.aura?.patterns) ?? NO_NAMES;
  const sender = useSender();
  const look = useWire((s) => (s.aura ? liveLook(s.aura.looks, s.aura.triggers) ?? s.aura.looks?.made ?? s.aura.pattern : null));
  const headId = useId();
  const add = useRef<HTMLButtonElement>(null);
  const full = useDisclosure();
  const rows = useRef(new Map<string, HTMLElement>());
  const [moving, setMoving] = useState<{ readonly id: string; readonly by: Mover; readonly top: number } | null>(null);
  const [removing, setRemoving] = useState<string | null>(null);
  // Whether the rows are shut, as each look starts, until opened by hand.
  const [shut, setShut] = useState(true);
  const [opened, setOpened] = useState<string | null>(null);
  // Where a move put its layer, or that a remove took it, for assistive tech: the row's name does not change.
  const [moved, setMoved] = useState("");
  useOnChange(look, () => setShut(true));
  useOnChange(useRefusal("remove_layer"), () => setRemoving(null));
  useOnChange(useRefusal("move_layer"), () => setMoving(null));
  // A row asked to take focus (an added layer's, the next after a remove) opens.
  useOnChange(selection.focus, () => {
    if (selection.focus && selection.focus !== ADD) setShut(false);
  });
  const ids = layers.map((l) => l.id);
  const order = ids.join(" ");
  if (removing && !ids.includes(removing)) {
    setRemoving(null);
    setMoved(`${removing} removed`);
  }
  const atCap = layers.length >= MAX_LAYERS;

  useEffect(() => {
    const target = selection.focus;
    if (!target || removing) return;
    const el = target === ADD ? add.current : rows.current.get(target)?.querySelector<HTMLElement>(TRIGGER);
    if (!el) return;
    el.focus();
    selection.focused();
  });
  // Run when the order the move asked for arrives, not when the move is asked for.
  useLayoutEffect(() => {
    if (!moving) return;
    setMoving(null);
    const at = ids.indexOf(moving.id);
    if (at >= 0) setMoved(`${moving.id} moved to ${ids.length - at} of ${ids.length}, top first`);
    const row = rows.current.get(moving.id);
    if (!row) return;
    // The row stays where it was in the slot, which taking it out and back in may have scrolled.
    const slot = slotOf(row);
    if (slot) slot.scrollTop += row.getBoundingClientRect().top - moving.top;
    const focused = document.activeElement;
    // A move that kept the node kept its focus, unless on the ▲ or ▼ that the new place turned off.
    if (row.contains(focused) && !(focused instanceof HTMLButtonElement && focused.disabled)) return;
    const own = moving.by === "row" ? TRIGGER : `[data-move="${moving.by}"]:not(:disabled)`;
    [own, "[data-move]:not(:disabled)", TRIGGER].map((part) => row.querySelector<HTMLElement>(part)).find(Boolean)?.focus({ preventScroll: true });
  }, [order]);
  // A row opened by hand that would run past the slot's bottom scrolls its head up to just under the
  // look's header. Its body mounts after its head: the row is watched while it takes its height.
  const watching = useRef<ResizeObserver | null>(null);
  useLayoutEffect(() => {
    if (!opened) return;
    setOpened(null);
    const row = rows.current.get(opened);
    const slot = row && slotOf(row);
    if (!row || !slot) return;
    const fit = () => {
      const r = row.getBoundingClientRect(), view = slot.getBoundingClientRect();
      const top = view.top + (parseFloat(getComputedStyle(slot).scrollPaddingTop) || 0);
      if (r.bottom > view.bottom) slot.scrollTop += Math.min(r.top - top, r.bottom - view.bottom);
    };
    watching.current?.disconnect();
    const watch = (watching.current = new ResizeObserver(fit));
    watch.observe(row);
    setTimeout(() => watch.disconnect(), OPEN_MS);
  }, [opened]);

  const move = (id: string, up: boolean, by: Mover) => {
    const to = moveTo(layers, id, up);
    if (to === null) return;
    selection.select(id); // picked by name: the top one by default may be another once it moves
    setMoving({ id, by, top: rows.current.get(id)?.getBoundingClientRect().top ?? 0 });
    sender.send({ type: "move_layer", lid: id, to });
  };
  const remove = (id: string) => {
    const i = ids.indexOf(id);
    const next = ids[i - 1] ?? ids[i + 1]!; // the row under it in the list, else the one over it
    setRemoving(id);
    selection.select(next);
    selection.focusOn(layers.length > 2 ? next : ADD);
    sender.send({ type: "remove_layer", lid: id });
  };

  if (!layers.length) return null; // no aura state yet
  const capText = `a look has at most ${MAX_LAYERS} layers; remove one first`;
  const addButton = (
    <Button ref={add} variant="tertiary" reason={atCap ? capText : null} note={full} onPress={onAdd}>
      + layer
    </Button>
  );
  if (layers.length === 1) return <LoneLayer layer={layers[0]!} pattern={pattern} patterns={patterns} add={addButton} />;
  return (
    <section className="block layers" aria-labelledby={headId}>
      <header className="block-head">
        <h3 id={headId} className="t-heading" tabIndex={-1}>
          layers<span className="t-caption"> · top first</span>
        </h3>
        {addButton}
      </header>
      <DisclosureNote disclosure={full} live />
      <p className="sr-only" role="status">
        {moved}
      </p>
      <Accordion.Root
        collapsible
        lazyMount
        unmountOnExit
        value={selection.id && !shut ? [selection.id] : []}
        onValueChange={(d) => {
          setShut(!d.value[0]);
          if (!d.value[0]) return;
          selection.select(d.value[0]);
          setOpened(d.value[0]);
        }}
      >
        {layers.toReversed().map((layer) => (
          <LayerRow
            key={layer.id}
            layer={layer}
            patterns={patterns}
            bottom={layer.id === ids[0]}
            picked={layer.id === selection.id}
            rowRef={(el) => {
              if (el) rows.current.set(layer.id, el);
              else rows.current.delete(layer.id);
            }}
            up={moveTo(layers, layer.id, true) !== null}
            down={moveTo(layers, layer.id, false) !== null}
            onMove={(up, by) => move(layer.id, up, by)}
            onRemove={() => remove(layer.id)}
          />
        ))}
      </Accordion.Root>
    </section>
  );
}

/** The heading a lone layer's knobs go under: its id and what it is, `pattern` or `3 steps` (RA-27b §3). */
function loneTitle(layer: LayerItem): string {
  const n = layer.nodes.length;
  return `${layer.id} · ${isPattern(layer) ? "pattern" : `${n} step${n === 1 ? "" : "s"}`}`;
}

/** A look of one layer, with no layer chrome (RA-27b §3): no list, switch, opacity or order, only its
 * knobs under its heading (`loneTitle`) with "reset to defaults". A pattern shows its pick, which [ and ]
 * step through, then its knobs; a program its wiring, when that says more than its steps do, then its
 * steps, folded to their names. Its mix (on, opacity, blend) shows while any of it is off its defaults,
 * and "reset to defaults" then covers it too, so a page that left it so, a layer switched off above all,
 * can put it back. Then, quiet, "replace with pattern…" for a program, and "+ layer" (`add`) at the column's
 * edge. */
function LoneLayer({ layer, pattern, patterns, add }: { layer: LayerItem; pattern: string; patterns: readonly string[]; add: ReactNode }) {
  const { id } = layer;
  const params = useWire((s) => s.params);
  const { all } = useLayerKnobs(id);
  const headId = useId();
  const [replacing, setReplacing] = useState(false);
  const enabled = mixOf(params, id, "enabled"), opacity = mixOf(params, id, "opacity"), blend = mixOf(params, id, "blend");
  const mix = [enabled, opacity, blend].filter((p): p is Param => !!p);
  const mixed = !useAtDefaults(mix);
  const knobs = mixed ? [...mix, ...all] : all;
  const program = !isPattern(layer);
  return (
    <section className="block lone-layer" aria-labelledby={headId}>
      <header className="block-head">
        <h3 id={headId} className="t-title" tabIndex={-1}>
          {loneTitle(layer)}
        </h3>
        {knobs.length > 0 && <DefaultsButton knobs={knobs} />}
      </header>
      {program ? <Chain layer={layer} params={params} /> : <PatternPicker pattern={pattern} patterns={patterns} keys />}
      {mixed && enabled && <ParamField p={enabled} />}
      {mixed && opacity && <ParamField p={opacity} />}
      {mixed && blend && <BlendField blend={blend} bottom />}
      <LayerKnobList layer={id} open={!program} level={4} />
      <div className="row lone-actions">
        {program &&
          (replacing ? (
            <PatternPicker pattern="custom" patterns={patterns} layer={id} narrow autoFocus />
          ) : (
            <Button variant="tertiary" className="replace" onPress={() => setReplacing(true)}>
              replace with pattern…
            </Button>
          ))}
        {add}
      </div>
      {replacing && <p className="note">picking a pattern replaces this layer's parts</p>}
    </section>
  );
}

interface RowProps {
  readonly layer: LayerItem;
  readonly patterns: readonly string[];
  /** Whether it is the bottom layer, with nothing under it. */
  readonly bottom: boolean;
  /** Whether it is the one open. */
  readonly picked: boolean;
  rowRef(el: HTMLElement | null): void;
  /** Whether it can move up (towards the top), and down. */
  readonly up: boolean;
  readonly down: boolean;
  onMove(up: boolean, by: Mover): void;
  onRemove(): void;
}

/** Layer `id`'s mix knob `knob` among `params`, or undefined. */
function mixOf(params: readonly Param[], id: string, knob: "opacity" | "blend" | "enabled"): Param | undefined {
  return params.find((p) => p.name === mixAddress(id, knob));
}

/** `blend`, its modes that show black over nothing marked when the layer has nothing under it. */
function blendOver(blend: Param, blends: readonly BlendNote[], bottom: boolean): Param {
  if (!bottom || blend.kind !== "choice") return blend;
  const options = blend.options.map((o) => (showsBlack(blends, o.value) ? { ...o, label: `${o.label} (black: nothing below)` } : o));
  return { ...blend, options } satisfies ChoiceParam;
}

/** A layer's blend knob, each mode's "?" saying what it does; when the layer is at the `bottom`, the modes
 * that show black over nothing say so. */
function BlendField({ blend, bottom, owner }: { blend: Param; bottom: boolean; owner?: string }) {
  const blends = useWire((s) => s.catalog?.blends) ?? NO_BLENDS;
  return <ParamField p={blendOver(blend, blends, bottom)} owner={owner} about={(mode) => blendsAbout(blends, String(mode), bottom)} />;
}

/** A program layer's wiring, when it says more than its steps' sections do (`chainSaysMore`). */
function Chain({ layer, params }: { layer: LayerItem; params: readonly Param[] }) {
  const knobbed = new Set(params.flatMap((p) => (p.layer === layer.id && p.node ? [p.node] : [])));
  return chainSaysMore(layer, knobbed) ? <p className="chain">{runs(layer)}</p> : null;
}

function LayerRow({ layer, patterns, bottom, picked, rowRef, up, down, onMove, onRemove }: RowProps) {
  const { id } = layer;
  const params = useWire((s) => s.params);
  const failed = useWire((s) => s.error?.source === "render" && !!s.error.path && layerOf(s.error.path) === id);
  const [replacing, setReplacing] = useState(false);
  // A knob of its own off the look as saved, or its program changed since: a save would change it.
  const off = useOffSaved(params.filter((p) => p.layer === id), `layers.${id}.`);
  const opacity = mixOf(params, id, "opacity"), blend = mixOf(params, id, "blend"), enabled = mixOf(params, id, "enabled");
  // With a mouse, the row's own slider is the opacity's one home.
  const rowSlider = useMedia(FINE_POINTER);
  const keys = (e: KeyboardEvent) => {
    if (!e.altKey || (e.key !== "ArrowUp" && e.key !== "ArrowDown")) return;
    e.preventDefault(); // before the accordion's own arrow keys, which move focus
    onMove(e.key === "ArrowUp", "row");
  };
  const program = !isPattern(layer);
  const summary = summaryOf(layer).toLowerCase();
  return (
    <Accordion.Item ref={rowRef} value={id} className="layer" data-picked={picked || undefined}>
      <div className="layer-head">
        <h4 className="row-title">
          <Accordion.ItemTrigger onKeyDownCapture={keys} aria-keyshortcuts="Alt+ArrowUp Alt+ArrowDown">
            <Accordion.ItemIndicator>
              <Icon name="chevron" />
            </Accordion.ItemIndicator>
            <SizedName name={id} className="layer-id" />{" "}
            <span className="runs">
              {summary && (
                <span className="sep" aria-hidden="true">
                  ·{" "}
                </span>
              )}
              {summary}
            </span>
            {off && <ChangedMark />}
            {failed && <Badge tone="danger">failed</Badge>}
          </Accordion.ItemTrigger>
        </h4>
        {opacity && blend && <MixGlance opacity={opacity} blend={blend} id={id} slider={rowSlider} />}
        {enabled?.kind === "bool" && <LayerSwitch p={enabled} id={id} />}
      </div>
      <Accordion.ItemContent className="layer-body">
        <div className="row layer-actions">
          <IconButton variant="secondary" icon="up" data-move="up" label={`move ${id} up`} disabled={!up} onPress={() => onMove(true, "up")} />
          <IconButton variant="secondary" icon="down" data-move="down" label={`move ${id} down`} disabled={!down} onPress={() => onMove(false, "down")} />
          <Button variant="tertiary" tone="danger" confirm="again to remove" say={`remove ${id}? press again to confirm`} onPress={onRemove}>
            remove
          </Button>
        </div>
        {opacity && !rowSlider && <ParamField p={opacity} owner={id} />}
        {blend && <BlendField blend={blend} bottom={bottom} owner={id} />}
        {program ? (
          <>
            <Chain layer={layer} params={params} />
            {replacing ? (
              <>
                <PatternPicker pattern="custom" patterns={patterns} layer={id} narrow autoFocus />
                <p className="note">picking a pattern replaces this layer's parts</p>
              </>
            ) : (
              <Button variant="tertiary" className="replace" onPress={() => setReplacing(true)}>
                replace with pattern…
              </Button>
            )}
          </>
        ) : (
          <PatternPicker pattern={runs(layer)} patterns={patterns} layer={id} narrow />
        )}
        <LayerKnobList layer={id} />
        <RowDefaults layer={id} />
      </Accordion.ItemContent>
    </Accordion.Item>
  );
}

/** "defaults" for layer `layer`'s own knobs, under them, when it has any. */
function RowDefaults({ layer }: { layer: string }) {
  const { all } = useLayerKnobs(layer);
  return all.length ? (
    <div className="row layer-defaults">
      <DefaultsButton knobs={all} />
    </div>
  ) : null;
}

/** A layer's mix on its row, open or not: its blend unless normal, and its opacity; with `slider`, the
 * opacity's own slider too, so layers balance against each other in one view. It is named as the knob
 * is. On touch, where a short slider cannot be dragged finely, the open row holds the knob instead,
 * with its steps. */
function MixGlance({ opacity, blend, id, slider }: { opacity: Param; blend: Param; id: string; slider: boolean }) {
  const sender = useSender();
  const o = useParamValue(opacity);
  const b = useParamValue(blend);
  const draft = useDraft(typeof o === "number" ? o : 1, Object.is);
  const mode = blend.kind === "choice" ? (blend.options.find((x) => x.value === b)?.label ?? String(b)) : String(b);
  const level = (
    <span className="readout" aria-hidden="true">
      {b !== "normal" && `${mode.toLowerCase()} · `}
      {typeof o === "number" && <span className="t-value">{percent(draft.shown)}</span>}
    </span>
  );
  if (!slider || opacity.kind !== "float") return <span className="mix-glance">{level}</span>;
  // display: contents: the slider and the readout are cells of the rows' columns (page.css).
  return (
    <span className="mix-glance">
      <Slider.Root
        className="mix-opacity"
        min={opacity.lo}
        max={opacity.hi}
        step={opacity.step}
        value={[draft.shown]}
        aria-label={[`opacity · ${id}`]}
        getAriaValueText={(d) => percent(d.value)}
        onValueChange={(d) => {
          const v = d.value[0] ?? draft.shown;
          draft.change(v);
          setParam(sender, opacity, v);
        }}
        onValueChangeEnd={draft.release}
      >
        <SliderBody />
      </Slider.Root>
      {level}
    </span>
  );
}

/** Whether a layer runs: a switch on its row, named by the layer, in a label as big as a target. */
function LayerSwitch({ p, id }: { p: BoolParam; id: string }) {
  const sender = useSender();
  const draft = useDraft(useParamValue(p), Object.is);
  return (
    <label className="layer-on">
      <input
        type="checkbox"
        role="switch"
        className="switch"
        aria-label={`layer ${id}`}
        checked={draft.shown}
        onChange={(e) => {
          const on = e.currentTarget.checked;
          draft.change(on);
          draft.release();
          setParam(sender, p, on);
        }}
      />
    </label>
  );
}
