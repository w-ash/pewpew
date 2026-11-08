import { QueryClientProvider } from "@tanstack/react-query";
import type { ReactNode } from "react";
import { expect, test, vi } from "vitest";
import { renderHook } from "vitest-browser-react";
import { createQueryClient, useCompiled } from "../../../src/studio/api/queries";
import type { Arrangement } from "../../../src/studio/api/types";
import { DEFAULT_ARRANGEMENT } from "../../../src/studio/store/doc";
import { dragPreview, useSettledPreview } from "../../../src/studio/viewer/dragPreview";
import { stubApi } from "../fixtures/api";

function wrapper({ children }: { children: ReactNode }) {
  return <QueryClientProvider client={createQueryClient()}>{children}</QueryClientProvider>;
}

/** The studio's rule: the view's compile, and the preview that ends when it settles. */
function useView(arrangement: Arrangement) {
  const compiled = useCompiled(arrangement);
  useSettledPreview(compiled.answered);
  return compiled;
}

const refused: Arrangement = { ...DEFAULT_ARRANGEMENT, fixtures: [{ id: "x", type: "no-such-type" }] };

test("a drag whose commit does not compile, then undone, leaves no preview over the last good rig", async () => {
  stubApi();
  const { result, rerender } = await renderHook((props?: { arrangement: Arrangement }) => useView(props!.arrangement), {
    wrapper,
    initialProps: { arrangement: DEFAULT_ARRANGEMENT },
  });
  await vi.waitFor(() => expect(result.current.current).toBe(true));
  const good = result.current.rig;

  // A drag commits a pose the server refuses: the view keeps the last good rig, so the preview ends.
  dragPreview.begin([0]);
  await rerender({ arrangement: refused });
  await vi.waitFor(() => expect(result.current.query.isError).toBe(true));
  expect(result.current.rig).toBe(good);
  expect(dragPreview.delta).toBeNull();

  // Another drag commits the pose the last good rig has: its compile is the cached one, the same rig
  // object, and the preview still ends.
  dragPreview.begin([0]);
  await rerender({ arrangement: DEFAULT_ARRANGEMENT });
  await vi.waitFor(() => expect(result.current.current).toBe(true));
  expect(result.current.rig).toBe(good);
  expect(dragPreview.delta).toBeNull();
});

test("a drag's preview holds until the compile of its commit arrives", async () => {
  stubApi();
  const { result, rerender } = await renderHook((props?: { arrangement: Arrangement }) => useView(props!.arrangement), {
    wrapper,
    initialProps: { arrangement: DEFAULT_ARRANGEMENT },
  });
  await vi.waitFor(() => expect(result.current.current).toBe(true));
  dragPreview.begin([0]);
  await rerender({ arrangement: { ...DEFAULT_ARRANGEMENT, power: { max_brightness: 0.5 } } });
  expect(dragPreview.delta).not.toBeNull();
  await vi.waitFor(() => expect(result.current.current).toBe(true));
  expect(dragPreview.delta).toBeNull();
});
