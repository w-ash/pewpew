/**
 * The wire to the engine, for other pages: the hosted studio talks to its
 * session through this socket and store, so both pages read one protocol.
 */

export { parseFrame, type ClientMessage, type Frame, type Sender, type ServerMessage, type TypedMessage } from "./wire/protocol";
export { Socket } from "./wire/socket";
export { useRefusalExcept, useSender, useStandingAura, useWire, WireContext, WireStore } from "./wire/store";
