import { Slider } from "@ark-ui/react/slider";

/** A one-thumb slider's track and thumb, inside a Slider.Root, and a mark at `live` when given:
 * the value a route moves the knob to, hidden from assistive tech (the value text is the thumb's).
 * `describedBy` names what describes the thumb. */
export function SliderBody({ live, describedBy }: { live?: number | null; describedBy?: string | undefined }) {
  return (
    <Slider.Control>
      <Slider.Track>
        <Slider.Range />
      </Slider.Track>
      {live != null && <Slider.Marker className="live-mark" value={live} />}
      <Slider.Thumb index={0} aria-describedby={describedBy}>
        <Slider.HiddenInput />
      </Slider.Thumb>
    </Slider.Control>
  );
}
