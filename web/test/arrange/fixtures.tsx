import goldenRings from "../../../src/pewpew/rig/examples/golden-rings.json";
import { asArrangement } from "../../src/arrange/arrangement";
import { ArrangementPanel, type ArrangementPanelProps } from "../../src/arrange/ArrangementPanel";
import { useDocEditor } from "../../src/arrange/doc";
import type { Arrangement } from "../../src/arrange/types";

/** The golden rings, from the rig package's examples: two ring groups. */
export const RINGS = asArrangement(goldenRings) as Arrangement;

type Bound = "arrangement" | "onCommit" | "selection" | "onSelect" | "canUndo" | "canRedo" | "onUndo" | "onRedo";

/** The arrangement panel on the doc store, as the Console and the studio wire it. */
export function DocPanel(props: Omit<ArrangementPanelProps, Bound>) {
  return <ArrangementPanel {...props} {...useDocEditor()} />;
}
