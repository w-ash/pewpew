// Every message on the preview socket, both directions. This file is where the
// protocol is described; pewpew.sinks.preview builds each message from one
// source, and tests/goldens/wire.json holds real ones. Every text message is
// absolute state, so the last write wins on every tab. A new client gets the
// hello, then the current text of every other server message but `layout`,
// `refused` and `ack`; after that, each one when its text changes.
//
// Any client may give a request an `id`, which its answer, an `ack` or a
// `refused`, carries back. This page gives one only to a request it shows
// as busy until the engine answers (`Sender.ask`: a look the engine makes,
// or a keep). A client outside the package (`python -m pewpew push`, an
// agent) also reads the hello's `capabilities` (ADR-020 amendment
// "capabilities"). This page ships with its engine: it never reads them.
import type { HealthState } from "../../domain/health/health";
import { isRecord, type Param, type ValueOf } from "../../domain/params/schema";
import type { MapShape } from "../../domain/room/layout";
import type { AuraState } from "../../domain/aura/aura";
import type { Catalog } from "../../domain/stack/catalog";

export interface HelloMessage extends MapShape {
  readonly type: "hello";
  /** The gamma the frames are encoded with, so a swatch can match them. */
  readonly display_gamma: number;
  /** The build stamp of the page the engine serves; a tab built otherwise reloads. Null without one. */
  readonly build: string | null;
  /** For clients outside the package only; this page never reads it. What such a client may rely on:
   * "ack" (a request with an `id` is answered), and "look" (the run takes `look`, `run --accept-looks`).
   * Empty when no control is wired. */
  readonly capabilities: readonly string[];
}

/** A new map (a room map reload), sent before the first frame drawn on it. */
interface LayoutMessage extends MapShape {
  readonly type: "layout";
}

/** The part of the engine an error comes from. On "render" a layer of the running look raises: it
 * pulses red in its place, or an unattended run leaves it out of a mix that has other layers. */
export type ErrorSource = "render" | "reload" | "looks";

/** The engine's error, when it changes; every field is null when there is none. */
interface StatusMessage {
  readonly type: "status";
  readonly error: string | null;
  readonly source: ErrorSource | null;
  /** For a render error, the path of the part that raised: a layer's node (`layers.base.comet`)
   * or a signal (`signals.breath`), during a fade maybe not one of the look fading in. */
  readonly path: string | null;
}

/** Every knob's value, by address (a record's `name`), as JSON. */
interface ParamsMessage {
  readonly type: "params";
  readonly values: Readonly<Record<string, unknown>>;
}

/** The live value of each knob a route moves (`aura.stack.routes`): its value plus the routes'
 * offsets, wrapped or clamped into its range, by address (a param's, or a color's part,
 * `layers.base.zoo.color.h`), rounded to its decimals. Read at most 10 times a second; empty when
 * no route runs. A readout only: the knob's own value, which `params` carries, is what a control
 * shows and sets. */
interface ModMessage {
  readonly type: "mod";
  readonly values: Readonly<Record<string, number>>;
}

/** Every knob of the running look in display order (pewpew.params spec()), each record's `name`
 * its address (`layers.base.comet.speed`, `signals.breath.rate`), plus the `layer` and `node` it
 * belongs to (`node` "" for a layer's opacity, blend and enabled; `layer` "" and `node` the
 * signal's id for a signal's knob); when they change (a hot reload, a pick, a recall). A `params`
 * message always follows. */
interface DeclareMessage {
  readonly type: "declare";
  readonly params: readonly unknown[];
}

interface AuraMessage extends AuraState {
  readonly type: "aura";
}

/** Never sent when the run has no health monitor. */
interface HealthMessage extends HealthState {
  readonly type: "health";
}

/** What a layer can run, for the page's "add layer" cards, and what each blend mode does
 * (pewpew.fx.catalog.page); again when an op file loads or the pattern names change. */
interface CatalogMessage extends Catalog {
  readonly type: "catalog";
}

