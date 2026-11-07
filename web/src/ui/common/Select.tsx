export interface SelectItem {
  readonly value: string;
  readonly label: string;
  readonly disabled?: boolean;
}

interface Props {
  readonly items: readonly SelectItem[];
  readonly value: string | null;
  onChange(value: string): void;
  /** Its name, when no label element names it. */
  readonly label?: string;
  readonly title?: string;
  readonly className?: string;
  /** Waiting on the engine: its fill pulses. */
  readonly busy?: boolean;
  readonly disabled?: boolean;
  /** Take focus once shown: for a list that takes the place of the button that asked for it. */
  readonly autoFocus?: boolean;
}

/** Pick one of a list: the platform's own `<select>`, so a phone opens its native picker. */
export function Select({ items, value, onChange, label, title, className, busy, disabled, autoFocus }: Props) {
  return (
    <select
      className={className}
      autoFocus={autoFocus}
      disabled={disabled}
      value={value ?? ""}
      aria-label={label}
      title={title}
      data-busy={busy || undefined}
      aria-busy={busy || undefined}
      onChange={(e) => onChange(e.currentTarget.value)}
    >
      {items.map((item) => (
        <option key={item.value} value={item.value} disabled={item.disabled}>
          {item.label}
        </option>
      ))}
    </select>
  );
}
