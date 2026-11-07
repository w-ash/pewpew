import { Slider } from "@ark-ui/react/slider";
import { percent } from "../../domain/params/format";
import { SliderBody } from "../common/SliderBody";

/** The floor plan's opacity, this tab only. */
export function PlanDimmer({ value, onChange }: { value: number; onChange(v: number): void }) {
  return (
    <Slider.Root
      className="plan-dimmer"
      min={0}
      max={1}
      step={0.05}
      value={[value]}
      getAriaValueText={(d) => percent(d.value)}
      onValueChange={(d) => onChange(d.value[0] ?? value)}
    >
      <Slider.Label>plan</Slider.Label>
      <SliderBody />
      <output className="readout">{percent(value)}</output>
    </Slider.Root>
  );
}
