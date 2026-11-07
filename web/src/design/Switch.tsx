import { useId, type ReactNode } from "react";

interface Props {
  readonly checked: boolean;
  onChange(on: boolean): void;
  readonly disabled?: boolean;
  /** What it turns on, after the switch. */
  readonly children: ReactNode;
  /** A control right after the words, its "?": drawn before the switch, which keeps the column's edge. */
  readonly after?: ReactNode;
}

/** A setting that stays on or off: its words, then a checkbox drawn and announced as a switch at the
 * column's edge, as a layer's row has it; the switch shows its state. The label is the target. A control in
 * `after` follows the words; the switch is named by the words alone. */
export function Switch({ checked, onChange, disabled, children, after }: Props) {
  const words = useId();
  return (
    <label className="bool-control">
      <span id={words}>{children}</span>
      <input
        type="checkbox"
        role="switch"
        className="switch"
        checked={checked}
        disabled={disabled}
        aria-labelledby={after ? words : undefined}
        onChange={(e) => onChange(e.currentTarget.checked)}
      />
      {after}
    </label>
  );
}
