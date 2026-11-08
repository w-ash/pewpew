// Where each pixel lands on the canvas, in device pixels.
//
// 2D maps draw their bounding box as large as fits, one scale for both axes
// (y=0 at the bottom). 3D maps draw their z-slices side by side, ascending z
// left to right, the same reading as the ANSI sink. A room map draws true to
// life: one scale for meters and the plan image, each dot sized from its
// fixture's real pitch.

export type Vec = readonly number[];

export interface RoomFixture {
  readonly id: string;
  /** Meters, centre to centre. */
  readonly pitch: number;
  /** The strip's ends, normalized (x, y). */
  readonly start: Vec;
  readonly end: Vec;
  /** The end where data enters. */
  readonly input: "start" | "end";
}

export type RoomPlan =
  /** `corner` is the image's top-left, normalized; `unit` is normalized units per image pixel. */
  | { readonly corner: Vec; readonly unit: number; readonly url: string }
  /** The room names an image the engine cannot find. */
  | { readonly error: string };

export interface RoomShape {
  /** Normalized units per meter. */
  readonly scale: number;
  /** In wire order. */
  readonly fixtures: readonly RoomFixture[];
  /** The fixture index of each pixel sent. */
  readonly fixture_of: readonly number[];
  /** Null without a floor plan. */
  readonly plan: RoomPlan | null;
}

/** The positions the engine sends in `hello` and `layout`. */
export interface MapShape {
  /** The pixels sent: a map past the engine's budget is decimated evenly. */
  readonly n: number;
  /** The map's own size. */
  readonly total: number;
  readonly positions: readonly Vec[];
  readonly is3d: boolean;
  /** Null unless the map is an arrangement or room file (`run --map`). */
  readonly room: RoomShape | null;
}

export interface Viewport {
  readonly width: number;
  readonly height: number;
  readonly dpr: number;
}

export interface Size {
  readonly width: number;
  readonly height: number;
}

export interface Rect {
  readonly x: number;
  readonly y: number;
  readonly w: number;
  readonly h: number;
}

/** A fixture's strip in device pixels, from its start (ax, ay) to its end (bx, by). */
export interface FixtureLine {
  readonly id: string;
  readonly ax: number;
  readonly ay: number;
  readonly bx: number;
  readonly by: number;
  readonly input: "start" | "end";
}

export interface Layout {
  readonly n: number;
  readonly px: Float32Array;
  readonly py: Float32Array;
  readonly radii: Float32Array;
  /** On a strip, each dot is a bar this tall, as wide as its pitch, in device pixels; else null. */
  readonly bar?: { readonly w: number; readonly h: number } | null;
  /** The glow's blur (a Gaussian sigma), in device pixels. */
  readonly glow: number;
  readonly fixtures: readonly FixtureLine[];
  readonly plan: Rect | null;
}

/** A dot's diameter, as a fraction of its fixture's pitch; the gap between neighbours is left to the glow. */
export const DOT = 0.7;
/** The glow's blur per dot radius. */
const GLOW = 1.1;
/** A room's smallest dot radius, in css px: a far fixture still reads as a line of light. */
export const DOT_MIN = 1.5;
/** A room's glow per gap to a fixture's nearest neighbour, and at most, in css px: it lights the
 * dark between fixtures, so each bar reads as a bar of light, and stops short of the next. */
export const GLOW_GAP = 0.25;
export const GLOW_MAX = 8;
/** A strip's bar height, as a fraction of the stage's: 1 / STRIP_BAR. */
const STRIP_BAR = 12;

const coord = (p: Vec | undefined, i: number) => p?.[i] ?? 0;

/** The room of a flat room map, else null: a 3D map draws as slices, not a room. */
export function roomOf(map: MapShape | null): RoomShape | null {
  return map && !map.is3d ? map.room : null;
}

export function planUrl(room: RoomShape | null): string | null {
  return room?.plan && "url" in room.plan ? room.plan.url : null;
}

/** Why the server cannot send the room's plan image, or null. */
export function planError(room: RoomShape | null): string | null {
  return room?.plan && "error" in room.plan ? room.plan.error : null;
}

/** The room's margin in `view`, in device px: 30 CSS px, or a tenth of its shorter side on a small
 * stage, so the room keeps its share. */
export function padOf(view: Viewport): number {
  return Math.min(30 * view.dpr, 0.1 * Math.min(view.width, view.height));
}

function inner(view: Viewport) {
  const pad = padOf(view);
  return { pad, w: view.width - 2 * pad, hgt: view.height - 2 * pad };
}

