// The Console's gizmo tools: whether the 3D view's gizmo moves or turns, and on which axes. The 3D view
// shows them over its canvas on a wide screen; on a phone, whose canvas is small, the layout panel shows
// them instead, so they cover none of it.
import { create } from "zustand";
import { ToggleButton } from "../design/Button";
import { Segments } from "../design/Segments";
import type { SelectItem } from "../design/Select";

export type GizmoMode = "translate" | "rotate";
export type GizmoSpace = "world" | "local";

interface GizmoTools {
  readonly mode: GizmoMode;
  readonly space: GizmoSpace;
  /** Whether the 3D view shows the gizmo: a fixture or group is selected while the editor is open. */
  readonly shown: boolean;
}

export const useGizmoTools = create<GizmoTools>()(() => ({ mode: "translate", space: "world", shown: false }));

const GIZMO_ITEMS: readonly SelectItem[] = [
  { value: "translate", label: "Move" },
  { value: "rotate", label: "Rotate" },
];

/** Move or Rotate, and World or Local axes; `className` styles each control. */
export function GizmoToolbar({ className }: { className?: string }) {
  const mode = useGizmoTools((s) => s.mode);
  const space = useGizmoTools((s) => s.space);
  return (
    <>
      <Segments
        className={className}
        label="Gizmo"
        items={GIZMO_ITEMS}
        value={mode}
        onChange={(m) => useGizmoTools.setState({ mode: m as GizmoMode })}
      />
      <ToggleButton
        className={className}
        variant="tertiary"
        pressed={space === "local"}
        onPressedChange={(local) => useGizmoTools.setState({ space: local ? "local" : "world" })}
        title="Gizmo axes"
      >
        {space === "world" ? "World" : "Local"}
      </ToggleButton>
    </>
  );
}
