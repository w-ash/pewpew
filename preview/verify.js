// Playwright drive-through of preview/index.html — the standing verification
// harness referenced by .claude/rules/preview-visual-verify.md.
//
//   cd preview && npm install && node verify.js
//   (first time: npx playwright install chromium)
//
// Checks: zero console/page errors; all five patterns lit AND animating
// (each card scrolled into view first — off-screen cards are deliberately
// culled and freeze); fire wind/height levers; comet slider extremes; pause;
// sdf3d spin; transport controls. Screenshots land in the OS tmpdir.
//
// Hard-won measurement rules (violating these makes the checks flaky):
// - Scroll a card into view before sampling it (culling blanks the canvas).
// - The fire wind check measures DIFFERENTIAL lean (top-half brightness
//   centroid minus bottom-half — the ignition base anchors out shared
//   noise), averaged over 6 snapshots, with gusts/tongues/embers OFF
//   (stochastic bright elements dominate centroids) and height 0.7
//   (0.85 can saturate the panel: no headroom, no visible lean).
// - The sdf3d spin check uses bright-cell-set symmetric difference net of
//   size change (beat-pulse breathing); y-row histograms are blind to it.
//
// page.evaluate below is Playwright's sandboxed in-page script execution
// against our own local file — not eval() of untrusted input. The page's
// top-level lexical bindings (players, etc.) are visible to evaluate.
const { chromium } = require('playwright');
const path = require('path');
const os = require('os');

