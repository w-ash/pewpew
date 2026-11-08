/**
 * The engine's parts catalog (`GET /parts.json`, src/pewpew/sinks/preview.py), cached for the page.
 * Apart from the 3D view's files, so the page's own retry can reach it without loading three.js.
 */
import type { PartsCatalog } from "./parts";

export const PARTS_URL = "/parts.json";

let parts: { readonly key: string; readonly promise: Promise<PartsCatalog> } | null = null;

/**
 * The parts catalog, fetched once for each `key`, and again for a new one. The 3D view's key is the
 * rig's `catalog_digest` and its retry count. A failed fetch stays failed, so React's `use` reads the
 * same rejection on each render; `forgetParts` makes the next read fetch again, as the page's retry of
 * a 3D view that did not load does.
 */
export function loadParts(key: string): Promise<PartsCatalog> {
  if (parts?.key === key) return parts.promise;
  const promise = fetch(PARTS_URL).then((r) => {
    if (!r.ok) throw new Error(`the parts catalog answered ${r.status}`);
    return r.json() as Promise<PartsCatalog>;
  });
  parts = { key, promise };
  return promise;
}

/** Makes the next `loadParts` fetch the catalog again. */
export function forgetParts(): void {
  parts = null;
}
