// The canvas renderer. Colors arrive display-ready (the engine applies gamma
// and quantizes once), so nothing here applies a curve of its own.
import { inputMarker, type FixtureLine, type Layout } from "../../domain/room/layout";

const FILTERS = typeof CanvasRenderingContext2D !== "undefined" && "filter" in CanvasRenderingContext2D.prototype;

export interface Plan {
  readonly image: CanvasImageSource;
  /** Opacity, 0..1. */
  readonly dim: number;
}

export interface Scene {
  readonly layout: Layout;
  readonly rgb: Uint8Array | null;
  readonly plan: Plan | null;
  readonly markers: boolean;
  /** The fixture layout mode has picked, drawn as a band under its LEDs; null for none. */
  readonly picked?: FixtureLine | null;
  readonly dpr: number;
}

/** The colors the canvas draws in, as CSS colors. */
export interface Palette {
  readonly bg: string;
  readonly marker: string;
}

/** The offscreen layers a scene draws through and its palette, kept between frames. */
export interface Layers extends Palette {
  readonly dots: HTMLCanvasElement;
  readonly glow: HTMLCanvasElement;
}

export function newLayers(palette: Palette): Layers {
  return { ...palette, dots: document.createElement("canvas"), glow: document.createElement("canvas") };
}

export function drawScene(ctx: CanvasRenderingContext2D, layers: Layers, s: Scene): void {
  const { canvas } = ctx;
  const { layout } = s;
  ctx.fillStyle = layers.bg;
  ctx.fillRect(0, 0, canvas.width, canvas.height);
  if (layout.plan && s.plan && s.plan.dim > 0) {
    ctx.globalAlpha = s.plan.dim;
    ctx.drawImage(s.plan.image, layout.plan.x, layout.plan.y, layout.plan.w, layout.plan.h);
    ctx.globalAlpha = 1;
  }
  if (s.picked) {
    const f = s.picked;
    ctx.strokeStyle = layers.marker;
    ctx.globalAlpha = 0.45;
    ctx.lineWidth = 10 * s.dpr;
    ctx.lineCap = "round";
    ctx.beginPath();
    ctx.moveTo(f.ax, f.ay);
    ctx.lineTo(f.bx, f.by);
    ctx.stroke();
    ctx.globalAlpha = 1;
  }
  if (s.rgb && s.rgb.length >= layout.n * 3) drawDots(ctx, layers, layout, s.rgb);
  if (s.markers && layout.fixtures.length) {
    const size = 5 * s.dpr;
    ctx.fillStyle = layers.marker;
    ctx.globalAlpha = 0.9;
    ctx.beginPath();
    for (const f of layout.fixtures) {
      const [tip, left, right] = inputMarker(f, size);
      ctx.moveTo(...tip);
      ctx.lineTo(...left);
      ctx.lineTo(...right);
      ctx.closePath();
    }
    ctx.fill();
    ctx.globalAlpha = 1;
  }
}

// The dots go on their own layer. Where two overlap the brighter shows: dots
// drawn wider than their spacing (a map without a room) would otherwise sum
// to white. A black dot adds nothing, so it is skipped. The glow is that
// layer blurred, with the dots drawn over it: a dot shows its own color, and
// the glow lights only the dark around it. The result is added onto the
// room, as light is, in display space. One blur per frame, not one shadow per
// dot: a shadow under "lighter" composites through a layer of its own for
// every dot, which stalls on a 3,840-px canopy. Without canvas filters (older
// Safari) the page adds the dots alone.
function drawDots(ctx: CanvasRenderingContext2D, { dots, glow }: Layers, layout: Layout, rgb: Uint8Array): void {
  fit(dots, ctx.canvas);
  const d = dots.getContext("2d");
  if (!d) return;
  d.globalCompositeOperation = "source-over";
  d.clearRect(0, 0, dots.width, dots.height);
  d.globalCompositeOperation = "lighten";
  for (let i = 0; i < layout.n; i++) {
    const r = rgb[3 * i]!, g = rgb[3 * i + 1]!, b = rgb[3 * i + 2]!;
    if (!(r | g | b)) continue;
    d.fillStyle = `rgb(${r},${g},${b})`;
    if (layout.bar) {
      d.fillRect(layout.px[i]! - layout.bar.w / 2, layout.py[i]! - layout.bar.h / 2, layout.bar.w, layout.bar.h);
      continue;
    }
    d.beginPath();
    d.arc(layout.px[i]!, layout.py[i]!, layout.radii[i]!, 0, 2 * Math.PI);
    d.fill();
  }
  const gl = FILTERS ? fit(glow, ctx.canvas).getContext("2d") : null;
  if (gl) {
    gl.clearRect(0, 0, glow.width, glow.height);
    gl.filter = `blur(${layout.glow}px)`;
    gl.drawImage(dots, 0, 0);
    gl.filter = "none";
    gl.drawImage(dots, 0, 0);
  }
  ctx.globalCompositeOperation = "lighter";
  ctx.drawImage(gl ? glow : dots, 0, 0);
  ctx.globalCompositeOperation = "source-over";
}

/** `layer`, sized to `canvas`; resizing clears it, so only on a change. */
function fit(layer: HTMLCanvasElement, canvas: HTMLCanvasElement): HTMLCanvasElement {
  if (layer.width !== canvas.width || layer.height !== canvas.height) {
    layer.width = canvas.width;
    layer.height = canvas.height;
  }
  return layer;
}
