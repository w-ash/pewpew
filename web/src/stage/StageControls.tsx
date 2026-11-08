import type { SelectItem } from "../design/Select";
import { Segments } from "../design/Segments";

/** What the stage draws: the flat map, or the rig in 3D. */
export type StageView = "2d" | "3d";

const ITEMS: readonly SelectItem[] = [
  { value: "2d", label: "2D" },
  { value: "3d", label: "3D" },
];

/** The stage's 2D/3D switch, at its bottom left. Shown only on an arrangement run: only a rig has a
 * 3D view (app/App.tsx). */
export function StageControls({ view, onChange }: { view: StageView; onChange(view: StageView): void }) {
  return (
    <div className="stage-switch">
      <Segments className="stage-veil" label="Stage view" items={ITEMS} value={view} onChange={(v) => onChange(v as StageView)} />
    </div>
  );
}
