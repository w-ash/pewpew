// A touch on a slider's thumb is a scroll until it goes sideways. The page's own rule is that only a
// sideways drag moves a slider; Zag moves the value on the first pointermove, before the browser has taken
// the gesture as a scroll (pointercancel), so the guard holds the value back until the movement is sideways.
import { useEffect, useRef } from "react";
import type { PointerEvent } from "react";

/** How far a touch must go sideways, and further than it went up or down, to be a drag. */
const SLIDE_PX = 4;

interface Touch {
  readonly id: number;
  readonly from: number;
  readonly x: number;
  readonly y: number;
  slid: boolean;
}

/** The props a `Slider.Root` of one value takes so that a touch moves it only when it goes sideways. A
 * scroll (pointercancel) after the thumb moved puts the value back where the touch found it. A mouse or a
 * pen passes through unchanged. */
export function useSlideGuard(value: number, onChange: (v: number) => void, onEnd: () => void) {
  const now = useRef({ value, onChange, onEnd });
  useEffect(() => {
    now.current = { value, onChange, onEnd };
  });
  const touch = useRef<Touch | null>(null);
  const stop = useRef<(() => void) | null>(null);
  const start = (e: PointerEvent) => {
    stop.current?.();
    if (e.pointerType !== "touch") return;
    const t: Touch = { id: e.pointerId, from: now.current.value, x: e.clientX, y: e.clientY, slid: false };
    touch.current = t;
    const move = (m: globalThis.PointerEvent) => {
      if (m.pointerId !== t.id || t.slid) return;
      const dx = Math.abs(m.clientX - t.x);
      t.slid = dx >= SLIDE_PX && dx > Math.abs(m.clientY - t.y);
    };
    const leave = (u: globalThis.PointerEvent) => {
      if (u.pointerId !== t.id) return;
      if (u.type === "pointercancel" && t.slid) {
        now.current.onChange(t.from);
        now.current.onEnd();
      }
      // After Zag's own pointerup handler, which reports the end.
      setTimeout(() => stop.current?.(), 0);
    };
    window.addEventListener("pointermove", move, true);
    window.addEventListener("pointerup", leave);
    window.addEventListener("pointercancel", leave);
    stop.current = () => {
      window.removeEventListener("pointermove", move, true);
      window.removeEventListener("pointerup", leave);
      window.removeEventListener("pointercancel", leave);
      if (touch.current === t) touch.current = null;
      stop.current = null;
    };
  };
  const held = () => touch.current !== null && !touch.current.slid;
  return {
    value: [value],
    onPointerDownCapture: start,
    onValueChange: (d: { value: number[] }) => {
      if (!held()) onChange(d.value[0] ?? value);
    },
    onValueChangeEnd: () => {
      if (!held()) onEnd();
    },
  };
}
