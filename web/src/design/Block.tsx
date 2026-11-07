import { useId, type ReactNode } from "react";
import { spaced } from "./spaced";

/** A block of a column under its heading, as the editor's layers and modulators are: the heading names the
 * region, and `actions` end the head's line. A `focusable` heading can take focus when what had it goes
 * away. */
export function Block({ title, actions, focusable, className, children }: { title: ReactNode; actions?: ReactNode; focusable?: boolean; className?: string; children?: ReactNode }) {
  const headId = useId();
  return (
    <section className={spaced("block", className)} aria-labelledby={headId}>
      <header className="block-head">
        <h3 id={headId} className="t-heading" tabIndex={focusable ? -1 : undefined}>
          {title}
        </h3>
        {actions}
      </header>
      {children}
    </section>
  );
}
