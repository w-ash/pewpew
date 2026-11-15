import { Field } from "@ark-ui/react/field";
import { useRef, useState, type KeyboardEvent, type MouseEvent, type PointerEvent } from "react";
import { blendHsv, cssRgb, displayRgb, gradientCss } from "../color";
import { formatNumber } from "../format";
import { palette } from "../kinds/palette";
import type { ColorParam, Gradient, PaletteParam, Stop } from "../schema";
import { useWire } from "../../wire/store";
import { Button, IconButton } from "../../design/Button";
import { sayStep } from "../../design/StepStatus";
import { DisclosureNote, useDisclosure } from "../../design/Disclosure";
import { ColorParts, PartStrip } from "./color";
import { stepKeys } from "./stepKeys";
import type { ControlProps } from "./types";

const PLAIN = { help: "", group: "", widget: "", layer: "", node: "" } as const;
/** How far a press moves, in px, before it is a drag: under it, it picks the stop. */
const SLOP = 4;
/** How much nearer, in px, the picked stop counts to a press: in a pile, a press takes it. */
const FAVOR = 6;

interface Drag {
  /** The stop that drags; in a pile, the first sideways move chooses it. */
  k: number;
  /** The stops at the pressed place, in order: more than one in a pile. */
  readonly pile: readonly number[];
  readonly id: number;
  /** Where the press began, and how far that was from the stop's own place. */
  readonly x: number;
  readonly y: number;
  readonly grab: number;
  /** The palette as the press found it: what a drag the browser takes over (a scroll) puts back. */
  readonly from: Gradient;
  moved: boolean;
}

/** palette: a preset list; the gradient as the LEDs show it, with a dot under it per stop; and,
 * once a dot is pressed, that stop's editor. A dot drags left and right as far as its neighbours, where two
 * stops at one place make a hard edge; the ends stay at 0 and 1. A press takes the nearest dot, the picked
 * one first in a pile; when it moves, the last of a pile goes if it moves right and the first if it moves left.
 * A dot is a slider: the arrow keys step it (ten steps with Shift or a Page key), Home and End take it to its
 * neighbours, Enter or Space opens its editor, Delete or Backspace removes it (an end stop or one of two says
 * why not) and focus goes to the dot before. A press on the gradient adds a stop there, in the color the gradient has there, so the room keeps its colors until the stop is moved or
 * colored. The editor says which stop of how many (said as it changes), steps to the stop before or after
 * (the way to one of several in a pile), adds a stop halfway to the next and removes one (in two presses),
 * and holds the stop's parts as strips: its position, on a strip that runs from the stop before to the stop
 * after and shows the two fades it sits between, so stops a few thousandths apart still have the strip's
 * whole width; then its color, as a color param's. A second press on the dot folds the editor. Each drag,
 * typed value, added or removed stop and preset is one step of the page's undo (params/history.ts). What
 * cannot be done says why when pressed. Any edit of a stop makes the palette custom. */
