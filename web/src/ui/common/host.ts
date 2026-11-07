const LOOPBACK = new Set(["127.0.0.1", "localhost", "[::1]", "::1"]);

/** Whether the page runs on the laptop that runs the engine, which a command line flag can
 * change, rather than on a phone or another machine on the private network. */
export function onEngineHost(): boolean {
  return LOOPBACK.has(location.hostname);
}
