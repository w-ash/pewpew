// FireSim — reference implementation for the backlog story
// "Port the upgraded fire to Python" (docs/backlog/unscheduled.md).
//
// Extracted verbatim (plus the three helpers it uses) from
// preview/index.html @ 519eb6d1418cf45a2840deb2b4708c6cd884f2b9 when the
// playground was retired in favor of the engine-backed preview sink
// (`python -m pewpew run <pattern> --preview`). This is NOT a port of
// bench/authoring/fire.py — it is an original upgrade: PSX-Doom
// randomized advection + wind/gusts, scrolling-noise cooling, wandering
// hot-spot tongues, and an additive ember layer. The Python port story
// must translate it onto the ADR-005 contract (seeded RNG in
// before_render, heat as a `self.buffer`, dt-based decay via the kit).
//
// The `Fire.render` palette maps heat -> R, then G, then B with a cap
// below white so only embers go white; the ember layer itself lived in
// the playground's renderer (additive sprite stamps, see the same commit)
// and is part of the look, not of this sim.

'use strict';

const TWO_PI = Math.PI * 2;
const clamp = (v, lo, hi) => v < lo ? lo : v > hi ? hi : v;

function mulberry32(seed) {
  let a = seed >>> 0;
  return function () {
    a |= 0; a = (a + 0x6D2B79F5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

// tileable 2-octave value noise, precomputed once (29a.ch trick)
function makeNoise(size, seed) {
  const r = mulberry32(seed);
  const base = new Float32Array(size * size);
  for (let i = 0; i < base.length; i++) base[i] = r();
  function raw(x, y) {
    const xi = Math.floor(x), yi = Math.floor(y);
    const fx = x - xi, fy = y - yi;
    const x0 = ((xi % size) + size) % size, y0 = ((yi % size) + size) % size;
    const x1 = (x0 + 1) % size, y1 = (y0 + 1) % size;
    const sx = fx * fx * (3 - 2 * fx), sy = fy * fy * (3 - 2 * fy);
    const a = base[y0 * size + x0], b = base[y0 * size + x1];
    const c = base[y1 * size + x0], d = base[y1 * size + x1];
    return a + (b - a) * sx + (c - a) * sy + (a - b - c + d) * sx * sy;
  }
  return (x, y) => 0.65 * raw(x, y) + 0.35 * raw(x * 2.7, y * 2.7);
}

// ------------------------------------------------------------ FireSim
// Upgraded fire: PSX-Doom randomized advection + wind/gusts, scrolling
// noise cooling, wandering hot-spot tongues, and an additive ember layer.
class FireSim {
  constructor(W, H) {
    this.W = W; this.H = H;
    this.heat = new Float32Array(W * H);   // row 0 = bottom
    this.buf = new Float32Array(W * H);
    this.noise = makeNoise(64, 1337);
    this.spots = [];
    this.embers = [];
    this.windNow = 0; this.gust = 0; this.gustTimer = 0;
    this.advTimer = 0; this.t = 0;
  }
  step(dt, p) {
    this.t += dt;
    // wind: lever bias + gusts (random walk toward a gust target)
    this.gustTimer -= dt;
    if (this.gustTimer <= 0) {
      this.gust = (Math.random() * 2 - 1) * 1.6 * p.gustiness;
      this.gustTimer = 0.4 + Math.random() * 1.8;
    }
    this.windNow += ((p.wind * 1.4 + this.gust) - this.windNow) * Math.min(1, dt * 3);

    // fixed-rate advection steps so speed x0.5 slows the flame properly
    this.advTimer += dt * 60;
    let steps = Math.min(3, this.advTimer | 0);
    this.advTimer -= steps;
    while (steps-- > 0) this.advect(p);

    // embers ride real time
    this.stepEmbers(dt, p);
  }
  advect(p) {
    const { W, H, heat, buf, noise } = this;
    // 1. cooling: base + scrolling coherent noise (turbulence lever)
    const coolBase = 0.006 + (1 - p.height) * 0.022;
    const coolAmp = p.turbulence * 0.045;
    const scroll = this.t * 14;
    for (let r = 0; r < H; r++) for (let c = 0; c < W; c++) {
      const i = r * W + c;
      const cool = coolBase + coolAmp * noise(c * 0.22, (r + scroll) * 0.16);
      heat[i] = Math.max(0, heat[i] - cool);
    }
    // 2. ignition: wandering pulsing hot spots (tongues) + spark floor
    const want = Math.round(p.tongues);
    while (this.spots.length < want)
      this.spots.push({ x: Math.random() * W, ph: Math.random() * TWO_PI });
    this.spots.length = want;
    for (const s of this.spots) {
      s.x = (s.x + (Math.random() - 0.5) * 0.6 + this.windNow * 0.15 + W) % W;
      s.ph += 0.06 + Math.random() * 0.05;
      const amp = 0.8 + 0.2 * Math.sin(s.ph);
      for (let dx = -3; dx <= 3; dx++) {
        const cx = ((s.x + dx + W) | 0) % W;
        const g = amp * Math.exp(-(dx * dx) / 4.5);
        heat[cx] = Math.max(heat[cx], g);
        heat[W + cx] = Math.max(heat[W + cx], g * 0.85);
      }
    }
    for (let c = 0; c < W; c++) if (Math.random() < 0.12) heat[c] = Math.max(heat[c], 0.45 + Math.random() * 0.3);
    // 3. Doom-style throw-up: random +-1 offset + wind bias, random 0-or-N decay
    buf.set(heat);
    const decayStep = 0.02 + (1 - p.height) * 0.075;
    const wInt = Math.floor(this.windNow), wFrac = this.windNow - wInt;
    for (let r = 1; r < H; r++) {
      const src = (r - 1) * W, dst = r * W;
      for (let c = 0; c < W; c++) {
        const off = ((Math.random() * 3) | 0) - 1 + wInt + (Math.random() < wFrac ? 1 : 0);
        const dc = c + off;
        if (dc < 0 || dc >= W) continue;   // wind carries heat off the panel edge
        const dec = Math.random() < 0.5 ? 0 : decayStep * (0.5 + Math.random());
        buf[dst + dc] = Math.max(0, heat[src + c] - dec);
      }
    }
    this.heat = buf; this.buf = heat;   // swap buffers
  }
  stepEmbers(dt, p) {
    const { W, H, heat } = this;
    // spawn from hot lower cells
    const rate = p.embers * 26;  // embers/second at lever=1
    if (Math.random() < rate * dt) {
      const c = Math.random() * W;
      const base = heat[(1 * W + c) | 0] || 0;
      if (base > 0.5) this.embers.push({
        x: c, y: 1.5 + Math.random() * 2,
        vx: (Math.random() - 0.5) * 2, vy: 6 + Math.random() * 8,
        life: 0, max: 0.6 + Math.random() * 1.2, wob: Math.random() * 100,
      });
    }
    const alive = [];
    for (const e of this.embers) {
      e.life += dt;
      e.vy = Math.min(e.vy + 10 * dt, 26);                          // buoyancy
      e.vx += (this.windNow * 2.2 - e.vx) * dt * 1.5
            + (this.noise(e.wob, e.life * 2) - 0.5) * 30 * dt;      // wobble
      e.x += e.vx * dt;
      e.y += e.vy * dt;
      if (e.life < e.max && e.y < H + 2 && e.x > -1 && e.x < W + 1 && alive.length < 90) alive.push(e);
    }
    this.embers = alive;
  }
}

class Fire {
  static id = 'fire';
  static params = [
    { k: 'height',     v: 0.6,  lo: 0.05, hi: 1, step: 0.01, label: 'height' },
    { k: 'tongues',    v: 3,    lo: 0,    hi: 6, step: 1,    label: 'tongues' },
    { k: 'wind',       v: 0,    lo: -1,   hi: 1, step: 0.01, label: 'wind' },
    { k: 'gustiness',  v: 0.3,  lo: 0,    hi: 1, step: 0.01, label: 'gusts' },
    { k: 'turbulence', v: 0.5,  lo: 0,    hi: 1, step: 0.01, label: 'turb' },
    { k: 'embers',     v: 0.35, lo: 0,    hi: 1, step: 0.01, label: 'embers' },
  ];
  constructor(W, H) { this.sim = new FireSim(W, H); }
  beforeRender(dt) { this.sim.step(dt, this); }
  render(fix, out) {
    const heat = this.sim.heat, n = fix.n;
    for (let i = 0; i < n; i++) {
      const h = Math.min(heat[i], 0.78) * 3;   // cap below white: only embers go white
      out[i * 3] = clamp(h, 0, 1);
      out[i * 3 + 1] = clamp(h - 1, 0, 1) * 0.85;
      out[i * 3 + 2] = clamp(h - 2, 0, 1) * 0.55;
    }
  }
}
