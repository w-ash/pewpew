import { cueDoes, cueText, type Held, type TriggersState } from "../aura/triggers";
import { useFrameValue, useSender } from "../wire/store";
import { Button } from "../design/Button";

/** One button per cue, firing its room event, its title saying what that does; the one holding its look in
 * amber. Each is as wide as its countdown, so one that counts down moves nothing. */
export function Cues({ triggers }: { triggers: TriggersState }) {
  const sender = useSender();
  if (!triggers.names.length) return null;
  return (
    <div className="scroller" role="group" aria-label="fire a cue">
      {triggers.names.map((name) => (
        <Button
          key={name}
          className="cue"
          title={cueDoes(name, triggers.cues)}
          held={triggers.held?.trigger === name}
          onPress={() => sender.send({ type: "fire", name, value: null })}
        >
          <span className="faces t-value">
            <CueText held={triggers.held} name={name} />
            <span className="sizer" aria-hidden="true">
              {name} · 00s
            </span>
          </span>
        </Button>
      ))}
    </div>
  );
}

/** The cue's name, and while it holds a look the seconds left at each
 * frame's engine time; it re-renders only when that text changes. */
function CueText({ held, name }: { held: Held | null; name: string }) {
  return <span>{useFrameValue((f) => cueText(name, held, f?.t ?? 0))}</span>;
}
