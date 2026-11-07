import { healthRows, okHint, type HealthState } from "../../domain/health/health";
import { useFrameGap, useFrameValue, useLayers, useWire } from "../../infra/wire/store";
import { Details } from "../common/Details";
import { onEngineHost } from "../common/host";
import { Panel } from "../common/Panel";
import { FINE_POINTER, useMedia } from "../common/useMedia";
import { FindBoards } from "./FindBoards";
import { HealthDot } from "./HealthDot";
import { failedText } from "./StatusBar";

export const HEALTH_PANEL = "health-panel";

// The page cannot hold a screen wake lock: that needs a secure context, and
// the private router serves plain http.
const WAKE = "Keep this phone's screen on while it controls the lights: set Auto-Lock or Screen timeout to Never.";

/** On a phone a row for this phone's screen, what to do first; then one row
 * per board, the rendering and whether the laptop can sleep, each led by its
 * status, then why it is not ok and what to do, its figures folded under
 * "details"; then find boards, which only an aura that streams to boards
 * offers. */
export function HealthPanel({ onClose }: { onClose(): void }) {
  const health = useWire((s) => s.health);
  return (
    <Panel id={HEALTH_PANEL} title="aura health" onClose={onClose}>
      {health ? <HealthBody health={health} /> : <p className="note">no health from the aura yet</p>}
    </Panel>
  );
}

function HealthBody({ health }: { health: HealthState }) {
  const gap = useFrameGap();
  const phone = !useMedia(FINE_POINTER);
  const map = useWire((s) => s.map);
  const t = useFrameValue((f) => (f ? Math.floor(f.t) : null));
  const failed = failedText(useWire((s) => s.error), useLayers());
  const hint = okHint(health);
  const rows = healthRows(health, gap, t !== null && map ? { t, n: map.n, total: map.total } : null, onEngineHost(), failed);
  return (
    <>
      {phone && (
        <div className="health-row" data-level="off">
          <div className="health-head">
            <HealthDot level="off" />
            <span className="name t-heading">this phone</span>
          </div>
          <div className="fix">{WAKE}</div>
        </div>
      )}
      {rows.map((r) => (
        <div key={r.key} className="health-row" data-level={r.level}>
          <div className="health-head">
            <HealthDot level={r.level} />
            <span className="name t-heading">{r.name}</span>
            {r.says !== "" && <span className="level">{r.says ?? r.level}</span>}
            {r.link && (
              <a href={r.link} target="_blank" rel="noopener">
                open WLED
              </a>
            )}
          </div>
          {r.reasons.map((why) => (
            <div key={why} className="why">
              {why}
            </div>
          ))}
          {r.fix && <div className="fix">{r.fix}</div>}
          <Details summary="details" className="facts t-value">
            {r.facts}
          </Details>
        </div>
      ))}
      {hint && <p className="note">{hint}</p>}
      {health.boards.length > 0 && <FindBoards health={health} />}
    </>
  );
}
