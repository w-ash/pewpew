import { chip } from "../health/health";
import { useFrameGap, useWire } from "../wire/store";
import { Button } from "../design/Button";
import { HealthDot } from "./HealthDot";
import { HEALTH_PANEL } from "./HealthPanel";

/** The aura's health in a word, its sign before it; a press opens the health panel. */
export function HealthChip({ open, onToggle }: { open: boolean; onToggle(): void }) {
  const health = useWire((s) => s.health);
  const gap = useFrameGap();
  const failed = useWire((s) => s.error?.source === "render");
  if (!health) return null;
  const c = chip(health, gap, failed);
  return (
    <Button
      variant="tertiary"
      className="health-chip"
      data-level={c.level}
      aria-expanded={open}
      aria-controls={open ? HEALTH_PANEL : undefined}
      aria-label={c.label}
      title="aura health: boards, rendering, sleep"
      onPress={onToggle}
    >
      <HealthDot level={c.level} />
      <span className="t-value">{c.text}</span>
    </Button>
  );
}