/** The layout for `shape` on `view`. `plan` is the loaded plan image's size,
 * or null while it is not loaded. `cover` device px at the view's top lie
 * under a banner: the layout fits in the rest, so the whole room shows. */
export function makeLayout(shape: MapShape, view: Viewport, plan: Size | null, cover = 0): Layout {
  if (cover <= 0) return fitLayout(shape, view, plan);
  const l = fitLayout(shape, { ...view, height: Math.max(view.height - cover, 1) }, plan);
  return {
    ...l,
    py: l.py.map((y) => y + cover),
    fixtures: l.fixtures.map((f) => ({ ...f, ay: f.ay + cover, by: f.by + cover })),
    plan: l.plan && { ...l.plan, y: l.plan.y + cover },
  };
}

function fitLayout(shape: MapShape, view: Viewport, plan: Size | null): Layout {
  const room = roomOf(shape);
  if (room) return roomLayout(shape, room, view, plan);
  const { n, positions: pos } = shape;
  const sliceOf = new Int32Array(n);
  let slices = 1;
  if (shape.is3d) {
    const zs = [...new Set(pos.map((p) => Math.round(coord(p, 2) * 100)))].sort((a, b) => a - b);
    slices = zs.length;
    const zi = new Map(zs.map((z, i) => [z, i]));
    for (let i = 0; i < n; i++) sliceOf[i] = zi.get(Math.round(coord(pos[i], 2) * 100)) ?? 0;
  }
  const gutter = 0.15; // in slice widths
  const totalW = slices + gutter * (slices - 1);
  const { pad, w, hgt } = inner(view);
  const px = new Float32Array(n), py = new Float32Array(n);

  // A degenerate y axis (a 1D strip) spans the full width, centered
  // vertically: each dot a bar as wide as its pitch and a twelfth of the
  // stage tall, so a long strip reads as a band of light, not a thread.
  const ys = pos.map((p) => coord(p, 1));
  if (!shape.is3d && Math.max(...ys) - Math.min(...ys) < 1e-6) {
    for (let i = 0; i < n; i++) {
      px[i] = pad + coord(pos[i], 0) * w;
      py[i] = view.height / 2;
    }
    const radius = Math.max(2, (w / n) * 0.6);
    const pitch = w / Math.max(n - 1, 1);
    const bar = { w: Math.max(pitch * 0.9, 1), h: Math.max(2 * radius, view.height / STRIP_BAR) };
    const glow = Math.min(GLOW * radius + bar.h / 8, GLOW_MAX * view.dpr);
    return { n, px, py, radii: new Float32Array(n).fill(radius), bar, glow, fixtures: [], plan: null };
  }

  // The box drawn: 0-1 per slice in 3D, the positions' own extent in 2D.
  let minX = 0, minY = 0, spanX = 1, spanY = 1;
  if (!shape.is3d) {
    const xs = pos.map((p) => coord(p, 0));
    minX = Math.min(...xs);
    spanX = Math.max(...xs) - minX || 1;
    minY = Math.min(...ys);
    spanY = Math.max(...ys) - minY;
  }
  const scale = shape.is3d ? Math.min(w / totalW, hgt) : Math.min(w / spanX, hgt / spanY);
  const x0 = (view.width - (shape.is3d ? totalW : spanX) * scale) / 2;
  const y0 = (view.height - spanY * scale) / 2;
  for (let i = 0; i < n; i++) {
    const off = (sliceOf[i] ?? 0) * (1 + gutter);
    px[i] = x0 + (off + coord(pos[i], 0) - minX) * scale;
    py[i] = y0 + (spanY - (coord(pos[i], 1) - minY)) * scale;
  }
  // Dot size from typical spacing: assume roughly square slices.
  const radius = Math.max(2, (scale / Math.max(4, Math.sqrt(n / slices))) * 0.42);
  return { n, px, py, radii: new Float32Array(n).fill(radius), glow: GLOW * radius, fixtures: [], plan: null };
}

