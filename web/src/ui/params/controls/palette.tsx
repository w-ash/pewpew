import { Field } from "@ark-ui/react/field";
import { useId, useState } from "react";
import { cssRgb, displayRgb, gradientCss } from "../../../domain/params/color";
import { formatNumber } from "../../../domain/params/format";
import { palette } from "../../../domain/params/kinds/palette";
import type { ColorParam, FloatParam, PaletteParam, Stop } from "../../../domain/params/schema";
import { useWire } from "../../../infra/wire/store";
import { Button } from "../../common/Button";
import { DisclosureNote, useDisclosure } from "../../common/Disclosure";
import { ColorControl } from "./color";
import { NumberControl } from "./number";
import type { ControlProps } from "./types";

const PLAIN = { help: "", group: "", widget: "", layer: "", node: "" } as const;

/** palette: a preset list, the gradient as the LEDs show it with a marker
 * per stop, and, once a marker is pressed, its stop's editor: which stop of
 * how many (said as it changes), add and remove (in two presses), its
 * position (the ends stay at 0 and 1), labelled above it as a param is, and
 * its color, edited as a color param is; a second press on the marker folds
 * it. Add and remove at their limits say why when pressed. Any edit of a stop
 * makes the palette custom. */
export function PaletteControl({ p, value, onChange, onCommit, onNote, labelId }: ControlProps<PaletteParam>) {
  // A param exists only after a hello, which brings the gamma.
  const gamma = useWire((s) => s.gamma) ?? 1;
  const [picked, pick] = useState<number | null>(null);
  const why = useDisclosure();
  const positionId = useId();
  const { stops } = value;
  const last = stops.length - 1;
  const i = Math.min(picked ?? 0, last);
  const stop = stops[i]!;
  const preset = p.presets.find((x) => palette.equal(x.value, value));
  const send = (next: readonly Stop[], commit: boolean) => {
    onChange({ label: "", stops: next });
    if (commit) onCommit();
  };
  const editStop = (patch: Partial<Stop>) => send(stops.with(i, { ...stop, ...patch }), false);
  const full = stops.length >= p.maxStops, few = stops.length <= 2;
  const add = () => {
    why.close();
    const k = i === last ? i - 1 : i; // the new stop goes halfway from stop k to the next
    send(stops.toSpliced(k + 1, 0, { ...stops[k]!, at: (stops[k]!.at + stops[k + 1]!.at) / 2 }), true);
    pick(k + 1);
  };
  const remove = () => {
    why.close();
    send(stops.toSpliced(i, 1), true);
    pick(Math.max(i - 1, 0));
  };
  const name = `stop ${i + 1}`;
  const at: FloatParam = { ...p.stop.at, ...PLAIN, kind: "float", name: `${p.name}.at`, label: `${name} position`, default: 0 };
  const color: ColorParam = {
    ...PLAIN, kind: "color", name: `${p.name}.color`, label: name, parts: { h: p.stop.h, s: p.stop.s, v: p.stop.v }, default: stop,
  };
  return (
    <div className="control palette-control">
      {p.presets.length > 0 && (
        <Field.Select
          value={preset?.label ?? ""}
          onChange={(e) => {
            const next = p.presets.find((x) => x.label === e.currentTarget.value);
            if (!next) return;
            onChange(next.value);
            onCommit();
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
      )}
      <div className="palette-strip" style={{ backgroundImage: gradientCss(value, gamma) }}>
        {stops.map((s, k) => (
          <button
            key={k}
            type="button"
            className="stop-marker"
            aria-label={`stop ${k + 1} at ${formatNumber(p.stop.at, s.at)}`}
            aria-pressed={picked !== null && k === i}
            title="edit this stop"
            style={{ left: `${s.at * 100}%`, color: cssRgb(displayRgb(s, gamma)) }}
            onClick={() => pick(picked !== null && k === i ? null : k)}
          />
        ))}
      </div>
      {picked !== null && (
        <div className="stop-editor">
          <div className="stop-head">
            <span role="status">
              {name} of {stops.length}
            </span>
            <div className="stop-actions">
              <Button variant="tertiary" reason={full ? `a palette has at most ${p.maxStops} stops` : null} note={why} onPress={add}>
                add stop
              </Button>
              <Button variant="tertiary" tone="danger" reason={few ? "a palette needs two stops" : null} note={why} confirm="again to remove" disarmOn={stops.length} onPress={remove}>
                remove stop
              </Button>
            </div>
          </div>
          <DisclosureNote disclosure={why} live />
          {i > 0 && i < last ? (
            <div className="stop-position">
              <div className="param-head">
                <span id={positionId} className="field-label">
                  <span className="sr-only">{name} </span>position
                </span>
              </div>
              <NumberControl
                p={at}
                value={stop.at}
                onChange={(x) => editStop({ at: x })}
                onCommit={onCommit}
                onNote={onNote}
                labelId={positionId}
                name={at.label}
              />
            </div>
          ) : (
            <p className="note">{i === 0 ? "starts the gradient, at 0" : "ends the gradient, at 1"}</p>
          )}
          <ColorControl p={color} value={stop} onChange={(c) => editStop(c)} onCommit={onCommit} onNote={onNote} labelId={labelId} name={name} />
        </div>
      )}
    </div>
  );
}
