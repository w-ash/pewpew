import { Slider } from "@ark-ui/react/slider";
import { percent } from "../params/format";
import { SliderBody } from "../design/SliderBody";
import { useSlideGuard } from "../design/useSlideGuard";

/** The floor plan's opacity, this tab only. */
export function PlanDimmer({ value, onChange }: { value: number; onChange(v: number): void }) {
  const guard = useSlideGuard(value, onChange, () => {});
  return (
    <Slider.Root
      className="plan-dimmer"
      min={0}
      max={1}
      step={0.05}
      getAriaValueText={(d) => percent(d.value)}
      {...guard}
    >
      <Slider.Label>plan</Slider.Label>
      <SliderBody />
      <output className="readout">{percent(value)}</output>
    </Slider.Root>
  );
}
