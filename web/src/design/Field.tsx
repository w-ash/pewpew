import type { ReactNode } from "react";
import { Select, type SelectItem } from "./Select";

/** A control under its visible name, as a knob's is. */
export function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <label className="field">
      <span className="field-label">{label}</span>
      {children}
    </label>
  );
}

/** A `Select` under its visible name. */
export function SelectField<T extends string>({ label, value, items, onChange }: { label: string; value: T; items: readonly SelectItem[]; onChange(value: T): void }) {
  return (
    <Field label={label}>
      <Select items={items} value={value} onChange={(v) => onChange(v as T)} />
    </Field>
  );
}
