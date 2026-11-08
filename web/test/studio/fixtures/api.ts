import { onTestFinished, vi } from "vitest";
import type { Arrangement, LookDocument } from "../../../src/studio/api/types";
import { partsCatalog, stubCompile } from "./rig";

interface Book {
  current: string;
  looks: Record<string, LookDocument>;
}

const files = import.meta.glob<Book>("../../../../examples/*.look.json", { eager: true, import: "default" });

/** The current look of each examples/*.look.json by the file's name, as `GET /api/looks` gives them. */
export const EXAMPLE_LOOKS: Record<string, LookDocument> = Object.fromEntries(
  Object.entries(files).map(([path, book]) => [path.replace(/^.*\//, "").replace(/\.look\.json$/, ""), book.looks[book.current]!]),
);

const reply = (body: unknown, status = 200) => new Response(JSON.stringify(body), { status });

/** Answers the page's fetches for the catalog, the example looks and the compile until the test ends, and
 * returns the paths it asked for, in order. A compile of a fixture of type `no-such-type`, or of an array group without counts, is refused with 422;
 * any other path is a 404. */
export function stubApi(): string[] {
  const asked: string[] = [];
  vi.stubGlobal("fetch", async (input: RequestInfo | URL, init?: RequestInit) => {
    const { pathname } = new URL(typeof input === "string" || input instanceof URL ? input : input.url, location.href);
    asked.push(pathname);
    if (pathname === "/api/catalog") return reply(partsCatalog);
    if (pathname === "/api/looks") return reply(EXAMPLE_LOOKS);
    if (pathname === "/api/compile") {
      const arrangement = JSON.parse(typeof init?.body === "string" ? init.body : "{}") as Arrangement;
      const bad = arrangement.fixtures.some((f) => f.type === "no-such-type") || arrangement.groups.some((g) => g.preset === "array" && !g.counts);
      if (bad) return reply({ issues: [{ level: "error", code: "invalid", message: "the arrangement does not compile", ref: null }] }, 422);
      return reply(stubCompile(arrangement));
    }
    return reply({ detail: "not found" }, 404);
  });
  onTestFinished(() => {
    vi.unstubAllGlobals();
  });
  return asked;
}
