import { useId } from "react";
import type { StackState } from "../stack/stack";
import { useSender } from "../wire/store";
import { Button } from "../design/Button";

/** The running look's colorways, above its main knobs: a head line "colorways", as a knob's, then a chip each in
 * the look's order, wrapping onto more lines on a narrow column. A press sets every knob of that colorway at
 * once, in one frame, an edit as a knob's is, while the look's motion carries on. The active one, the first
 * whose every value its knob holds now, is pressed (aria-pressed, the selected fill); turning one of its knobs by
 * hand leaves none pressed. A look with no colorways shows no row. */
export function Colorways({ stack }: { stack: StackState }) {
  const sender = useSender();
  const labelId = useId();
  if (!stack.colorways.length) return null;
  return (
    <div className="param colorways">
      <div className="param-head">
        <span id={labelId} className="t-label">
          colorways
        </span>
      </div>
      <div className="colorway-chips" role="group" aria-labelledby={labelId}>
        {stack.colorways.map((name) => (
          <Button
            key={name}
            aria-pressed={name === stack.colorway}
            title={`set the look's ${name} colours`}
            onPress={() => sender.send({ type: "colorway", name })}
          >
            {name}
          </Button>
        ))}
      </div>
    </div>
  );
}
