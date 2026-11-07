// The dev server's guard on its engine proxy. The proxy rewrites Origin and
// Host to the engine's own, which defeats the engine's cross-origin check, so
// the dev server makes that check itself: any other web page open in the
// developer's browser must not drive the engine through it (ADR-020).

const LOOPBACK = new Set(["127.0.0.1", "localhost", "[::1]"]);

/** Whether a WebSocket upgrade to the dev server may reach the engine: its
 * Host names this machine by loopback address (not a name a DNS answer can
 * move), and its Origin, when there is one, is the dev server itself. A
 * request with no Origin is not from a web page. */
export function upgradeAllowed(host: string | undefined, origin: string | undefined): boolean {
  if (!host) return false;
  const name = host.startsWith("[") ? host.slice(0, host.indexOf("]") + 1) : host.split(":")[0];
  if (!name || !LOOPBACK.has(name.toLowerCase())) return false;
  return origin === undefined || origin.toLowerCase() === `http://${host.toLowerCase()}`;
}
