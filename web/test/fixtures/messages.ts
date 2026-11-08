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

/** tests/goldens/session.json, as a Gallery session wrote it. Read loosely: the server writes the golden,
 * so a key it drops fails a test here, not the build. */
const gallery = session as unknown as {
  readonly greeting: readonly ServerMessage[];
  readonly power: Message<"power">;
  readonly refused: Readonly<Record<"session" | "message" | "paused", Message<"refused">>>;
  readonly exported: Message<"exported">;
};

/** What a Gallery session sends a new client: its hello (a share's rig, capabilities "gallery" and
 * "pause"), then the state of its look and its in-memory looks book. */
export const SESSION_GREETING = gallery.greeting;
/** The power reading of a streamed frame. */
export const SESSION_POWER = gallery.power;
/** The session's refusals: of the session, of a binary message, and of a request while paused. */
export const SESSION_REFUSED = gallery.refused;
/** The answer to an `export` of every look as a looks file. */
export const SESSION_EXPORTED = gallery.exported;

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

/** What a Gallery session's hello says it takes. */
export const GALLERY_CAPABILITIES: readonly string[] = ["ack", "look", "export", "pause", "gallery"];

/** A Gallery session's greeting, made from the engine's (`greeting`): its hello on the golden's rig (the
 * later layout's) with the Gallery's capabilities, and no health, arrangement or report, which the
 * Gallery never sends. */
export function galleryGreeting(op = "zoo_test"): ServerMessage[] {
  const { type: _, ...rig } = first("layout", LATER);
  return greeting(op)
    .filter((msg) => msg.type !== "health" && msg.type !== "arrangement" && msg.type !== "report")
    .map((msg) => (msg.type === "hello" ? { ...msg, ...rig, capabilities: GALLERY_CAPABILITIES } : msg));
}