export function PaletteControl({ p, value, onChange, onCommit, onRestore, onNote }: ControlProps<PaletteParam>) {
  // A param exists only after a hello, which brings the gamma.
  const gamma = useWire((s) => s.gamma) ?? 1;
  const [picked, pick] = useState<number | null>(null);
  const why = useDisclosure();
  const strip = useRef<HTMLDivElement>(null);
  const drag = useRef<Drag | null>(null);
  const { stops } = value;
  const last = stops.length - 1;
  const i = Math.min(picked ?? 0, last);
  const stop = stops[i]!;
  const open = picked !== null;
  const preset = p.presets.find((x) => palette.equal(x.value, value));
  const put = (next: Gradient, commit: boolean) => {
    onChange(next);
    if (commit) onCommit();
  };
  const send = (next: readonly Stop[], commit: boolean) => put({ label: "", stops: next }, commit);
  const editStop = (patch: Partial<Stop>) => send(stops.with(i, { ...stop, ...patch }), false);
  const full = stops.length >= p.maxStops, few = stops.length <= 2;
  const fewWhy = "a palette needs two stops";
  const fullWhy = `a palette has at most ${p.maxStops} stops`;
  /** A new stop at `at`, after stop `k`, in the color the gradient has there. */
  const insert = (k: number, at: number) => {
    const a = stops[k]!, b = stops[k + 1]!;
    const color = blendHsv(a, b, b.at > a.at ? (at - a.at) / (b.at - a.at) : 0);
    why.close();
    send(stops.toSpliced(k + 1, 0, { at, ...color }), true);
    pick(k + 1);
  };
  const add = () => {
    const k = i === last ? i - 1 : i; // halfway from stop k to the next
    insert(k, (stops[k]!.at + stops[k + 1]!.at) / 2);
  };
  const addHere = (e: MouseEvent<HTMLDivElement>) => {
    if (e.target !== e.currentTarget) return;
    if (full) return why.show(fullWhy);
    const box = e.currentTarget.getBoundingClientRect();
    const at = Math.min(Math.max((e.clientX - box.left) / box.width, 0), 1);
    insert(Math.min(stops.findLastIndex((s) => s.at <= at), last - 1), at);
  };
  const remove = () => {
    why.close();
    send(stops.toSpliced(i, 1), true);
    pick(Math.max(i - 1, 0));
  };
  const step = (to: number) => {
    why.close();
    pick(to);
  };
  const toggle = (k: number) => pick(open && k === i ? null : k);
  const isEnd = (k: number) => k === 0 || k === last;
  const endWhy = (k: number) => (k === 0 ? "the first stop stays at 0" : "the last stop stays at 1");
  const move = (k: number, at: number, done: boolean) => send(stops.with(k, { ...stops[k]!, at }), done);
  const press = (e: PointerEvent<HTMLDivElement>) => {
    if (e.button !== 0) return;
    const box = strip.current!.getBoundingClientRect();
    const place = (n: number) => box.left + stops[n]!.at * box.width;
    // The nearest dot, not the one on top: their boxes overlap long before the dots do.
    const far = stops.map((_, n) => Math.abs(place(n) - e.clientX) - (open && n === i ? FAVOR : 0));
    const k = far.indexOf(Math.min(...far));
    const dot = e.currentTarget.parentElement!.children[k] as HTMLElement;
    // The press is that dot's: its focus, and every move after.
    e.preventDefault();
    dot.focus();
    dot.setPointerCapture(e.pointerId);
    const grab = e.clientX - place(k);
    const pile = stops.flatMap((s, n) => (Math.abs(s.at - stops[k]!.at) < 1e-9 ? [n] : []));
    drag.current = { k, pile, id: e.pointerId, x: e.clientX, y: e.clientY, grab, from: value, moved: false };
  };
  const pull = (e: PointerEvent<HTMLDivElement>) => {
    const d = drag.current;
    if (!d || d.id !== e.pointerId) return;
    if (!d.moved) {
      // Sideways, and more sideways than up or down: a swipe along the page is the page's.
      const dx = Math.abs(e.clientX - d.x);
      if (dx < SLOP || dx < Math.abs(e.clientY - d.y)) return;
      d.moved = true;
      // In a pile the way it moves decides which stop goes: the one that is free to move that way.
      if (d.pile.length > 1) {
        d.k = (e.clientX > d.x ? d.pile.at(-1) : d.pile[0])!;
        (e.currentTarget.parentElement!.children[d.k] as HTMLElement).focus();
      }
      if (isEnd(d.k)) why.show(endWhy(d.k));
      else why.close();
      if (open) pick(d.k);
    }
    if (isEnd(d.k)) return;
    const box = strip.current!.getBoundingClientRect();
    move(d.k, (e.clientX - d.grab - box.left) / box.width, false);
  };
  /** The press ends: a drag is done, and a press that did not move picks the stop. */
  const release = (e: PointerEvent<HTMLDivElement>) => {
    const d = drag.current;
    if (!d || d.id !== e.pointerId) return;
    drag.current = null;
    if (d.moved) onCommit();
    else toggle(d.k);
  };
  /** The browser took the press (the page scrolls): the stop goes back, and the drag leaves no undo step. */
  const cancel = (e: PointerEvent<HTMLDivElement>) => {
    const d = drag.current;
    if (!d || d.id !== e.pointerId) return;
    drag.current = null;
    if (!d.moved || isEnd(d.k)) return;
    onRestore(d.from);
  };
  const keys = (k: number) => (e: KeyboardEvent<HTMLDivElement>) => {
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      return toggle(k);
    }
    if (e.key === "Delete" || e.key === "Backspace") {
      // Not the field's reset, which this key would otherwise reach.
      e.preventDefault();
      e.stopPropagation();
      if (isEnd(k)) return why.show(`the ${k === 0 ? "first" : "last"} stop stays: it holds ${k === 0 ? "0" : "1"}`);
      if (few) return why.show(fewWhy);
      why.close();
      send(stops.toSpliced(k, 1), true);
      if (open) pick(k - 1);
      (strip.current!.children[k - 1] as HTMLElement).focus();
      return sayStep(`stop ${k + 1} removed`);
    }
    const to = (at: number) => {
      if (isEnd(k)) return why.show(endWhy(k));
      why.close();
      move(k, at, true);
    };
    if (e.key === "Home" || e.key === "End") {
      e.preventDefault();
      // A step past the neighbour, which stops it there: a neighbour can lie between steps.
      const way = e.key === "Home" ? -1 : 1;
      return to((stops[k + way]?.at ?? stops[k]!.at) + way * p.stop.at.step);
    }
    stepKeys((n) => to(stops[k]!.at + n * p.stop.at.step))(e);
  };
  const name = `stop ${i + 1}`;
  const before = stops[i - 1], after = stops[i + 1];
  const css = (c: Stop) => cssRgb(displayRgb(c, gamma));
  const color: ColorParam = {
    ...PLAIN, kind: "color", name: `${p.name}.color`, label: name, parts: { h: p.stop.h, s: p.stop.s, v: p.stop.v }, default: stop,
  };
  return (
    <div className="control palette-control">
      {p.presets.length > 0 && (
        <div className="palette-tools">
          <Field.Select
            value={preset?.label ?? ""}
            onChange={(e) => {
              const next = p.presets.find((x) => x.label === e.currentTarget.value);
              if (next) put(next.value, true);
            }}
          >
            {!preset && (
              <option value="" disabled>
                custom
              </option>
            )}
            {p.presets.map((x) => (
              <option key={x.label} value={x.label}>
                {x.label}
              </option>
            ))}
          </Field.Select>
        </div>
      )}
      <div
        ref={strip}
        className="palette-strip"
        title={full ? undefined : "press to add a stop here"}
        style={{ backgroundImage: gradientCss(value, gamma) }}
        onClick={addHere}
      >
        {stops.map((s, k) => (
          <div
            key={k}
            role="slider"
            tabIndex={0}
            className="stop-marker"
            data-end={isEnd(k) || undefined}
            aria-label={`stop ${k + 1} of ${stops.length}`}
            aria-orientation="horizontal"
            aria-valuemin={isEnd(k) ? s.at : stops[k - 1]!.at}
            aria-valuemax={isEnd(k) ? s.at : stops[k + 1]!.at}
            aria-valuenow={s.at}
            aria-valuetext={formatNumber(p.stop.at, s.at)}
            aria-readonly={isEnd(k) || undefined}
            aria-current={open && k === i ? "true" : undefined}
            title={isEnd(k) ? "press to edit this stop" : "drag to move this stop; press to edit it; Delete removes it"}
            style={{ left: `${s.at * 100}%`, color: cssRgb(displayRgb(s, gamma)) }}
            onPointerDown={press}
            onPointerMove={pull}
            onPointerUp={release}
            onPointerCancel={cancel}
            // A click no press came before: assistive tech's.
            onClick={(e) => e.detail === 0 && toggle(k)}
            onKeyDown={keys(k)}
          />
        ))}
      </div>
      <DisclosureNote disclosure={why} live />
      {open && (
        <div className="stop-editor">
          <div className="stop-head">
            <div className="stop-step">
              <IconButton icon="left" label="previous stop" reason={i === 0 ? "this is the first stop" : null} note={why} onPress={() => step(i - 1)} />
              <span role="status">
                {name} of {stops.length}
              </span>
              <IconButton icon="right" label="next stop" reason={i === last ? "this is the last stop" : null} note={why} onPress={() => step(i + 1)} />
            </div>
            <div className="stop-actions">
              <Button variant="tertiary" reason={full ? fullWhy : null} note={why} onPress={add}>
                add stop
              </Button>
              <Button variant="tertiary" tone="danger" reason={few ? fewWhy : null} note={why} confirm="again to remove" disarmOn={stops.length} onPress={remove}>
                remove stop
              </Button>
            </div>
          </div>
          <div className="control color-control">
            {!before || !after ? (
              <p className="note">{before ? "ends the gradient, at 1" : "starts the gradient, at 0"}</p>
            ) : after.at - before.at < p.stop.at.step ? (
              <p className="note">no room to move: the stops before and after are both at {formatNumber(p.stop.at, before.at)}</p>
            ) : (
              <PartStrip
                channel="at"
                spec={p.stop.at}
                min={before.at}
                max={after.at}
                value={stop.at}
                caption={
                  <>
                    position
                    <span className="context">
                      <span className="sep"> · </span>
                      between stops {i} and {i + 2}
                    </span>
                  </>
                }
                label={`${name} position`}
                percent={false}
                track={`linear-gradient(to right in oklab, ${css(before)}, ${css(stop)} ${+(((stop.at - before.at) / (after.at - before.at)) * 100).toFixed(2)}%, ${css(after)})`}
                onChange={(x) => editStop({ at: x })}
                onCommit={onCommit}
                onNote={onNote}
              />
            )}
            <ColorParts p={color} value={stop} onChange={(c) => editStop(c)} onCommit={onCommit} onNote={onNote} name={name} />
          </div>
        </div>
      )}
    </div>
  );
}
