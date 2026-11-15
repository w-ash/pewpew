import { Slider } from "@ark-ui/react/slider";
import { cssRgb, displayRgb } from "../color";
import { formatNumber, formatPart, percentOf } from "../format";
import { PARTS } from "../kinds/color";
import type { ReactNode } from "react";
import type { ColorParam, HSV, NumberSpec } from "../schema";
import { useWire } from "../../wire/store";
import { useSlideGuard } from "../../design/useSlideGuard";
import { NumberEntry } from "./NumberEntry";
import { stepKeys } from "./stepKeys";
import type { ControlProps, GlanceProps } from "./types";

const HUES = Array.from({ length: 25 }, (_, n) => n * 15);
const LEVELS = Array.from({ length: 9 }, (_, n) => n / 8);

/** What each part's strip shows, as the LEDs show it, so the color under a thumb is the color it sets: every
 * hue at full color; white to the hue; black to the color at full brightness. */
function stripOf(k: (typeof PARTS)[number], { h, s }: HSV, gamma: number): string {
  const along: readonly HSV[] =
    k === "h" ? HUES.map((hue) => ({ h: hue, s: 1, v: 1 })) : k === "s" ? LEVELS.map((x) => ({ h, s: x, v: 1 })) : LEVELS.map((x) => ({ h, s, v: x }));
  return `linear-gradient(to right, ${along.map((c) => cssRgb(displayRgb(c, gamma))).join(", ")})`;
}

interface StripProps {
  /** Which part it sets, for the page's styles and tests. */
  readonly channel: string;
  readonly spec: NumberSpec;
  /** Where its strip starts and ends, when not at the spec's own ends. */
  readonly min?: number;
  readonly max?: number;
  readonly value: number;
  /** Its name above it, and its full name for assistive tech. */
  readonly caption: ReactNode;
  readonly label: string;
  /** Read as a percent: a level from 0 to 1. A position is not. */
  readonly percent: boolean;
  /** What its strip shows: a CSS background. */
  readonly track: string;
  onChange(v: number): void;
  onCommit(): void;
  onNote(note: string | null): void;
}

/** One part of a color or a stop, laid out as a number knob is: its caption above a strip whose colors say
 * what the thumb sets, and its typed entry (on touch, the caption and entry on a line and the strip under
 * them). A `percent` part reads as one, on the strip as in the entry. Its keys step by the part's own step,
 * a hue wrapping. */
export function PartStrip({ channel, spec, min, max, value, caption, label, percent, track, onChange, onCommit, onNote }: StripProps) {
  const guard = useSlideGuard(value, onChange, onCommit);
  return (
    <div className="color-part">
      <span className="field-label" aria-hidden="true">
        {caption}
      </span>
      <Slider.Root
        data-channel={channel}
        min={min ?? spec.lo}
        max={max ?? spec.hi}
        step={spec.step}
        {...guard}
        onKeyDownCapture={stepKeys((n) => {
          onChange(value + n * spec.step);
          onCommit();
        })}
      >
        <Slider.Control>
          <Slider.Track style={{ background: track }} />
          <Slider.Thumb index={0} aria-label={label} aria-valuetext={percent ? formatPart(spec, value) : formatNumber(spec, value)}>
            <Slider.HiddenInput />
          </Slider.Thumb>
        </Slider.Control>
      </Slider.Root>
      <NumberEntry spec={spec} value={value} percent={percent} label={label} onChange={onChange} onCommit={onCommit} onNote={onNote} />
    </div>
  );
}

type PartsProps = Pick<ControlProps<ColorParam>, "p" | "value" | "onChange" | "onCommit" | "onNote" | "name">;

/** A color's three strips (hue, saturation, brightness), each named by its part and moving its own part
 * alone. The saturation strip runs at full brightness, so it shows at any. */
export function ColorParts({ p, value, onChange, onCommit, onNote, name }: PartsProps) {
  // A param exists only after a hello, which brings the gamma.
  const gamma = useWire((s) => s.gamma) ?? 1;
  return PARTS.map((k) => {
    const part = p.parts[k];
    const caption = (part.label || k).toLowerCase();
    return (
      <PartStrip
        key={k}
        channel={k}
        spec={part}
        value={value[k]}
        caption={caption}
        label={`${name} ${caption}`.toLowerCase()}
        percent={percentOf(part) !== null}
        track={stripOf(k, value, gamma)}
        onChange={(n) => onChange({ ...value, [k]: n })}
        onCommit={onCommit}
        onNote={onNote}
      />
    );
  });
}

/** color: its three parts (`ColorParts`), under its name. */
export function ColorControl(props: ControlProps<ColorParam>) {
  return (
    <div className="control color-control">
      <ColorParts {...props} />
    </div>
  );
}

/** The color as the LEDs show it, beside the field's label. */
export function ColorSwatch({ value }: GlanceProps<ColorParam>) {
  // A param exists only after a hello, which brings the gamma.
  const gamma = useWire((s) => s.gamma) ?? 1;
  return <span className="swatch" style={{ background: cssRgb(displayRgb(value, gamma)) }} />;
}
