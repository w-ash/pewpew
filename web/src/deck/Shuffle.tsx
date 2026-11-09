import { useId, useRef, useState } from "react";
import { eachItems, eachRequest, eachText, RIGHT_AWAY, rightAway, shuffleNote, shuffleOn, shuffleStatus, startItems, startRequest, type LooksState } from "../aura/looks";
import type { TriggersState } from "../aura/triggers";
import { useFrameValue, useSender } from "../wire/store";
import { Button } from "../design/Button";
import { Icon } from "../design/Icon";
import { Select } from "../design/Select";
import { Switch } from "../design/Switch";
import { useDismiss } from "../design/useDismiss";
import { useOnChange } from "../design/useOnChange";

/** Shuffle's row in the deck, under the make actions, a line tall: the one choice between the lights staying on
 * the look and the looks in shuffle taking turns, a switch at the column's edge, its word "shuffle" on the left.
 * Between them, what shuffle is doing: off, "stays on this look"; on, the turn it gives each look and when the next
 * comes (`1 min · next in 0:59`, `starts in 4:12` while it waits untouched), counted down on the frames' engine
 * time, or why it waits. On, that opens shuffle's settings in a well under the row: how long each look plays, and
 * whether it starts right away or after a while untouched; Esc or a press outside the row closes it. Each acts at
 * once and is kept in the looks file; a refusal goes to the status bar. Turned on, shuffle starts as it last did in
 * this page (right away, the first time). */
export function ShuffleRow({ looks, triggers }: { looks: LooksState; triggers: TriggersState | null }) {
  const sender = useSender();
  const group = useRef<HTMLDivElement>(null);
  const opener = useRef<HTMLButtonElement>(null);
  const settingsId = useId();
  const statusId = useId();
  const [open, setOpen] = useState(false);
  const on = shuffleOn(looks);
  // How shuffle starts while on, kept while it is off, for the switch to turn it on with.
  const startOf = (l: LooksState) => (l.idle === null || rightAway(l) ? RIGHT_AWAY : String(l.idle));
  const [lastStart, setLastStart] = useState(() => startOf(looks));
  useOnChange(looks.idle, () => {
    if (looks.idle !== null) setLastStart(startOf(looks));
  });
  useOnChange(on, () => setOpen(false));
  useDismiss(group, open, (esc) => {
    if (esc && group.current?.contains(document.activeElement)) opener.current?.focus();
    setOpen(false);
  });
  // The words do not follow the frames; the countdown, a string, re-renders the row once a second.
  const time = useFrameValue((f) => shuffleStatus(looks, triggers, f?.t ?? 0).time);
  const { words } = shuffleStatus(looks, triggers, 0);
  const each = eachItems(looks);
  const start = startItems(looks);
  const status = (
    <span id={statusId} className="shuffle-status">
      {time && <span className="shuffle-each">{eachText(looks)} ·</span>}
      <span className="t-label">{words}</span>
      {time && <span className="t-value">{time}</span>}
    </span>
  );
  return (
    <div ref={group} className="deck-group shuffle-group">
      <Switch
        checked={on}
        onChange={(next) => sender.send(next ? startRequest(looks, lastStart) : { type: "idle_cycle", idle: null })}
        after={
          on ? (
            <Button
              ref={opener}
              variant="tertiary"
              className="shuffle-open"
              aria-label={`shuffle settings: every ${eachText(looks)}`}
              aria-describedby={statusId}
              aria-expanded={open}
              aria-controls={settingsId}
              onPress={() => setOpen(!open)}
            >
              {status}
              <Icon name="chevron" />
            </Button>
          ) : (
            status
          )
        }
      >
        shuffle
      </Switch>
      {on && (
        <div id={settingsId} className="deck-more shuffle-settings" role="group" aria-label="shuffle settings" hidden={!open}>
          <div className="row">
            <Select
              items={each.items}
              value={each.value}
              label="how long each look plays"
              onChange={(v) => {
                if (v !== "range") sender.send(eachRequest(looks, Number(v)));
              }}
            />
            <Select items={start.items} value={start.value} label="when shuffle starts" onChange={(v) => sender.send(startRequest(looks, v))} />
          </div>
          <p className="note">{shuffleNote(looks)}</p>
        </div>
      )}
    </div>
  );
}
