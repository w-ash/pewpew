import { describe, expect, test } from "vitest";
import {
  bannerText, chip, frameGap, healthRows, mac, okHint, rebindOffers, scanNote, STALE_MS, uptime,
  type FoundBoard,
} from "../../src/domain/health/health";
import { board, health } from "../fixtures/messages";

test("frames go stale after STALE_MS, and none yet is not stale", () => {
  expect(frameGap(10_000, 10_000 - STALE_MS)).toBe(0);
  expect(frameGap(10_000, 10_000 - STALE_MS - 1)).toBeCloseTo(2.001);
  expect(frameGap(10_000, 0)).toBe(0);
});

test("uptime and MAC", () => {
  expect(uptime(59)).toBe("up 0m");
  expect(uptime(3700)).toBe("up 1h 1m");
  expect(uptime(90000)).toBe("up 1d 1h");
  expect(uptime(null)).toBeNull();
  expect(mac("aabbccddeeff")).toBe("aa:bb:cc:dd:ee:ff");
});

describe("chip", () => {
  test("counts boards by their worst level", () => {
    expect(chip(health([board({}), board({ host: "b" })]), 0).text).toBe("2 ok");
    expect(chip(health([board({ level: "warn" })], { level: "warn" }), 0).text).toBe("1 warn");
    expect(chip(health([board({ level: "bad" }), board({ level: "warn" })], { level: "bad" }), 0).text).toBe("1 bad");
    expect(chip(health([], { level: "pending" }), 0).text).toBe("…");
  });
  test("stale frames make it bad", () => {
    expect(chip(health([board({})]), 3)).toEqual({ level: "bad", text: "no frames here", label: "aura health: no frames reaching this page" });
  });
  test("a layer whose render raises makes it bad", () => {
    expect(chip(health([board({})]), 0, true)).toEqual({ level: "bad", text: "error", label: "aura health: a layer's render fails" });
  });
});

test("rows: boards, then the render loop and sleep", () => {
  const rows = healthRows(health([board({ reboots: 2, reset_reason: 4 })]), 0, { t: 488.7, n: 3840, total: 3840 });
  expect(rows.map((r) => r.name)).toEqual(["A · 192.168.1.50", "rendering", "laptop can sleep"]);
  expect(rows[0]!.facts).toBe(
    "MAC aa:bb:cc:dd:ee:ff · live · 40/40 fps · -55 dBm ch 6 · up 1h 1m · rebooted 2× (reason 4) · heap 120k · 320/320 px · 16.0.1",
  );
  expect(rows[0]!.link).toBe("http://192.168.1.50/");
  expect(rows[1]).toMatchObject({ facts: "t=488 s · 3840 px · 60/60 fps · 0 skips · watchdog off", level: "ok" });
  expect(rows[2]).toMatchObject({ name: "laptop can sleep", level: "off", facts: "this run did not ask to keep it awake" });
  // On the laptop itself, the flag that asks.
  expect(healthRows(health([]), 0, null, true)[1]!.facts).toBe("this run did not ask to keep it awake (start it with --keep-awake)");
  expect(healthRows(health([]), 5, null)[0]).toMatchObject({ level: "bad", reasons: ["no frames reaching this page for 5 s"] });
});

test("while a layer's render fails, the render loop row is bad and says which, as the chip does", () => {
  const loop = healthRows(health([]), 0, null, false, "base · boomer failed").find((r) => r.key === "loop")!;
  expect(loop).toMatchObject({ level: "bad", reasons: ["base · boomer failed"], fix: null });
  expect(healthRows(health([]), 0, null).find((r) => r.key === "loop")!.reasons).toEqual([]);
});

test("the render loop and sleep rows carry the engine's fix, and a page cut off from frames drops the loop's", () => {
  const h = health([], {
    loop: { level: "warn", fps: 40, target: 60, skips: 9, watchdog: null, fix: "Check the laptop is on AC." },
    awake: { level: "warn", requested: true, held: false, detail: "caffeinate exited", fix: "Restart the aura." },
  });
  expect(healthRows(h, 0, null).map((r) => r.fix)).toEqual(["Check the laptop is on AC.", "Restart the aura."]);
  expect(healthRows(h, 5, null)[0]!.fix).toBeNull();
});

test("a healthy board's fix shows once for all of them, a sick board's on its row", () => {
  const dark = "If the bars stay dark, check the LED supply.";
  const h = health([board({ fix: dark }), board({ host: "b", fix: dark }), board({ host: "c", level: "warn", fix: "Move it." })]);
  expect(healthRows(h, 0, null).map((r) => r.fix)).toEqual([null, null, "Move it.", null, null]);
  expect(okHint(h)).toBe(dark);
  expect(okHint(health([board({ level: "bad", fix: "x" })]))).toBeNull();
});

test("banner names one bad board, or counts several", () => {
  expect(bannerText([])).toBe("");
  expect(bannerText([board({ level: "bad", reasons: ["not live"] })])).toBe("Board A: not live. Tap for the fix.");
  expect(bannerText([board({ level: "bad" }), board({ board: null, host: "h" })])).toBe(
    "2 boards need attention: A, h. Tap for details.",
  );
});

test("scan note", () => {
  expect(scanNote(null)).toBe("lists the WLED boards on this laptop's network");
  expect(scanNote({ running: true, subnet: "10.0.0.0/24", found: [], error: null })).toBe("asking every address in 10.0.0.0/24…");
  expect(scanNote({ running: false, subnet: "10.0.0.0/24", found: [], error: "no route" })).toBe("the scan failed: no route");
});

test("a found board is offered to lost IPv4 boards it is not already", () => {
  const found = (patch: Partial<FoundBoard>): FoundBoard => ({
    address: "192.168.1.77", mac: "001122334455", name: "WLED", ver: "16.0.1", live: false, lm: null, lip: null,
    board: null, at: null, ...patch,
  });
  const bad = [
    board({ level: "bad", lost: true, board: "A" }),
    board({ level: "bad", lost: true, board: "B", host: "pewpew-2.local" }),
    board({ level: "bad", board: "C", host: "192.168.1.51" }), // bad, but still answering
  ];
  expect(rebindOffers(found({}), bad)).toEqual(["A"]);
  expect(rebindOffers(found({ at: "A" }), bad)).toEqual([]);
  expect(rebindOffers(found({ board: "C" }), bad)).toEqual([]);
  expect(rebindOffers(found({ board: "A" }), bad)).toEqual(["A"]);
});
