import { cycleText } from "../aura/looks";
import { useWire } from "../wire/store";
import { Badge } from "../design/Badge";
import { IconButton, ToggleButton } from "../design/Button";
import { DisclosureButton, DisclosureNote, useDisclosure, type Disclosure } from "../design/Disclosure";
import type { IconName } from "../design/Icon";
import { Blackout } from "../deck/Blackout";
import { CUES_ABOUT } from "../deck/Triggers";
import { useLayoutMode } from "../layout/LayoutMode";
import { HealthChip } from "./HealthChip";

/** The connection while there is none: the look's header names what plays once there is. */
function Connection() {
  const word = useWire((s) => (s.connected ? null : s.session ? "offline" : "connecting…"));
  return <span className="connection">{word}</span>;
}

/** A mode the aura is in, as a badge, then the "?" that opens what it means. */
function ModeBadge({ word, icon, tone, note }: { word: string; icon?: IconName; tone?: "accent"; note: Disclosure }) {
  return (
    <>
      <Badge tone={tone} icon={icon} compact>
        {word}
      </Badge>
      <DisclosureButton disclosure={note} label={`about ${word}`} />
    </>
  );
}

/** The page's top line, status chrome only (RA-27c §3.5): the connection while there is none, the modes the
 * aura is in (each a badge, its "?" opening a note under the bar), aura health, layout, the shortcuts, and on
 * a phone on its side, where the side panel scrolls the deck away, blackout (page.css). The look's header
 * names what plays, and the deck holds the brightness. */
export function TopBar({ healthOpen, onHealth, onHelp }: { healthOpen: boolean; onHealth(): void; onHelp(): void }) {
  const layout = useLayoutMode();
  const cycle = useWire((s) => (s.aura?.looks?.cycling ? cycleText(s.aura.looks) : null));
  const armed = useWire((s) => !!s.aura?.triggers?.armed);
  const blackout = useWire((s) => s.aura?.blackout ?? null);
  const cycleNote = useDisclosure();
  const armedNote = useDisclosure();
  return (
    <>
      <header className="top-bar">
        <Connection />
        <div className="tags">
          {cycle !== null && <ModeBadge word="shuffle" icon="cycle" note={cycleNote} />}
          {armed && <ModeBadge word="cues on" tone="accent" note={armedNote} />}
          {blackout && (
            <span className="hides">
              <Badge tone="danger">blackout</Badge>
            </span>
          )}
        </div>
        {blackout !== null && <Blackout on={blackout} keyless />}
        <HealthChip open={healthOpen} onToggle={onHealth} />
        <ToggleButton variant="tertiary" className="layout-toggle" pressed={layout.on} onPressedChange={layout.setOn} title="layout tools (L)">
          layout
        </ToggleButton>
        <IconButton className="help" icon="command" label="keyboard shortcuts" title="keyboard shortcuts (?)" onPress={onHelp} />
      </header>
      {cycle !== null && <DisclosureNote disclosure={cycleNote}>{cycle}</DisclosureNote>}
      {armed && <DisclosureNote disclosure={armedNote}>{CUES_ABOUT}</DisclosureNote>}
    </>
  );
}
