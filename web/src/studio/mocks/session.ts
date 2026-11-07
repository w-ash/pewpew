/**
 * A mock `/ws/session`, for dev and tests only. It follows the backend's
 * behavior (src/pewpew/studio/session.py, docs/studio/contracts.md): the
 * session starts in `tide` on a 256-pixel placeholder; `hello` comes on
 * connect and after each bind, the per-frame states after it; a request with
 * an `id` is answered with `ack` or `refused`, and one without is answered
 * only when refused; while paused, every request but `pause`, `resume` and
 * `bind` is refused. A failed bind is `refused` with `control: "bind"`.
 */
import { ws } from "msw";
import type { Arrangement } from "../api/types";
import { type PowerCap, powerOf } from "../editor/arrangement";
import { encodeFrame } from "../session/protocol";
import { MockAura } from "./aura";
import { MockCompileError, mockCompile } from "./compile";
import { mockWatts, renderMockFrame } from "./frames";
import { MOCK_LOOKS } from "./looks";

const FPS = 30;
const PLACEHOLDER_N = 256;
/** What a session without a looks file, boards or a room refuses. */
const NO_FILE = ["recall", "save", "keep", "delete", "cycle", "fade"];
const NO_BOARDS = ["scan", "rebind", "blink"];

const sessionLink = ws.link(/\/ws\/session$/);

export const sessionHandler = sessionLink.addEventListener(
  "connection",
  ({ client }) => {
    let n = PLACEHOLDER_N;
    let cap: PowerCap = { max_watts: null, max_brightness: 1 };
    const names = Object.keys(MOCK_LOOKS);
    let made = 0;
    const aura = new MockAura((MOCK_LOOKS.tide ?? MOCK_LOOKS[names[0]!])!);
    let paused = false;
    let seq = 0;
    let t = 0;
    const send = (msg: object) => client.send(JSON.stringify(msg));
    const states = () => {
      for (const msg of aura.states()) send(msg);
    };
    const hello = () => {
      send({ type: "hello", n, fps: FPS, capabilities: ["ack", "look"] });
      states();
    };

    hello();
    const timer = setInterval(() => {
      if (paused) return;
      t += 1 / FPS;
      seq = (seq + 1) >>> 0;
      const level = aura.blackout ? 0 : aura.master;
      const rgb = renderMockFrame(aura.layers.length, level, n, t);
      // The server's limiter on the linear frame, done here on display bytes.
      const uncapped = mockWatts(rgb);
      const s = Math.min(
        cap.max_brightness,
        cap.max_watts === null ? 1 : cap.max_watts / Math.max(uncapped, 1e-9),
      );
      if (s < 1) {
        const k = s ** (1 / 2.2);
        for (let i = 0; i < rgb.length; i++) rgb[i] = Math.round(rgb[i]! * k);
      }
      client.send(encodeFrame(t, seq, rgb));
      if (seq % (FPS / 2) === 0)
        send({
          type: "power",
          watts: uncapped * Math.min(s, 1),
          uncapped_watts: uncapped,
        });
    }, 1000 / FPS);

    /** The engine's answer to request `msg`: `reason` refuses it; else an `ack` when it has an `id`. */
    const answer = (msg: Record<string, unknown>, reason: string | null) => {
      const id = msg.id ?? null;
      if (reason !== null)
        send({
          type: "refused",
          control: msg.type,
          name: msg.type === "set" ? msg.name : null,
          id,
          reason,
        });
      else if (id !== null) send({ type: "ack", id, control: msg.type });
    };

    client.addEventListener("close", () => clearInterval(timer));
    client.addEventListener("message", (event) => {
      if (typeof event.data !== "string") return;
      let msg: { type?: string; [k: string]: unknown };
      try {
        msg = JSON.parse(event.data);
      } catch {
        return;
      }
      let reason: string | null = null;
      if (paused && !["pause", "resume", "bind"].includes(String(msg.type))) {
        answer(msg, "the session is paused: resume it first");
        return;
      }
      switch (msg.type) {
        case "pause":
          paused = true;
          return;
        case "resume":
          paused = false;
          return;
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
            send({
              type: "refused",
              control: "bind",
              name: null,
              id: null,
              reason: (e as Error).message,
              issues: e instanceof MockCompileError ? e.issues : [],
            });
          }
          return;
        case "set":
          reason = aura.set(msg.name, msg.value);
          break;
        case "look":
          if (typeof msg.look !== "object" || !msg.look)
            reason = "a look is an object with 'layers'";
          else aura.play(msg.look as never);
          break;
        case "surprise":
        case "vary":
          // The mock makes no looks: it plays the next example.
          made = (made + 1) % names.length;
          aura.play(MOCK_LOOKS[names[made]!]!);
          break;
        case "add_layer":
          reason = aura.add(msg.layer as Record<string, unknown>, msg.below);
          break;
        case "remove_layer":
          reason = aura.remove(msg.lid);
          break;
        case "move_layer":
          reason = aura.move(msg.lid, msg.to);
          break;
        case "front":
          aura.front = (msg.paths as string[]) ?? [];
          break;
        case "master":
          aura.master = Number(msg.value);
          break;
        case "blackout":
          aura.blackout = msg.on === true;
          break;
        default:
          if (NO_FILE.includes(String(msg.type)))
            reason = "no looks file: start the run with --looks PATH";
          else if (NO_BOARDS.includes(String(msg.type)))
            reason = "this session drives no boards";
          else if (msg.id === undefined) return;
          else reason = `unknown control ${String(msg.type)}`;
      }
      answer(msg, reason);
      if (reason === null) states();
    });
  },
);
