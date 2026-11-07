/**
 * A mock `/ws/session`, for dev and tests only. It follows the backend's
 * behavior (src/pewpew/studio/app.py and session.py): the session starts on
 * a 64-pixel placeholder, `hello` comes on connect and after each bind or
 * pattern change with the params' records and values, `bound` precedes that
 * `hello`, and a failed bind is `refused` with `control: "bind"` and
 * `issues`.
 */
import { ws } from "msw";
import type { Arrangement, ParamValue } from "@/api/types";
import { type PowerCap, powerOf } from "@/editor/arrangement";
import { encodeFrame } from "@/session/protocol";
import { MockCompileError, mockCompile } from "./compile";
import {
  MOCK_PATTERNS,
  mockRefusal,
  mockWatts,
  renderMockFrame,
} from "./frames";

const FPS = 30;
const PLACEHOLDER_N = 64;

const sessionLink = ws.link(/\/ws\/session$/);

export const sessionHandler = sessionLink.addEventListener(
  "connection",
  ({ client }) => {
    let n = PLACEHOLDER_N;
    let cap: PowerCap = { max_watts: null, max_brightness: 1 };
    let pattern = "rainbow";
    let values: Record<string, ParamValue> = defaults(pattern);
    let paused = false;
    let seq = 0;
    let t = 0;
    const send = (msg: object) => client.send(JSON.stringify(msg));
    const hello = () =>
      send({
        type: "hello",
        n,
        fps: FPS,
        patterns: Object.keys(MOCK_PATTERNS).sort(),
        pattern,
        params: MOCK_PATTERNS[pattern],
        values,
      });

    hello();
    const timer = setInterval(() => {
      if (paused) return;
      t += 1 / FPS;
      seq = (seq + 1) >>> 0;
      const rgb = renderMockFrame(pattern, values, n, t);
      // The server's limiter on the linear frame, done here on display bytes.
      const uncapped = mockWatts(rgb);
      const s = Math.min(
        cap.max_brightness,
        cap.max_watts === null ? 1 : cap.max_watts / Math.max(uncapped, 1e-9),
      );
      if (s < 1) {
        const k = s ** (1 / 2.2);
        for (let i = 0; i < rgb.length; i++) rgb[i] = Math.round(rgb[i] * k);
      }
      client.send(encodeFrame(t, seq, rgb));
      if (seq % (FPS / 2) === 0)
        send({
          type: "power",
          watts: uncapped * Math.min(s, 1),
          uncapped_watts: uncapped,
        });
    }, 1000 / FPS);

    client.addEventListener("close", () => clearInterval(timer));
    client.addEventListener("message", (event) => {
      if (typeof event.data !== "string") return;
      let msg: { type?: string; [k: string]: unknown };
      try {
        msg = JSON.parse(event.data);
      } catch {
        return;
      }
      switch (msg.type) {
        case "pause":
          paused = true;
          break;
        case "resume":
          paused = false;
          break;
        case "bind":
          try {
            const rig = mockCompile(msg.arrangement as Arrangement);
            n = rig.n;
            cap = powerOf(msg.arrangement as Arrangement);
            send({
              type: "bound",
              n,
              catalog_digest: rig.catalog_digest,
              issues: rig.issues,
            });
            hello();
          } catch (e) {
            const issues = e instanceof MockCompileError ? e.issues : [];
            send({
              type: "refused",
              control: "bind",
              reason: (e as Error).message,
              issues,
            });
          }
          break;
        case "pattern": {
          const name = String(msg.name).toLowerCase();
          if (!(name in MOCK_PATTERNS)) {
            send({
              type: "refused",
              control: "pattern",
              reason: `unknown pattern; available: ${Object.keys(MOCK_PATTERNS).join(", ")}`,
            });
            break;
          }
          pattern = name;
          values = defaults(pattern);
          hello();
          break;
        }
        case "set": {
          const spec = MOCK_PATTERNS[pattern].find((p) => p.name === msg.name);
          const reason = spec
            ? mockRefusal(spec, msg.value)
            : `no param ${String(msg.name)}`;
          if (reason !== null) {
            send({
              type: "refused",
              control: "set",
              ...(typeof msg.name === "string" ? { name: msg.name } : {}),
              reason,
            });
            break;
          }
          values = { ...values, [msg.name as string]: msg.value as ParamValue };
          send({ type: "params", values });
          break;
        }
      }
    });
  },
);

export function defaults(pattern: string): Record<string, ParamValue> {
  return Object.fromEntries(
    MOCK_PATTERNS[pattern].map((p) => [p.name, p.default as ParamValue]),
  );
}