const PAGE = 'file://' + path.resolve(__dirname, 'index.html');
const SHOTS = process.env.SHOTS_DIR || os.tmpdir();

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 960, height: 1000 } });
  const problems = [];
  page.on('console', m => { if (m.type() === 'error') problems.push('console.error: ' + m.text()); });
  page.on('pageerror', e => problems.push('pageerror: ' + e.message));

  await page.goto(PAGE);
  await page.waitForTimeout(2000);

  const sample = idx => page.evaluate(i => {
    const cv = document.querySelectorAll('canvas')[i];
    const d = cv.getContext('2d').getImageData(0, 0, cv.width, cv.height).data;
    let lit = 0, wsum = 0, xsum = 0;
    for (let p = 0; p < d.length; p += 4) {
      const b = d[p] + d[p + 1] + d[p + 2];
      if (b > 40) { lit++; const x = (p / 4) % cv.width; wsum += b; xsum += b * x; }
    }
    return { lit, cx: wsum ? xsum / wsum / cv.width : 0, total: d.length / 4 };
  }, idx);
  const setLever = (id, v) => page.evaluate(([id, v]) => {
    const el = document.getElementById(id);
    el.value = v; el.dispatchEvent(new Event('input'));
  }, [id, v]);

  const names = await page.$$eval('.card h2', els => els.map(e => e.firstChild.textContent));
  console.log('cards:', names.join(', '));

  // 1. lit + animating, per card, scrolled into view
  for (let i = 0; i < names.length; i++) {
    await page.evaluate(i => document.querySelectorAll('.card')[i].scrollIntoView({ block: 'center' }), i);
    await page.waitForTimeout(400);
    const before = await sample(i);
    await page.waitForTimeout(700);
    const after = await sample(i);
    const changed = Math.abs(after.lit - before.lit) > 2 || Math.abs(after.cx - before.cx) > 0.001;
    console.log(`${names[i]}: lit ${before.lit}->${after.lit} animating=${changed}`);
    if (before.lit === 0) problems.push(`${names[i]}: canvas dark`);
    if (!changed) problems.push(`${names[i]}: not animating`);
  }

  // 2. fire wind — differential lean, noise sources off
  const lean = () => page.evaluate(() => {
    const cv = document.querySelectorAll('canvas')[0];
    const d = cv.getContext('2d').getImageData(0, 0, cv.width, cv.height).data;
    let tw = 0, tx = 0, bw = 0, bx = 0;
    for (let p = 0; p < d.length; p += 4) {
      const b = d[p] + d[p + 1] + d[p + 2];
      if (b < 40) continue;
      const idx = p / 4, xc = (idx % cv.width) / cv.width, yc = (idx / cv.width | 0) / cv.height;
      if (yc < 0.5) { tw += b; tx += b * xc; } else { bw += b; bx += b * xc; }
    }
    return (tw ? tx / tw : 0.5) - (bw ? bx / bw : 0.5);
  });
  const meanLean = async () => {
    let s = 0;
    for (let j = 0; j < 6; j++) { s += await lean(); await page.waitForTimeout(150); }
    return s / 6;
  };
  await page.evaluate(() => document.querySelectorAll('.card')[0].scrollIntoView({ block: 'center' }));
  await page.waitForTimeout(500);
  await setLever('fire-gustiness', 0);
  await setLever('fire-tongues', 0);
  await setLever('fire-embers', 0);
  await setLever('fire-height', 0.7);
  await setLever('fire-wind', 1); await page.waitForTimeout(1500);
  const leanR = await meanLean();
  await setLever('fire-wind', -1); await page.waitForTimeout(1500);
  const leanL = await meanLean();
  console.log(`fire wind: lean right=${leanR.toFixed(3)} left=${leanL.toFixed(3)}`);
  if (!(leanR - leanL > 0.06)) problems.push('fire wind lever has no directional effect');
  await page.click('text=reset >> nth=0');

  // 3. fire height changes lit area
  await setLever('fire-height', 1); await page.waitForTimeout(1200);
  const tall = await sample(0);
  await setLever('fire-height', 0.05); await page.waitForTimeout(1200);
  const short = await sample(0);
  console.log(`fire height: lit tall=${tall.lit} short=${short.lit}`);
  if (!(tall.lit > short.lit * 1.3)) problems.push('fire height lever ineffective');
  await setLever('fire-height', 0.6);

  // 4. comet slider extremes stay renderable
  await setLever('comet-tail', 0.01); await setLever('comet-sparkle', 0);
  await page.waitForTimeout(600);
  if ((await sample(1)).lit === 0) problems.push('comet dark at tail=0.01');
  await page.click('text=reset >> nth=1');

  // 5. sdf3d spin — bright-set lateral motion, net of beat breathing
  const brightSet = () => page.evaluate(() => {
    const out = players[4].out, s = [];
    for (let i = 0; i < 1000; i++)
      if (Math.max(out[i * 3], out[i * 3 + 1], out[i * 3 + 2]) > 0.9) s.push(i);
    return s;
  });
  const motion = (a, b) => {
    const A = new Set(a), B = new Set(b);
    let sd = 0;
    for (const v of A) if (!B.has(v)) sd++;
    for (const v of B) if (!A.has(v)) sd++;
    return sd - Math.abs(a.length - b.length);
  };
  await setLever('sdf3d-spin', 1); await page.waitForTimeout(300);
  const s1 = await brightSet(); await page.waitForTimeout(900); const s2 = await brightSet();
  await setLever('sdf3d-spin', 0); await page.waitForTimeout(300);
  const z1 = await brightSet(); await page.waitForTimeout(900); const z2 = await brightSet();
  const mv1 = motion(s1, s2), mv0 = motion(z1, z2);
  console.log(`sdf3d spin: motion on=${mv1} off=${mv0}`);
  if (!(mv1 > mv0 + 10)) problems.push('sdf3d spin lever has no visible effect');
  await setLever('sdf3d-spin', 0.15);

  // 6. pause freezes fire
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.waitForTimeout(400);
  await page.click('#playpause');
  await page.waitForTimeout(300);
  const p1 = await sample(0);
  await page.waitForTimeout(500);
  const p2 = await sample(0);
  if (p1.lit !== p2.lit) problems.push('pause does not freeze fire');
  await page.click('#playpause');

  // 7. transport controls + screenshots
  await page.click('text=2×');
  await page.evaluate(() => { const el = document.getElementById('bpm'); el.value = 180; el.dispatchEvent(new Event('input')); });
  await page.waitForTimeout(400);
  await page.screenshot({ path: path.join(SHOTS, 'preview-top.png') });
  const cards = await page.$$('.card');
  await cards[0].screenshot({ path: path.join(SHOTS, 'preview-fire.png') });
  await cards[4].screenshot({ path: path.join(SHOTS, 'preview-sdf3d.png') });
  console.log('screenshots in', SHOTS);

  console.log(problems.length ? 'PROBLEMS:\n' + problems.join('\n') : 'ALL CHECKS PASSED');
  await browser.close();
  process.exit(problems.length ? 1 : 0);
})();