function roomLayout(shape: MapShape, room: RoomShape, view: Viewport, planSize: Size | null): Layout {
  const { n, positions: pos } = shape;
  let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
  for (const p of pos) {
    minX = Math.min(minX, coord(p, 0));
    maxX = Math.max(maxX, coord(p, 0));
    minY = Math.min(minY, coord(p, 1));
    maxY = Math.max(maxY, coord(p, 1));
  }
  let plan: Rect | null = null;
  if (planSize && room.plan && "url" in room.plan) {
    const [cx = 0, cy = 0] = room.plan.corner;
    const u = room.plan.unit;
    plan = { x: cx, y: cy, w: planSize.width * u, h: planSize.height * u };
    minX = Math.min(minX, plan.x);
    maxX = Math.max(maxX, plan.x + plan.w);
    minY = Math.min(minY, plan.y - plan.h);
    maxY = Math.max(maxY, plan.y);
  }
  const { w, hgt } = inner(view);
  const spanX = maxX - minX || 1, spanY = maxY - minY;
  const scale = Math.max(0, Math.min(w / spanX, spanY > 0 ? hgt / spanY : Infinity));
  const x0 = (view.width - spanX * scale) / 2, y0 = (view.height - spanY * scale) / 2;
  const sx = (x: number) => x0 + (x - minX) * scale;
  const sy = (y: number) => y0 + (maxY - y) * scale; // y=0 at the bottom
  const px = new Float32Array(n), py = new Float32Array(n), radii = new Float32Array(n);
  const perMeter = scale * room.scale; // device px per meter
  const floor = DOT_MIN * view.dpr; // still a line of light when far away
  for (let i = 0; i < n; i++) {
    px[i] = sx(coord(pos[i], 0));
    py[i] = sy(coord(pos[i], 1));
    const f = room.fixtures[room.fixture_of[i] ?? 0];
    radii[i] = Math.max(floor, 0.5 * DOT * (f?.pitch ?? 0) * perMeter);
  }
  const fixtures = room.fixtures.map((f) => ({
    id: f.id, ax: sx(coord(f.start, 0)), ay: sy(coord(f.start, 1)), bx: sx(coord(f.end, 0)), by: sy(coord(f.end, 1)), input: f.input,
  }));
  const rect = plan && { x: sx(plan.x), y: sy(plan.y), w: plan.w * scale, h: plan.h * scale };
  // One blur for the room: the median dot's, or more, from the median gap to a nearest fixture.
  const sorted = Float32Array.from(radii).sort();
  const own = GLOW * (n ? (sorted[n >> 1] ?? 1) : 1);
  const gap = medianGap(fixtures);
  const glow = gap === null ? own : Math.max(own, Math.min(GLOW_GAP * gap, GLOW_MAX * view.dpr));
  return { n, px, py, radii, glow, fixtures, plan: rect };
}

/** The median, over `fixtures`, of the distance from each to its nearest other, or null for
 * fewer than two. Segments that do not cross are nearest at an end of one of them. */
function medianGap(fixtures: readonly FixtureLine[]): number | null {
  if (fixtures.length < 2) return null;
  const ends = (f: FixtureLine) => [[f.ax, f.ay], [f.bx, f.by]] as const;
  const near = fixtures.map((f) => {
    let best = Infinity;
    for (const g of fixtures) {
      if (g === f) continue;
      for (const [x, y] of ends(f)) best = Math.min(best, segmentDistance(x, y, g));
      for (const [x, y] of ends(g)) best = Math.min(best, segmentDistance(x, y, f));
    }
    return best;
  }).sort((a, b) => a - b);
  return near[near.length >> 1] ?? null;
}

function segmentDistance(x: number, y: number, f: FixtureLine): number {
  const dx = f.bx - f.ax, dy = f.by - f.ay, len2 = dx * dx + dy * dy;
  const k = len2 ? Math.max(0, Math.min(1, ((x - f.ax) * dx + (y - f.ay) * dy) / len2)) : 0;
  return Math.hypot(x - (f.ax + k * dx), y - (f.ay + k * dy));
}

/** The fixture within 16 CSS px of device point (x, y), nearest first, or null. */
export function nearestFixture(layout: Layout, x: number, y: number, dpr: number): FixtureLine | null {
  let best: FixtureLine | null = null, bestD = 16 * dpr;
  for (const f of layout.fixtures) {
    const d = segmentDistance(x, y, f);
    if (d < bestD) {
      best = f;
      bestD = d;
    }
  }
  return best;
}

type Pt = readonly [number, number];

/** The arrowhead at a fixture's input end, pointing the way data runs: tip
 * one marker-length inside the strip, base across the input end. */
export function inputMarker(f: FixtureLine, size: number): readonly [Pt, Pt, Pt] {
  const start = f.input === "start";
  const x = start ? f.ax : f.bx, y = start ? f.ay : f.by;
  let dx = (start ? f.bx : f.ax) - x, dy = (start ? f.by : f.ay) - y;
  const len = Math.hypot(dx, dy) || 1;
  dx /= len;
  dy /= len;
  return [
    [x + dx * size * 1.6, y + dy * size * 1.6],
    [x - dy * size, y + dx * size],
    [x + dy * size, y - dx * size],
  ];
}
