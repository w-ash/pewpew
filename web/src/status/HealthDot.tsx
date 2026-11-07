import type { Level } from "../health/health";
import { Icon } from "../design/Icon";

/** A health level's sign, beside its word: a dot, green when ok and red when bad, or ▲ for a warning. */
export function HealthDot({ level }: { level: Level | "off" }) {
  return (
    <span className="health-dot" data-level={level} aria-hidden="true">
      <Icon name={level === "warn" ? "up" : "dot"} />
    </span>
  );
}