/** A request's `id`, as a client outside the package sent it; it comes back as sent. */
export type RequestId = string | number;

/** A declined request, to the client that sent it. The reason names the param,
 * pattern, look, fixture or cap, never a path, and carries no hint: the port has no login. */
interface RefusedMessage {
  readonly type: "refused";
  /** The request's type; for a request with an `id`, maybe one the engine does not know, or
   * null when its `type` is not text. */
  readonly control: Control | null;
  /** The address of what was refused: the param of a `set`, or the part of a `look`
   * (`layers.base.comet.pattern`, `master`); null when no one part is to blame. */
  readonly name: string | null;
  /** The request's `id`; null without one. */
  readonly id: RequestId | null;
  readonly reason: string;
}

/** An accepted request that carried an `id`, to the client that sent it. */
interface AckMessage {
  readonly type: "ack";
  readonly id: RequestId;
  readonly control: Control;
}

export type ServerMessage =
  | HelloMessage | LayoutMessage | StatusMessage | ParamsMessage | ModMessage | DeclareMessage
  | AuraMessage | HealthMessage | CatalogMessage | RefusedMessage | AckMessage;

/** What a client may send. The engine checks every field and refuses a bad one with its
 * reason. Without an `id`, only a message that is not an object, has no known `type`, or is
 * a `set` without a string `name` gets no reply. Any message may also carry an `id` (a
 * `RequestId`); the engine then answers it with an `ack` or a `refused` that carries it, an
 * unknown `type` included. */
export type ClientMessage =
  /** `value` as JSON, in the param's kind, for the knob at address `name`. */
  | { readonly type: "set"; readonly name: string; readonly value: unknown }
  /** One of the aura's `patterns`, by name, never a path, on `layer`; null for the bottom layer. */
  | { readonly type: "pick"; readonly name: string; readonly layer: string | null }
  /** A layer for the running look, in the looks file's form, its patterns by name, put under layer
   * `below`, or on top when null. Without an `id` the engine gives it a free one made from its `out`
   * node (`plasma`, `plasma2`). The look stays current, changed until a save keeps it. */
  | { readonly type: "add_layer"; readonly layer: Readonly<Record<string, unknown>>; readonly below: string | null }
  /** Stop layer `lid` of the running look; the last one stays. */
  | { readonly type: "remove_layer"; readonly lid: string }
  /** Run layer `lid` at render index `to` among the running look's layers (0: the bottom). */
  | { readonly type: "move_layer"; readonly lid: string; readonly to: number }
  /** Show the knobs at addresses `paths` first, in that order: the look's front, an edit a save keeps. */
  | { readonly type: "front"; readonly paths: readonly string[] }
  /** At most the cap. */
  | { readonly type: "master"; readonly value: number }
  | { readonly type: "blackout"; readonly on: boolean }
  /** Crossfade over `fade` seconds, or the look's own fade when null. A recall during a fade waits for it to end. */
  | { readonly type: "recall"; readonly name: string; readonly fade: number | null }
  /** Fade to a whole look (looks v4, one look), unsaved, over `fade` seconds or its own fade when
   * null; it ends a running fade. Its patterns go by name, never a file. Needs `run --accept-looks`;
   * sent by clients outside the package, never by this page. */
  | { readonly type: "look"; readonly look: unknown; readonly fade: number | null }
  /** Fade to a look the engine makes from `seed` for its map, or from its own next seed when null; it plays
   * unsaved, as a pick does, until a `save`. Refused when nothing it made passed its gate. */
  | { readonly type: "surprise"; readonly seed: number | null }
  /** Fade to a look the engine makes like the running one, moved by `strength` (above 0, at most 1; null for the
   * default) from `seed` (null for its own next), unsaved, as `surprise` does. */
  | { readonly type: "vary"; readonly strength: number | null; readonly seed: number | null }
  /** A `save` with a null name, for clients outside the package; this page sends that `save` instead. */
  | { readonly type: "keep" }
  /** Save the live state as look `name`, replacing one of that name. Null saves it under the name it offers
   * (the looks' `offered`: a surprise's or a vary's, "surprise 7", else "kept", with a number past the first
   * one taken) and with a made look's fade; it becomes the current look, and a save under another name and a
   * delete rename it. `fade` is stored when given, else the replaced look's is kept; `master` false leaves the
   * master out, and null keeps the replaced look's choice. Needs a looks file. */
  | { readonly type: "save"; readonly name: string | null; readonly fade: number | null; readonly master: boolean | null }
  | { readonly type: "delete"; readonly name: string }
  /** Whether the idle cycle plays the look. */
  | { readonly type: "cycle"; readonly name: string; readonly on: boolean }
  /** The look's own fade, stored alone: unsaved edits stay unsaved. This and the four above need a looks file. */
  | { readonly type: "fade"; readonly name: string; readonly fade: number }
  /** Triggers fire only while armed; the switch starts off unless the run has `--armed`. */
  | { readonly type: "arm"; readonly on: boolean }
  /** A room event from source "page"; null is an impulse. Refused only when malformed or the
   * queue is full: its fate arrives as the triggers' `last`. */
  | { readonly type: "fire"; readonly name: string; readonly value: number | null }
  /** Look for WLED boards on the laptop's /24 (needs DDP). */
  | { readonly type: "scan" }
  /** Point a room board at an address the last scan found, by rewriting the room file: a
   * tier-1 action. Needs DDP and a room map; a board named by mDNS is never rebound. */
  | { readonly type: "rebind"; readonly board: string; readonly address: string }
  /** Flash a room fixture white and off for a few seconds (needs a room map). With DDP on,
   * this drives the real boards. */
  | { readonly type: "blink"; readonly fixture: string };

