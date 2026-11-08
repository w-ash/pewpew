import { useEffect } from "react";
import { RECONNECT_MS, Socket } from "../wire/socket";
import { useWireContext, type WireStore } from "../wire/store";

/** The longest wait before a reconnect to the Gallery. */
export const RECONNECT_MAX_MS = 10_000;

/** The Gallery's reconnect waits for `store`'s connection, asked at each close: RECONNECT_MS after a
 * connection that had a hello, else twice the last wait, to RECONNECT_MAX_MS, so a full Gallery is not
 * asked every second. */
export function backoff(store: WireStore): () => number {
  let wait = RECONNECT_MS;
  let seen = -1;
  return () => {
    const { session } = store.getState();
    wait = session === seen ? Math.min(wait * 2, RECONNECT_MAX_MS) : RECONNECT_MS;
    seen = session;
    return wait;
  };
}

/** Give `socket` the Gallery's reconnect waits for `store` (`backoff`); returns what puts its own back. */
function backOff(socket: Socket, store: WireStore): () => void {
  const own = socket.retryMs;
  socket.retryMs = backoff(store);
  return () => {
    socket.retryMs = own;
  };
}

/** While the page is the Gallery's, its socket backs its reconnects off (`backoff`). */
export function useBackoff(): void {
  const { store, sender } = useWireContext();
  useEffect(() => (sender instanceof Socket ? backOff(sender, store) : undefined), [store, sender]);
}
