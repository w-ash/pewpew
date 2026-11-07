import { HttpResponse, http } from "msw";
import type { Arrangement } from "@/api/types";
import { mockCatalog } from "./catalog";
import { MockCompileError, mockCompile } from "./compile";
import { MOCK_PATTERNS } from "./frames";
import { mockGlb } from "./glb";
import { defaults, sessionHandler } from "./session";

/**
 * Saved arrangements, keyed by a fake 22-character id. Handlers run in the
 * page, so the browser mock keeps them in localStorage to survive opening
 * the link.
 */
const memory = new Map<string, Arrangement>();
const saved = {
  get(id: string): Arrangement | undefined {
    try {
      const text = globalThis.localStorage?.getItem(`pewpew-mock:${id}`);
      if (text) return JSON.parse(text) as Arrangement;
    } catch {}
    return memory.get(id);
  },
  set(id: string, arrangement: Arrangement) {
    memory.set(id, arrangement);
    try {
      globalThis.localStorage?.setItem(
        `pewpew-mock:${id}`,
        JSON.stringify(arrangement),
      );
    } catch {}
  },
};

function mockId(text: string): string {
  let h = 0x811c9dc5;
  for (let i = 0; i < text.length; i++)
    h = Math.imul(h ^ text.charCodeAt(i), 0x01000193) >>> 0;
  return `mock${h.toString(36)}`.padEnd(22, "0").slice(0, 22);
}

function compileOr422(arrangement: Arrangement) {
  try {
    return mockCompile(arrangement);
  } catch (e) {
    if (e instanceof MockCompileError)
      return HttpResponse.json({ issues: e.issues }, { status: 422 });
    throw e;
  }
}

export const httpHandlers = [
  http.get("/api/catalog", () => HttpResponse.json(mockCatalog)),
  http.get("/api/patterns", () =>
    HttpResponse.json(
      Object.entries(MOCK_PATTERNS).map(([name, params]) => ({
        name,
        params,
        values: defaults(name),
      })),
    ),
  ),
  http.post("/api/compile", async ({ request }) => {
    const rig = compileOr422((await request.json()) as Arrangement);
    return rig instanceof HttpResponse ? rig : HttpResponse.json(rig);
  }),
  http.get("/api/assembly/:file", async ({ params }) => {
    const glb = mockGlb(String(params.file).replace(/\.glb$/, ""));
    if (!glb) return new HttpResponse(null, { status: 404 });
    return HttpResponse.arrayBuffer(await glb, {
      headers: { "Content-Type": "model/gltf-binary" },
    });
  }),
  http.post("/api/arrangements", async ({ request }) => {
    const arrangement = (await request.json()) as Arrangement;
    const rig = compileOr422(arrangement);
    if (rig instanceof HttpResponse) return rig;
    const id = mockId(JSON.stringify(arrangement));
    saved.set(id, arrangement);
    return HttpResponse.json({ id });
  }),
  http.get("/api/arrangements/:id", ({ params }) => {
    const arrangement = saved.get(String(params.id));
    return arrangement
      ? HttpResponse.json(arrangement)
      : HttpResponse.json({ detail: "no such arrangement" }, { status: 404 });
  }),
];

export const handlers = [...httpHandlers, sessionHandler];
