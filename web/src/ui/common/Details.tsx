import type { ReactNode } from "react";
import { Icon } from "./Icon";
import { spaced } from "./spaced";

/** More that most never need, folded under `summary` ("details"): a native disclosure with the page's
 * chevron, which points right while shut. */
export function Details({ summary, className, id, children }: { summary: string; className?: string; id?: string; children: ReactNode }) {
  return (
    <details id={id} className={spaced("details", className)}>
      <summary>
        <Icon name="chevron" />
        {summary}
      </summary>
      {children}
    </details>
  );
}
