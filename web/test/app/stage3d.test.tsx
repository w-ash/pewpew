import { useGLTF } from "@react-three/drei";
import { afterEach, beforeEach, expect, onTestFinished, test, vi } from "vitest";
import { App } from "../../src/app/App";
import type { PartsCatalog } from "../../src/rig/parts";
import { forgetParts, PARTS_URL } from "../../src/rig/loadParts";
import index from "../../../src/pewpew/rig/assemblies/index.json";
import { first, LATER } from "../fixtures/messages";
import { renderWired } from "../harness";
import { partsCatalog } from "../studio/fixtures/rig";

// The layout's rig: two strip variants.
const RIG_LAYOUT = first("layout", LATER);
// The strip type's committed GLB, served by Vite's dev server.
const STRIP_GLB = new URL(`../../../src/pewpew/rig/assemblies/${index.strip.digest}.glb`, import.meta.url).href;
const CATALOG: PartsCatalog = {
  ...partsCatalog,
  fixture_types: [
    { id: "strip", name: "Straight LED strip", digest: index.strip.digest, assembly_url: STRIP_GLB, dims: { length: { v: 1 } } },
  ],
};

const realFetch = globalThis.fetch;
/** The engine's answer to `/parts.json`; the GLB comes from the dev server. */
let partsAnswer: () => Response;
/** Whether the GLB answers 404, as an engine upgraded under the page answers an old assembly's URL. */
let glbGone = false;
const fetched = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
  const url = typeof input === "string" ? input : input instanceof URL ? input.href : input.url;
  if (url === PARTS_URL) return partsAnswer();
  return glbGone && url === STRIP_GLB ? new Response("no such assembly\n", { status: 404 }) : realFetch(input, init);
});
const partsFetches = () => fetched.mock.calls.filter(([input]) => input === PARTS_URL).length;

beforeEach(() => {
  forgetParts();
  useGLTF.clear(STRIP_GLB); // the loader keeps what it loaded for the page's life
  fetched.mockClear();
  partsAnswer = () => Response.json(CATALOG);
  glbGone = false;
  vi.stubGlobal("fetch", fetched);
});

afterEach(() => {
  vi.unstubAllGlobals();
});

async function show3d() {
  const wired = await renderWired(<App />);
  wired.receive(RIG_LAYOUT);
  await wired.screen.getByRole("radiogroup", { name: "Stage view" }).getByText("3D", { exact: true }).click();
  return wired;
}

test("3D loads its own files, fetches the parts catalog and each GLB, and mounts the canvas", async () => {
  const { screen } = await show3d();
  await expect.element(screen.getByRole("img", { name: "3D preview of the LEDs" })).toBeInTheDocument();
  expect(document.querySelector(".stage-3d canvas")).not.toBeNull();
  expect(partsFetches()).toBe(1);
  await expect.poll(() => fetched.mock.calls.some(([input]) => String(input instanceof Request ? input.url : input) === STRIP_GLB)).toBe(true);
  expect(document.querySelector(".stage-3d-note")).toBeNull();
});

test("a parts catalog that fails shows the boundary's note, and Retry fetches it again", async () => {
  partsAnswer = () => new Response("", { status: 503 });
  const { screen } = await show3d();
  const note = screen.getByRole("alert").filter({ hasText: "The 3D view did not load." });
  await expect.element(note).toBeInTheDocument();
  expect(partsFetches()).toBe(1);
  partsAnswer = () => Response.json(CATALOG);
  await note.getByRole("button", { name: "Retry" }).click();
  await expect.element(screen.getByRole("img", { name: "3D preview of the LEDs" })).toBeInTheDocument();
  await expect.poll(partsFetches).toBe(2);
});

/** R3F reports an error its tree caught as an `error` event (`reportError`), which Vitest counts as
 * unhandled; the view's boundary handles it. */
function expectLoadErrors(): () => void {
  const swallow = (e: ErrorEvent) => {
    if (String(e.message).includes("Could not load")) e.stopImmediatePropagation();
  };
  window.addEventListener("error", swallow, { capture: true });
  return () => window.removeEventListener("error", swallow, { capture: true });
}

test("a GLB that fails shows the view's note, and its Retry fetches the parts catalog again", async () => {
  onTestFinished(expectLoadErrors());
  glbGone = true;
  const { screen } = await show3d();
  const note = screen.getByRole("alert").filter({ hasText: "Fixture models did not load" });
  await expect.element(note).toBeInTheDocument();
  await expect.element(screen.getByRole("img", { name: "3D preview of the LEDs" })).toBeInTheDocument();
  expect(partsFetches()).toBe(1);
  glbGone = false;
  await note.getByRole("button", { name: "Retry" }).click();
  await expect.element(note).not.toBeInTheDocument();
  await expect.element(screen.getByRole("img", { name: "3D preview of the LEDs" })).toBeInTheDocument();
  await expect.poll(partsFetches).toBe(2);
});
