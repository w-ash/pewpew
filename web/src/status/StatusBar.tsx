import { useState } from "react";
import { formatValue } from "../params/kinds";
import { caption } from "../params/schema";
import { layerOf, nodeAt, type LayerItem } from "../stack/stack";
import { setParam } from "../wire/protocol";
import { useLayers, useSender, useWire, type EngineError, type Refusal } from "../wire/store";
import { Button } from "../design/Button";
import { Details } from "../design/Details";
import { focusParam } from "../design/useFocusKeeper";
import { FINE_POINTER, useMedia } from "../design/useMedia";
import { useOnChange } from "../design/useOnChange";
import { EDIT_MS, useLastSet, type LastSet } from "../params/lastSet";
import { useShownRefusal } from "./refusal";

/** The bar's lines: a refusal, else the engine's error, else the plan note.
 * A layer that raises gets what the room shows and what to do first, then
 * the engine's own text. `layers` are the running look's, bottom first;
 * `looks` says whether there are looks to pick; `edit` is the set that most
 * likely made it raise, in words, or null. */
export function barLines(
  refusal: Refusal | null,
  error: EngineError | null,
  layers: readonly LayerItem[],
  looks: boolean,
  planNote: string | null,
  edit: string | null = null,
): readonly string[] {
  if (refusal) return [refusal.reason];
  if (error?.source === "render" && error.path) return [failedLine(error.path, layers, looks, edit), error.text];
  if (error) return [error.text];
  return planNote ? [planNote] : [];
}

/** What the room shows when the layer node at `address` raises, and what to do, naming the node
 * by its label (its op's): after `edit`, put it back (the bar offers it); else move off it: another
 * look, or for a lone layer without looks, a new layer in its place. Only a lone layer surely pulses
 * red: with others, an unattended run leaves the failing one out of the mix, and its row can turn it
 * off or remove it. */
function failedLine(address: string, layers: readonly LayerItem[], looks: boolean, edit: string | null): string {
  const label = nodeAt(address, layers)?.label;
  const lone = layers.length <= 1;
  const layer = layerOf(address);
  const what = lone ? `The room is pulsing red: ${label ?? address}` : label ? `Layer ${layer} (${label})` : `Layer ${layer ?? address}`;
  if (edit) return `${what} failed after ${edit}.`;
  if (lone) return `${what} failed. ${looks ? "Pick another look." : "Add a layer, then remove this one."}`;
  return `${what} failed. Turn it off or remove it.`;
}

/** What failed while a layer's render raises, in a few words (`base · Oscillator failed`), else null: the bar's
 * lead on touch, and the health panel's reason. */
export function failedText(error: EngineError | null, layers: readonly LayerItem[]): string | null {
  const path = error?.source === "render" ? error.path : null;
  if (!path) return null;
  const label = nodeAt(path, layers)?.label;
  return `${[layers.length > 1 && layerOf(path), label].filter(Boolean).join(" · ") || path} failed`;
}

/** The knob set last, when a render error at `error` came within EDIT_MS of its set (at `errorAt`) from
 * a knob of the node that raised: what most likely made it raise. */
function blamed(last: LastSet | null, error: EngineError | null, errorAt: number): LastSet | null {
  const path = error?.source === "render" ? error.path : null;
  return last && path && last.p.name.startsWith(`${path}.`) && errorAt - last.at < EDIT_MS ? last : null;
}

/** The engine's error, which persists until the engine clears it, the plan
 * note, and a refusal, which borrows the bar (`useShownRefusal`). The
 * engine's own text follows the lead, folded under "details", so the bar
 * leaves the stage in view. A render error just after a knob of the node
 * that raised was set names the knob, and offers its value back; putting
 * it back takes focus to the knob, as the button goes. On touch, where the
 * stage is short, an error's lead is what failed, on one line with the put
 * back, and the sentence waits under "details" too. `coverRef` measures it:
 * the stage fits the room under it. */
export function StatusBar({ planNote, coverRef }: { planNote: string | null; coverRef?: (el: HTMLElement | null) => void }) {
  const error = useWire((s) => s.error);
  const looks = useWire((s) => !!s.aura?.looks);
  const layers = useLayers();
  const sender = useSender();
  const fine = useMedia(FINE_POINTER);
  const last = useLastSet();
  const [errorAt, setErrorAt] = useState(0);
  useOnChange(error, () => setErrorAt(performance.now()));
  const shown = useShownRefusal();
  const edit = shown ? null : blamed(last, error, errorAt);
  const value = (v: unknown) => (edit ? formatValue(edit.p, v as never) : "");
  const [lead, detail] = barLines(shown, error, layers, looks, planNote, edit && `${caption(edit.p).toLowerCase()} went to ${value(edit.to)}`);
  const short = !fine && !shown ? failedText(error, layers) : null;
  return (
    <div ref={coverRef} className="status-bar" role="status" aria-live="polite" hidden={!lead} data-kind={shown || error ? "error" : "plan"}>
      <span className="status-lead">{short ?? lead}</span>
      {edit && (
        <Button
          className="put-back"
          onPress={() => {
            focusParam(edit.p.name);
            setParam(sender, edit.p, edit.from as never);
          }}
        >
          put back {value(edit.from)}
        </Button>
      )}
      {detail && (
        <Details summary="details">
          {short && <p>{lead}</p>}
          <div className="status-detail">{detail}</div>
        </Details>
      )}
    </div>
  );
}
