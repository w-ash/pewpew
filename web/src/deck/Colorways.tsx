import { useId } from "react";
import type { LooksState } from "../aura/looks";
import type { StackState } from "../stack/stack";
import { useRefusal, useSender } from "../wire/store";
import { Button, ToggleButton } from "../design/Button";
import { roamTiles } from "../design/TileRow";

/** The running look's colorways, above its main knobs: a head line "colorways", as a knob's, then a chip each in
 * the look's order, wrapping onto more lines on a narrow column. A press sets every knob of that colorway at
 * once, an edit as a knob's is, while the look's motion carries on and the room glides to the new colours over
 * the look's fade. The active one, the first whose every value its knob holds now, is pressed (aria-pressed, the
 * selected fill) from the press on; turning one of its knobs by hand leaves none pressed. At the head's end, where
 * a knob's marks sit, a saved look with 2 colorways or more shows a square "drift" toggle (a wind sign, always
 * shown): it turns the look's colorway drift on or off, stored in the looks file at once as its shuffle switch
 * is; on, the look changes colorway by itself now and then, and the chips follow. A look with no colorways
 * shows no row. The chips are one tab stop, a toolbar as the looks row is: the pressed chip (the first when none
 * is) takes Tab, and the arrow keys, Home and End move between them. */
export function Colorways({ stack, looks }: { stack: StackState; looks: LooksState | null }) {
  const sender = useSender();
  const labelId = useId();
  const refusal = useRefusal("drift");
  if (!stack.colorways.length) return null;
  const current = looks && !looks.made ? (looks.items.find((item) => item.name === looks.current) ?? null) : null;
  const stop = stack.colorways.includes(stack.colorway ?? "") ? stack.colorway : stack.colorways[0];
  const drifts = current !== null && stack.colorways.length > 1;
  return (
    <div className="param colorways">
      <div className="param-head">
        <span id={labelId} className="t-label">
          colorways
        </span>
        {drifts && (
          <span className="knob-end">
            <ToggleButton
              variant="secondary"
              icon="drift"
              className="drift"
              pressed={current.drift}
              title={current.drift ? "drift: the colours move on by themselves now and then (press to hold them)" : "drift: let the colours move on by themselves now and then"}
              onPressedChange={(on) => sender.send({ type: "drift", name: current.name, on })}
            >
              drift
            </ToggleButton>
          </span>
        )}
      </div>
      <div className="colorway-chips" role="toolbar" aria-labelledby={labelId} onKeyDown={roamTiles}>
        {stack.colorways.map((name) => (
          <Button
            key={name}
            tabIndex={name === stop ? 0 : -1}
            aria-pressed={name === stack.colorway}
            title={`set the look's ${name} colours`}
            onPress={() => sender.send({ type: "colorway", name })}
          >
            {name}
          </Button>
        ))}
      </div>
      {drifts && refusal && (
        <p className="refusal" role="alert">
          {refusal.reason}
        </p>
      )}
    </div>
  );
}
