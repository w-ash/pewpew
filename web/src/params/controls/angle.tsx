import type { FloatParam } from "../schema";
import type { GlanceProps } from "./types";

/** float with widget "angle", a direction in the room: a number knob, its slider as long as every other
 * knob's at every width, and beside its label a dial, drawn only, its hand where the value points on the
 * room plan: counterclockwise from +x. */
export function AngleGlance({ value }: GlanceProps<FloatParam>) {
  return <span className="compass" aria-hidden="true" style={{ rotate: `${-value}deg` }} />;
}
