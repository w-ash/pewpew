import { Field } from "@ark-ui/react/field";
import type { ChoiceParam } from "../schema";
import { Segments } from "../../design/Segments";
import type { ControlProps } from "./types";

/** Options up to this many show at once (`Segments`); more go in a list. Every option reads in lower case,
 * as every label on the page does. */
const SEGMENTS_MAX = 5;

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
    <Segments
      className="control"
      items={p.options.map((o) => ({ value: o.value, label: o.label.toLowerCase() }))}
      value={value}
      labelId={labelId}
      describedBy={describedBy}
      onChange={choose}
    />
  );
}
