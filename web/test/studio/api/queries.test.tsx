import { QueryClientProvider } from "@tanstack/react-query";
import type { ReactNode } from "react";
import { expect, test, vi } from "vitest";
import { renderHook } from "vitest-browser-react";
import { createQueryClient, useCompiled } from "../../../src/studio/api/queries";
import type { Arrangement } from "../../../src/studio/api/types";
import { DEFAULT_ARRANGEMENT } from "../../../src/studio/store/share";
import { stubApi } from "../fixtures/api";

function wrapper({ children }: { children: ReactNode }) {
  return <QueryClientProvider client={createQueryClient()}>{children}</QueryClientProvider>;
}

const renderCompiled = () =>
  renderHook((props?: { arrangement: Arrangement }) => useCompiled(props?.arrangement ?? DEFAULT_ARRANGEMENT), {
    wrapper,
    initialProps: { arrangement: DEFAULT_ARRANGEMENT },
  });

test("useCompiled keeps the last good rig after the server rejects an edit", async () => {
  stubApi();
  const { result, rerender } = await renderCompiled();
  await vi.waitFor(() => expect(result.current.current).toBe(true));
  const good = result.current.rig;
  expect(good?.fixtures).toHaveLength(48);

  await rerender({ arrangement: { ...DEFAULT_ARRANGEMENT, fixtures: [{ id: "x", type: "no-such-type" }] } });
  await vi.waitFor(() => expect(result.current.query.isError).toBe(true));
  expect(result.current.rig).toBe(good);
  expect(result.current.current).toBe(false);
});

test("useCompiled compiles once after a run of quick edits", async () => {
  const asked = stubApi();
  const { result, rerender } = await renderCompiled();
  await vi.waitFor(() => expect(result.current.current).toBe(true));
  for (const level of [0.2, 0.4, 0.6, 0.8]) {
    await rerender({ arrangement: { ...DEFAULT_ARRANGEMENT, power: { max_brightness: level } } });
  }
  await vi.waitFor(() => expect(result.current.current).toBe(true));
  expect(asked.filter((path) => path === "/api/compile")).toHaveLength(2);
});

test("useCompiled compiles nothing for a new name: the compile never reads it", async () => {
  const asked = stubApi();
  const { result, rerender } = await renderCompiled();
  await vi.waitFor(() => expect(result.current.current).toBe(true));
  const rig = result.current.rig;
  await rerender({ arrangement: { ...DEFAULT_ARRANGEMENT, name: "gold" } });
  await vi.waitFor(() => expect(result.current.current).toBe(true));
  expect(result.current.rig).toBe(rig);
  expect(asked.filter((path) => path === "/api/compile")).toHaveLength(1);
});
