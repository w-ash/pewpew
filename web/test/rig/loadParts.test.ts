import { afterEach, beforeEach, expect, test, vi } from "vitest";
import { forgetParts, loadParts, PARTS_URL } from "../../src/rig/loadParts";
import { partsCatalog } from "../studio/fixtures/rig";

const fetched = vi.fn<typeof fetch>();

beforeEach(() => {
  forgetParts();
  fetched.mockReset();
  fetched.mockImplementation(async () => Response.json(partsCatalog));
  vi.stubGlobal("fetch", fetched);
});

afterEach(() => {
  vi.unstubAllGlobals();
});

test("the catalog is fetched once for a catalog digest, and again for a new one", async () => {
  const first = loadParts("aaa");
  expect(loadParts("aaa")).toBe(first);
  expect(await first).toEqual(partsCatalog);
  expect(fetched).toHaveBeenCalledOnce();
  expect(fetched).toHaveBeenCalledWith(PARTS_URL);
  await loadParts("bbb");
  expect(fetched).toHaveBeenCalledTimes(2);
});

test("forgetParts makes the next read fetch again, for the same digest", async () => {
  await loadParts("aaa");
  forgetParts();
  await loadParts("aaa");
  expect(fetched).toHaveBeenCalledTimes(2);
});

test("a failed fetch stays failed until forgotten", async () => {
  fetched.mockImplementationOnce(async () => new Response("", { status: 503 }));
  const failed = loadParts("aaa");
  await expect(failed).rejects.toThrow("the parts catalog answered 503");
  // React's `use` reads the same rejection on a render after it, rather than fetching in a loop.
  expect(loadParts("aaa")).toBe(failed);
  forgetParts();
  expect(await loadParts("aaa")).toEqual(partsCatalog);
  expect(fetched).toHaveBeenCalledTimes(2);
});
