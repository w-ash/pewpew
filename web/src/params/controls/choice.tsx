import { Field } from "@ark-ui/react/field";
import { SegmentGroup } from "@ark-ui/react/segment-group";
import type { CSSProperties } from "react";
import type { ChoiceParam } from "../schema";
import type { ControlProps } from "./types";

/** Options up to this many show at once; more go in a list. From GRID_MIN, the options are cells of a
 * grid, each as wide as the longest, which wraps into rows on a narrow column. Every option reads in
 * lower case, as every label on the page does. */
const SEGMENTS_MAX = 5;
const GRID_MIN = 4;

export function ChoiceControl({ p, value, onChange, onCommit, labelId, describedBy }: ControlProps<ChoiceParam>) {
  const choose = (v: string) => {
    onChange(v);
    onCommit();
  };
  if (p.options.length > SEGMENTS_MAX) {
    return (
      <Field.Select className="control" value={value} onChange={(e) => choose(e.currentTarget.value)}>
        {p.options.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label.toLowerCase()}
          </option>
        ))}
      </Field.Select>
    );
  }
  return (
    <SegmentGroup.Root
      className="control segments"
      data-grid={p.options.length >= GRID_MIN || undefined}
      style={{ "--seg": `${Math.max(...p.options.map((o) => o.label.length))}ch` } as CSSProperties}
      value={value}
      ids={{ label: labelId }}
      aria-describedby={describedBy}
      onValueChange={(d) => d.value !== null && choose(d.value)}
    >
      <SegmentGroup.Indicator />
      {p.options.map((o) => (
        <SegmentGroup.Item key={o.value} value={o.value}>
          <SegmentGroup.ItemText>{o.label.toLowerCase()}</SegmentGroup.ItemText>
          <SegmentGroup.ItemControl />
          <SegmentGroup.ItemHiddenInput />
        </SegmentGroup.Item>
      ))}
    </SegmentGroup.Root>
  );
}
