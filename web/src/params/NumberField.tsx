import { useState } from "react";
import type { NumberSpec } from "./schema";
import { NumberEntry } from "./controls/NumberEntry";

/** What a number field takes: a knob's range, step and unit, without its tick labels. */
export type NumberRange = Omit<NumberSpec, "text">;

/** A number that is no knob, as a knob types one (`NumberEntry`) under its visible name: − and + step it, a
 * typed value goes on Enter or blur, and what became of a typed value it could not take says so under it.
 * `percent` shows a 0..1 level as a percent. */
export function NumberField({ label, value, range, percent, onChange }: { label: string; value: number; range: NumberRange; percent?: boolean; onChange(v: number): void }) {
  const [note, setNote] = useState<string | null>(null);
  return (
    <div className="field number-field">
      <span className="field-label" aria-hidden="true">
        {label}
      </span>
      <NumberEntry spec={{ ...range, text: [] }} value={value} label={label} percent={percent} onChange={onChange} onCommit={() => {}} onNote={setNote} />
      {note && (
        <p className="note" role="status">
          {note}
        </p>
      )}
    </div>
  );
}
