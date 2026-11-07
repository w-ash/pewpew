import { Select, type SelectItem } from "@pewpew/page";
import { type ReactNode, useEffect, useId, useState } from "react";

export function SectionHeading({ children }: { children: ReactNode }) {
  return <h2 className="t-eyebrow">{children}</h2>;
}

/** A control under its visible name, as the page's knobs are. */
export function Field({
  label,
  unit,
  htmlFor,
  children,
}: {
  label: string;
  unit?: string;
  htmlFor?: string;
  children: ReactNode;
}) {
  return (
    <label htmlFor={htmlFor} className="studio-field">
      <span className="field-label">
        {label}
        {unit && ` ${unit}`}
      </span>
      {children}
    </label>
  );
}

/**
 * A number input that keeps what is typed until it parses, then reports
 * each valid value. It follows `value` whenever it is not being edited.
 * With `onClear`, an empty field reports a clear and a null `value` shows
 * as empty.
 */
export function NumberField({
  label,
  value,
  onChange,
  onClear,
  placeholder,
  step = 0.01,
  min,
  max,
  unit,
  decimals = 3,
  integer = false,
}: {
  label: string;
  value: number | null;
  onChange: (value: number) => void;
  onClear?: () => void;
  placeholder?: string;
  step?: number;
  min?: number;
  max?: number;
  unit?: string;
  decimals?: number;
  integer?: boolean;
}) {
  const id = useId();
  const format = (v: number | null) =>
    v === null
      ? ""
      : integer
        ? String(Math.round(v))
        : String(Number(v.toFixed(decimals)));
  const [text, setText] = useState(format(value));
  const [editing, setEditing] = useState(false);
  // biome-ignore lint/correctness/useExhaustiveDependencies: `format` depends only on props already listed.
  useEffect(() => {
    if (!editing) setText(format(value));
  }, [value, editing, decimals, integer]);
  return (
    <Field label={label} unit={unit} htmlFor={id}>
      <input
        id={id}
        type="number"
        inputMode="decimal"
        className="t-value"
        step={step}
        min={min}
        max={max}
        placeholder={placeholder}
        value={text}
        onFocus={() => setEditing(true)}
        onBlur={() => {
          setEditing(false);
          setText(format(value));
        }}
        onChange={(e) => {
          setText(e.target.value);
          const v = Number(e.target.value);
          if (e.target.value.trim() === "") {
            onClear?.();
            return;
          }
          if (!Number.isFinite(v)) return;
          if ((min !== undefined && v < min) || (max !== undefined && v > max))
            return;
          onChange(integer ? Math.round(v) : v);
        }}
      />
    </Field>
  );
}

/** The page's Select under a visible name. */
export function SelectField<T extends string>({
  label,
  value,
  options,
  onChange,
}: {
  label: string;
  value: T;
  options: readonly SelectItem[];
  onChange: (value: T) => void;
}) {
  return (
    <Field label={label}>
      <Select
        items={options}
        value={value}
        onChange={(v) => onChange(v as T)}
      />
    </Field>
  );
}
