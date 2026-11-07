import type { ReactNode } from "react";
import { Icon, type IconName } from "./Icon";

/** A state in a word, and a sign when it has one: an eyebrow on the raised surface, never pressable.
 * `compact`: on touch, the sign alone, the word kept for assistive tech. */
export function Badge({ children, tone, icon, compact }: { children: ReactNode; tone?: "accent" | "danger"; icon?: IconName; compact?: boolean }) {
  return (
    <span className="badge t-eyebrow" data-tone={tone} data-compact={(compact && !!icon) || undefined}>
      {icon && <Icon name={icon} />}
      <span className="badge-word">{children}</span>
    </span>
  );
}
