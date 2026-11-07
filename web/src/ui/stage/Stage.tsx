import { useCallback, useEffect, useRef, useState } from "react";
import { makeLayout, nearestFixture, type Viewport } from "../../domain/room/layout";
import { useWire, useWireContext } from "../../infra/wire/store";
import { FINE_POINTER, useMedia } from "../common/useMedia";
import { useLayoutMode } from "../layout/LayoutMode";
import { drawScene, newLayers } from "./draw";
import type { PlanImage } from "./plan";
import { PlanDimmer } from "./PlanDimmer";

/** The room as the LEDs show it, fitted under the `cover` CSS px a banner lies over at its top. Frames
 * draw straight onto the canvas, outside React. In layout mode
 * a click on a bar blinks it; a tap picks it first, drawn on the stage, and blinks it on a second tap,
 * as bars on a phone lie closer than a finger is wide. */
export function Stage({ plan, cover }: { plan: PlanImage; cover: number }) {
  const { store } = useWireContext();
  const mode = useLayoutMode();
  const fine = useMedia(FINE_POINTER);
  const map = useWire((s) => s.map);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  // The page's own colors, from theme.css: the canvas lies on the page's ground, and the layout marks are
  // neutral, as amber is for what the room is shown.
  const [layers] = useState(() => {
    const css = getComputedStyle(document.documentElement);
    return newLayers({ bg: css.getPropertyValue("--surface-page"), marker: css.getPropertyValue("--text-1") });
  });
  const [view, setView] = useState<Viewport>({ width: 0, height: 0, dpr: 1 });
  const [dim, setDim] = useState(0.25);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const measure = () => {
      const dpr = devicePixelRatio;
      const width = Math.round(canvas.clientWidth * dpr), height = Math.round(canvas.clientHeight * dpr);
      canvas.width = width;
      canvas.height = height;
      setView({ width, height, dpr });
    };
    const ro = new ResizeObserver(measure);
    ro.observe(canvas);
    return () => ro.disconnect();
  }, []);

  const layout = map && view.width ? makeLayout(map, view, plan.size, cover * view.dpr) : null;
  const markers = mode.on && mode.markers;
  const picked = (mode.on && layout?.fixtures.find((f) => f.id === mode.fixture)) || null;

  useEffect(() => {
    const ctx = canvasRef.current?.getContext("2d");
    if (!ctx || !layout) return;
    const scene = { layout, plan: plan.image && { image: plan.image, dim }, markers, picked, dpr: view.dpr };
    const draw = () => drawScene(ctx, layers, { ...scene, rgb: store.getFrame()?.rgb ?? null });
    draw();
    // At most one draw per animation frame: a burst after a stall draws once,
    // and a hidden tab draws nothing.
    let queued = 0;
    const unsubscribe = store.subscribeFrame(() => {
      if (queued) return;
      queued = requestAnimationFrame(() => {
        queued = 0;
        draw();
      });
    });
    return () => {
      unsubscribe();
      cancelAnimationFrame(queued);
    };
  }, [store, layers, layout, plan.image, dim, markers, picked, view.dpr]);

  return (
    <div className="stage">
      <canvas
        ref={canvasRef}
        role="img"
        aria-label="preview of the LEDs"
        data-layout={mode.on || undefined}
        onClick={(ev) => {
          if (!mode.on || !layout) return;
          const f = nearestFixture(layout, ev.nativeEvent.offsetX * view.dpr, ev.nativeEvent.offsetY * view.dpr, view.dpr);
          if (!f) return;
          if (fine || f.id === mode.fixture) mode.blink(f.id);
          else mode.setFixture(f.id);
        }}
      />
      {plan.image && <PlanDimmer value={dim} onChange={setDim} />}
    </div>
  );
}

/** What lies over the stage's top (the status bar, the lost banner): a callback ref that measures each,
 * and the tallest one's height in CSS px, 0 while none shows. */
export function useCover(): [measure: (el: HTMLElement | null) => (() => void) | undefined, height: number] {
  const [heights] = useState(() => new Map<HTMLElement, number>());
  const [height, setHeight] = useState(0);
  const measure = useCallback(
    (el: HTMLElement | null) => {
      if (!el) return;
      const tallest = () => setHeight(Math.max(0, ...heights.values()));
      const watch = new ResizeObserver(() => {
        heights.set(el, el.offsetHeight);
        tallest();
      });
      watch.observe(el);
      return () => {
        watch.disconnect();
        heights.delete(el);
        tallest();
      };
    },
    [heights],
  );
  return [measure, height];
}
