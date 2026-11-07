import { Slider } from "@ark-ui/react/slider";
import { formatNumber, percent } from "../../../domain/params/format";
import { isOpacity } from "../../../domain/stack/stack";
import type { FloatParam, IntParam } from "../../../domain/params/schema";
import { SliderBody } from "../../common/SliderBody";
import { NumberEntry } from "./NumberEntry";
import type { ControlProps } from "./types";

/** float and int: a slider, and typed entry beside it. A route's live value is a mark on the
 * slider; the thumb and its value text stay on the knob's own value. A layer's opacity reads as a
 * percent, as the master does. */
export function NumberControl({ p, value, onChange, onCommit, onNote, labelId, name, describedBy, live }: ControlProps<FloatParam | IntParam>) {
  const pct = isOpacity(p);
  return (
    <div className="control number-control">
      <Slider.Root
        min={p.lo}
        max={p.hi}
        step={p.step}
        value={[value]}
        ids={{ label: labelId }}
        getAriaValueText={(d) => (pct ? percent(d.value) : formatNumber(p, d.value))}
        onValueChange={(d) => onChange(d.value[0] ?? value)}
        onValueChangeEnd={onCommit}
      >
        <SliderBody live={live} describedBy={describedBy} />
      </Slider.Root>
      <NumberEntry spec={p} value={value} percent={pct} label={name} describedBy={describedBy} onChange={onChange} onCommit={onCommit} onNote={onNote} />
    </div>
  );
}
