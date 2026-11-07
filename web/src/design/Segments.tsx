import { SegmentGroup } from "@ark-ui/react/segment-group";
import type { CSSProperties } from "react";
import type { SelectItem } from "./Select";
import { spaced } from "./spaced";

/** From this many options, the options are cells of a grid. */
const GRID_MIN = 4;

/** Pick one of a few, every option shown, the chosen one in the selected fill. From GRID_MIN options, the
 * options are cells of a grid, each as wide as the longest, which wraps into rows on a narrow column. It is
 * named by `label`, or by the element `labelId` names. */
export function Segments({ items, value, onChange, label, labelId, describedBy, className }: { items: readonly SelectItem[]; value: string; onChange(value: string): void; label?: string; labelId?: string; describedBy?: string | undefined; className?: string }) {
  return (
    <SegmentGroup.Root
      className={spaced("segments", className)}
      data-grid={items.length >= GRID_MIN || undefined}
      style={{ "--seg": `${Math.max(...items.map((o) => o.label.length))}ch` } as CSSProperties}
      value={value}
      ids={labelId ? { label: labelId } : undefined}
      aria-label={label}
      aria-describedby={describedBy}
      onValueChange={(d) => d.value !== null && onChange(d.value)}
    >
      <SegmentGroup.Indicator />
      {items.map((o) => (
        <SegmentGroup.Item key={o.value} value={o.value} disabled={o.disabled}>
          <SegmentGroup.ItemText>{o.label}</SegmentGroup.ItemText>
          <SegmentGroup.ItemControl />
          <SegmentGroup.ItemHiddenInput />
        </SegmentGroup.Item>
      ))}
    </SegmentGroup.Root>
  );
}
