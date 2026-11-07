import { Slider } from "@ark-ui/react/slider";
import { cssRgb, displayRgb } from "../../../domain/params/color";
import { formatPart, percentOf } from "../../../domain/params/format";
import { PARTS } from "../../../domain/params/kinds/color";
import type { ColorParam, HSV } from "../../../domain/params/schema";
import { useWire } from "../../../infra/wire/store";
import { NumberEntry } from "./NumberEntry";
import { stepKeys } from "./stepKeys";
import type { ControlProps, GlanceProps } from "./types";

const HUES = [0, 60, 120, 180, 240, 300, 360].map((h) => `hsl(${h} 100% 50%)`).join(", ");

/** What each part's strip shows: every hue at full color; white to the hue; black to the color at full
 * brightness. */
function stripOf(k: (typeof PARTS)[number], { h, s }: HSV): string {
  const to = k === "h" ? HUES : k === "s" ? `#fff, hsl(${h} 100% 50%)` : `#000, hsl(${h} 100% ${100 - s * 50}%)`;
  return `linear-gradient(to right, ${to})`;
}

/** color: per part, laid out as a number knob is: its label (hue, saturation, brightness) above a
 * strip one thumb high and its typed entry (on touch, the label and entry on a line and the strip
 * under them); saturation and brightness read as percents, on the strip as in the entry. The
 * saturation strip runs at full brightness, so it shows at any. Each strip and entry is named by its
 * part; a strip moves its own part alone. Its keys step by the part's own step, the hue wrapping. */
export function ColorControl({ p, value, onChange, onCommit, onNote, name }: ControlProps<ColorParam>) {
  return (
    <div className="control color-control">
      {PARTS.map((k) => {
        const part = p.parts[k];
        const label = `${name} ${part.label || k}`.toLowerCase();
        return (
          <div key={k} className="color-part">
            <span className="field-label" aria-hidden="true">
              {(part.label || k).toLowerCase()}
            </span>
            <Slider.Root
              data-channel={k}
              min={part.lo}
              max={part.hi}
              step={part.step}
              value={[value[k]]}
              onValueChange={(d) => onChange({ ...value, [k]: d.value[0] ?? value[k] })}
              onValueChangeEnd={onCommit}
              onKeyDownCapture={stepKeys((n) => {
                onChange({ ...value, [k]: value[k] + n * part.step });
                onCommit();
              })}
            >
              <Slider.Control>
                <Slider.Track style={{ background: stripOf(k, value) }} />
                <Slider.Thumb index={0} aria-label={label} aria-valuetext={formatPart(part, value[k])}>
                  <Slider.HiddenInput />
                </Slider.Thumb>
              </Slider.Control>
            </Slider.Root>
            <NumberEntry
              spec={part}
              value={value[k]}
              percent={percentOf(part) !== null}
              label={label}
              onChange={(n) => onChange({ ...value, [k]: n })}
              onCommit={onCommit}
              onNote={onNote}
            />
          </div>
        );
      })}
    </div>
  );
}

/** The color as the LEDs show it, beside the field's label. */
export function ColorSwatch({ value }: GlanceProps<ColorParam>) {
  // A param exists only after a hello, which brings the gamma.
  const gamma = useWire((s) => s.gamma) ?? 1;
  return <span className="swatch" style={{ background: cssRgb(displayRgb(value, gamma)) }} />;
}
