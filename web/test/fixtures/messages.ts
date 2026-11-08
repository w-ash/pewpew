import session from "../../../tests/goldens/session.json";
import wire from "../../../tests/goldens/wire.json";
import type { BoardHealth, HealthState } from "../../src/health/health";
import type { AuraState } from "../../src/aura/aura";
import type { Control, HelloMessage, ServerMessage } from "../../src/wire/protocol";
import { OPS } from "./describe";

type Message<T extends ServerMessage["type"]> = Extract<ServerMessage, { type: T }>;

/** What a real engine sends a new client, in order (tests/goldens/wire.json). */
export const GREETING = wire.greeting as unknown as readonly ServerMessage[];
/** The golden's later messages: a held trigger, a refusal, a look and a layer refused with their
 * ids, an ack, a render error, a scan and a room layout. */
export const LATER = wire.later as unknown as readonly ServerMessage[];

/** What a studio session sends a new client (tests/goldens/session.json): the engine's greeting on the
 * placeholder rig. */
export const SESSION_GREETING = session.greeting as unknown as readonly ServerMessage[];
/** The layout after a bind: the bound rig of 16 pixels. */
export const SESSION_LAYOUT = session.layout as unknown as Message<"layout">;
/** The power reading of a streamed frame. */
export const SESSION_POWER = session.power as unknown as Message<"power">;
/** The session's refusals: of a bind, of the session, of a binary message, and of a request while paused. */
export const SESSION_REFUSED = session.refused as unknown as Readonly<Record<"bind" | "session" | "message" | "paused", Message<"refused">>>;

/** The first message of `type` in `messages`. */
export function first<T extends ServerMessage["type"]>(type: T, messages: readonly ServerMessage[] = GREETING): Message<T> {
  const msg = messages.find((m) => m.type === type);
  if (!msg) throw new Error(`no ${type} message in wire.json`);
  return msg as Message<T>;
}

const { type: _aura, ...aura } = first("aura");
const { type: _health, ...greetingHealth } = first("health");

/** The greeting's aura state: one layer running the zoo_test op, at master 0.8, in look warm of warm and
 * cool, with triggers door and bell disarmed. */
export const AURA: AuraState = aura;

export function hello(patch: Partial<HelloMessage> = {}): HelloMessage {
  return { ...first("hello"), ...patch };
}

/** A refusal of `control` without an `id`, as the page gets one; `name` is the refused knob of a `set`. */
export function refused(control: Control, reason: string, name: string | null = null): Message<"refused"> {
  return { type: "refused", control, name, id: null, reason };
}

/** The greeting of an engine whose knobs are op `op`'s: its declarations and defaults stand in for the
 * golden's. */
export function greeting(op = "zoo_test"): ServerMessage[] {
  const records = OPS[op] ?? [];
  return GREETING.map((msg): ServerMessage => {
    if (msg.type === "declare") return { type: "declare", params: records };
    if (msg.type === "params") return { type: "params", values: Object.fromEntries(records.map((r) => [r.name, r.default])) };
    return msg;
  });
}

/** The greeting's one board (A at 192.168.1.50, healthy), with `patch`. */
export const board = (patch: Partial<BoardHealth>): BoardHealth => ({ ...greetingHealth.boards[0]!, ...patch });

export const health = (boards: BoardHealth[], patch: Partial<HealthState> = {}): HealthState => ({ ...greetingHealth, boards, ...patch });
