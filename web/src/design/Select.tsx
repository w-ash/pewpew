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
  readonly className?: string;
  readonly disabled?: boolean;
}

/** Pick one of a list: the platform's own `<select>`, so a phone opens its native picker. */
export function Select({ items, value, onChange, label, className, disabled }: Props) {
  return (
    <select
      className={className}
      disabled={disabled}
      value={value ?? ""}
      aria-label={label}
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
