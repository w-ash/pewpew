import { useEffect, useRef } from "react";
import { useSender } from "../wire/store";
import { Button } from "../design/Button";
import { sayStep } from "../design/StepStatus";

/** Blackout takes two presses; restoring takes one. A secondary button in the danger tone, found by its fixed
 * place. The server takes one message either way, and the room going black or coming back is said for
 * assistive tech, which may not read the button's new name. `keyless`: a second one, which leaves B, and
 * saying so, to the first. */
export function Blackout({ on, keyless }: { on: boolean; keyless?: boolean }) {
  const sender = useSender();
  const was = useRef(on);
  useEffect(() => {
    if (was.current === on) return;
    was.current = on;
    if (!keyless) sayStep(on ? "room blacked out" : "room restored");
  }, [on, keyless]);
  return (
    <Button
      className="blackout"
      tone={on ? undefined : "danger"}
      confirm="again to black out"
      twoPress={!on}
      disarmOn={on}
      shortcut={keyless ? undefined : { hotkey: "b", label: "blackout (twice) or restore" }}
      onPress={() => sender.send({ type: "blackout", on: !on })}
    >
      {on ? "restore" : "blackout"}
    </Button>
  );
}
