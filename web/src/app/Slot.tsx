import type { ReactNode } from "react";
import { LookSignals } from "../params/ParamPanel";
import { LayerList } from "../stack/LayerList";
import type { LayerSelection } from "../stack/selection";

interface SlotProps {
  /** A panel that takes the slot in place of the editor; null for none. */
  readonly panel: ReactNode;
  /** The look's header: its name and actions, or its main knobs. */
  readonly head: ReactNode;
  /** The id of the region's title, which names it. */
  readonly labelledBy: string;
  /** The layers and signals wait, inert, while a cue holds a look or a recall waits. */
  readonly held?: boolean;
  readonly selection: LayerSelection;
  readonly onAdd: () => void;
}

/** The side slot: the editor (the look's header, its layers, each open with its own knobs, and its signals), or
 * in its place a panel. The editor stays mounted under a panel: a typed look name, its toggles and a refusal that
 * comes meanwhile are still there when it closes. For assistive tech the look is one region, its blocks headed a
 * level under it. */
export function Slot({ panel, head, labelledBy, held, selection, onAdd }: SlotProps) {
  return (
    <>
      {panel}
      <div hidden={panel !== null}>
        <section className="look-region" aria-labelledby={labelledBy}>
          {head}
          <div className="rest" inert={held ?? false}>
            <LayerList selection={selection} onAdd={onAdd} />
            <LookSignals />
          </div>
        </section>
      </div>
    </>
  );
}
