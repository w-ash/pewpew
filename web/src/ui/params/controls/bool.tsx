import { Field } from "@ark-ui/react/field";
import type { BoolParam } from "../../../domain/params/schema";
import type { ControlProps } from "./types";

/** bool: a native checkbox drawn and announced as a switch, and its state in
 * words. The label around them is the target: a full-height row on touch. */
export function BoolControl({ value, onChange, onCommit }: ControlProps<BoolParam>) {
  return (
    <label className="control bool-control">
      <Field.Input
        type="checkbox"
        role="switch"
        className="switch"
        checked={value}
        onChange={(e) => {
          onChange(e.currentTarget.checked);
          onCommit();
        }}
      />
      {/* The switch's own state says this; the words are for the eye. */}
      <span className="readout" aria-hidden>
        {value ? "on" : "off"}
      </span>
    </label>
  );
}
