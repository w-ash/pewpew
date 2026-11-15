import { useEffect } from "react";
import { expect, test } from "vitest";
import { render } from "vitest-browser-react";
import { useSlideGuard } from "../../src/design/useSlideGuard";

/** A stand-in for a slider: the guard's props on a box, and Zag's value change as a function it calls. */
let zag: (v: number) => void = () => undefined;
function Probe({ log }: { log: string[] }) {
  const guard = useSlideGuard(0.3, (v) => log.push(`change ${v}`), () => log.push("end"));
  useEffect(() => {
    zag = (v) => guard.onValueChange({ value: [v] });
  });
  return <div id="box" onPointerDownCapture={guard.onPointerDownCapture} />;
}

const fire = (type: string, target: EventTarget, x: number, y: number, pointerType = "touch") =>
  target.dispatchEvent(new PointerEvent(type, { bubbles: true, pointerId: 3, pointerType, clientX: x, clientY: y }));
const settle = () => new Promise((r) => setTimeout(r, 10));

async function gesture(moves: readonly (readonly [number, number])[], end: string, pointerType = "touch") {
  const log: string[] = [];
  const { unmount } = await render(<Probe log={log} />);
  const box = document.getElementById("box")!;
  fire("pointerdown", box, 100, 100, pointerType);
  for (const [dx, dy] of moves) {
    fire("pointermove", document, 100 + dx, 100 + dy, pointerType);
    zag(Math.round(300 + dx) / 1000);
  }
  fire(end, document, 100, 100, pointerType);
  await settle();
  await unmount();
  return log;
}

test("a touch that goes up or down moves nothing, whatever it drifts sideways, and a scroll after it leaves the value alone", async () => {
  const climb = Array.from({ length: 10 }, (_, i): readonly [number, number] => [i * 3, -(i + 1) * 15]);
  expect(await gesture(climb, "pointercancel")).toEqual([]);
  expect(await gesture(climb, "pointerup")).toEqual([]);
});

test("a touch that goes sideways moves the value, and a scroll after that puts it back", async () => {
  expect(await gesture([[8, 1], [30, 2]], "pointerup")).toEqual(["change 0.308", "change 0.33"]);
  expect(await gesture([[8, 1], [30, 2]], "pointercancel")).toEqual(["change 0.308", "change 0.33", "change 0.3", "end"]);
});

test("a mouse drag passes through, whichever way it goes", async () => {
  expect(await gesture([[0, -20]], "pointerup", "mouse")).toEqual(["change 0.3"]);
});