/** The inbound type a refusal names. */
export type Control = ClientMessage["type"];

/** What the page sends. */
export interface Sender {
  /** Send at once, after anything `sendLatest` holds. */
  send(msg: ClientMessage): void;
  /** Send with the next animation frame; a newer set of the same param, or
   * a newer master, replaces it. For what a drag sends. */
  sendLatest(msg: ClientMessage): void;
  /** Send at once with an `id`, for a request that takes the engine a while. Settles when the engine
   * answers it, accepted or refused (a refusal reaches the store as any does), or when the connection
   * closes, which leaves it unanswered. */
  ask(msg: ClientMessage): Promise<void>;
}

/** Request a param value, as a drag does. */
export function setParam<P extends Param>(sender: Sender, p: P, value: ValueOf<P>): void {
  sender.sendLatest({ type: "set", name: p.name, value });
}

/** A binary frame: engine time, sequence number, then `n` display-ready RGB
 * triples. Gamma and quantization happen in the engine, once. */
export interface Frame {
  readonly t: number;
  readonly seq: number;
  readonly rgb: Uint8Array;
}

const HEADER = 8; // struct "<fI"

export function parseFrame(data: ArrayBuffer): Frame {
  const view = new DataView(data, 0, HEADER);
  return { t: view.getFloat32(0, true), seq: view.getUint32(4, true), rgb: new Uint8Array(data, HEADER) };
}

// Every server message type: a new member of ServerMessage fails to compile until it is listed.
const TYPES: Readonly<Record<ServerMessage["type"], true>> = {
  hello: true, layout: true, status: true, params: true, mod: true, declare: true, aura: true, health: true,
  catalog: true, refused: true, ack: true,
};

/** The message in `text`, or null for anything this page does not read. */
export function parseMessage(text: string): ServerMessage | null {
  let msg: unknown;
  try {
    msg = JSON.parse(text);
  } catch {
    return null;
  }
  const type = isRecord(msg) ? msg.type : undefined;
  return typeof type === "string" && Object.hasOwn(TYPES, type) ? (msg as ServerMessage) : null;
}
