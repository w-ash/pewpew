// Which layer of the running look the editor shows, and where focus goes after an edit moves
// the control that had it (an added layer's row, the row next to a removed one).
import { useState } from "react";
import { useLayers } from "../../infra/wire/store";

/** The focus target of the "+ layer" button, which is never a layer id. */
export const ADD = "+";

export interface LayerSelection {
  /** The layer picked while it runs, else the top one; null before the engine sends the aura state. */
  readonly id: string | null;
  /** The layer whose row takes focus once drawn, `ADD` for the "+ layer" button, or null. */
  readonly focus: string | null;
  select(id: string): void;
  /** Ask for `target`, a layer id or `ADD`, to take focus once drawn. */
  focusOn(target: string): void;
  /** The control asked for took focus. */
  focused(): void;
}

export function useLayerSelection(): LayerSelection {
  const layers = useLayers();
  const [chosen, setChosen] = useState<string | null>(null);
  const [focus, setFocus] = useState<string | null>(null);
  return {
    id: layers.some((l) => l.id === chosen) ? chosen : (layers.at(-1)?.id ?? null),
    focus,
    select: setChosen,
    focusOn: setFocus,
    focused: () => setFocus(null),
  };
}
