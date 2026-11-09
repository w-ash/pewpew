import { eachItems, eachRequest, eachText, shuffleOn, shuffleStatus, shuffleSwitch, startItems, startRequest, type LooksState } from "../aura/looks";
import type { TriggersState } from "../aura/triggers";
import { useFrameValue, useSender } from "../wire/store";
import { Button, ToggleButton } from "../design/Button";
import { useDisclosure } from "../design/Disclosure";
import { Icon } from "../design/Icon";
import { Select } from "../design/Select";
import { FINE_POINTER, useMedia, WIDE } from "../design/useMedia";

/** "shuffle", the one choice between the lights staying on the look and the looks in shuffle taking turns: a
 * press turns it on, right away, each look at the turn the looks file has, and a press turns it off. On, the
 * selected fill. Its word shows wide with a mouse, where the row has a column for it; else ↻ alone, so the make
 * row keeps one line down to a 360 px phone. */
export function ShuffleToggle({ looks }: { looks: LooksState }) {
  const sender = useSender();
  const fine = useMedia(FINE_POINTER);
  const wide = useMedia(WIDE);
  const worded = fine && wide;
  return (
    <ToggleButton
      className="shuffle"
      icon="cycle"
      label="shuffle"
      pressed={shuffleOn(looks)}
      onPressedChange={(on) => sender.send(shuffleSwitch(looks, on))}
    >
      {worded ? "shuffle" : undefined}
    </ToggleButton>
  );
}

/** While shuffle is on, a line under the make row: what it is doing (`next in 1:24`, `starts in 4:12`, or why it
 * waits), counted down on the frames' engine time, then at the column's edge the turn it gives each look
 * (`every 2 min ⌄`), which opens its settings under the line: how long each look plays, and whether it starts
 * right away or after a while untouched. Each choice acts at once and is kept in the looks file; a refusal goes
 * to the status bar. Off, there is no line: the lights stay on the look. */
export function ShuffleLine({ looks, triggers }: { looks: LooksState; triggers: TriggersState | null }) {
  const sender = useSender();
  const settings = useDisclosure();
  const status = useFrameValue((f) => shuffleStatus(looks, triggers, f?.t ?? 0));
  if (!shuffleOn(looks)) return null;
  const each = eachItems(looks);
  const start = startItems(looks);
  return (
    <div className="deck-group shuffle-group">
      <div className="row shuffle-line">
        <span className="note shuffle-status">
          <Icon name="cycle" />
          <span className="t-value">{status}</span>
        </span>
        <Button
          variant="tertiary"
          className="shuffle-open"
          aria-label={`shuffle settings: every ${eachText(looks)}`}
          aria-expanded={settings.open}
          aria-controls={settings.id}
          onPress={() => settings.toggle()}
        >
          every {eachText(looks)}
          <Icon name="chevron" />
        </Button>
      </div>
      <div id={settings.id} className="deck-more shuffle-settings" role="group" aria-label="shuffle settings" hidden={!settings.open}>
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
        <p className="note">any touch restarts the wait; a look's ⋯ puts it in shuffle</p>
      </div>
    </div>
  );
}
