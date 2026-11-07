import { type ReactNode, useEffect, useId, useState } from "react";
import { cn } from "@/lib/cn";

export function SectionHeading({ children }: { children: ReactNode }) {
  return (
    <h2 className="mb-2 text-[11px] font-semibold uppercase tracking-[0.1em] text-muted">
      {children}
    </h2>
  );
}

export function Button({
  children,
  onClick,
  disabled,
  variant = "default",
  title,
}: {
  children: ReactNode;
  onClick?: () => void;
  disabled?: boolean;
  variant?: "default" | "primary" | "danger";
  title?: string;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      title={title}
      className={cn(
        "inline-flex min-h-11 min-w-11 items-center justify-center gap-1.5 rounded-md border px-3 text-sm",
        "disabled:cursor-not-allowed disabled:opacity-40",
        variant === "default" &&
          "border-line bg-surface text-ink hover:border-muted",
        variant === "primary" &&
          "border-accent bg-accent text-surface hover:opacity-90",
        variant === "danger" &&
          "border-line bg-surface text-error hover:border-error",
      )}
    >
      {children}
    </button>
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
    <label
      htmlFor={id}
      className="flex min-w-0 flex-col gap-1 text-xs text-muted"
    >
      <span>
        {label}
        {unit && <span className="opacity-70"> {unit}</span>}
      </span>
      <input
        id={id}
        type="number"
        inputMode="decimal"
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
        className="h-11 w-full min-w-0 rounded-md border border-line bg-bg px-2 font-data text-sm text-ink tabular-nums focus:border-accent focus:outline-none"
      />
    </label>
  );
}

export function Select<T extends string>({
  label,
  value,
  options,
  onChange,
}: {
  label: string;
  value: T;
  options: ReadonlyArray<{ value: T; label: string }>;
  onChange: (value: T) => void;
}) {
  const id = useId();
  return (
    <label
      htmlFor={id}
      className="flex min-w-0 flex-col gap-1 text-xs text-muted"
    >
      <span>{label}</span>
      <select
        id={id}
        value={value}
        onChange={(e) => onChange(e.target.value as T)}
        className="h-11 w-full min-w-0 rounded-md border border-line bg-bg px-2 text-sm text-ink focus:border-accent focus:outline-none"
      >
        {options.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
      </select>
    </label>
  );
}
