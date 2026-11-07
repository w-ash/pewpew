import { QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { describe, expect, it } from "vitest";
import { server } from "@/mocks/node";
import { DEFAULT_ARRANGEMENT } from "@/store/doc";
import { createQueryClient, useCompiled } from "./queries";
import type { Arrangement } from "./types";

function wrapper({ children }: { children: ReactNode }) {
  return (
    <QueryClientProvider client={createQueryClient()}>
      {children}
    </QueryClientProvider>
  );
}

function countCompiles() {
  let n = 0;
  const onRequest = ({ request }: { request: Request }) => {
    if (new URL(request.url).pathname === "/api/compile") n++;
  };
  server.events.on("request:start", onRequest);
  return () => {
    server.events.removeListener("request:start", onRequest);
    return n;
  };
}

describe("useCompiled", () => {
  it("keeps the last good rig after the server rejects an edit", async () => {
    const { result, rerender } = renderHook(
      ({ arrangement }: { arrangement: Arrangement }) =>
        useCompiled(arrangement),
      { wrapper, initialProps: { arrangement: DEFAULT_ARRANGEMENT } },
    );
    await waitFor(() => expect(result.current.current).toBe(true));
    const good = result.current.rig;
    expect(good?.fixtures).toHaveLength(48);

    rerender({
      arrangement: {
        ...DEFAULT_ARRANGEMENT,
        fixtures: [{ id: "x", type: "no-such-type" }],
      },
    });
    await waitFor(() => expect(result.current.query.isError).toBe(true));
    expect(result.current.rig).toBe(good);
    expect(result.current.current).toBe(false);
  });

  it("compiles once after a run of quick edits", async () => {
    const stop = countCompiles();
    const { result, rerender } = renderHook(
      ({ arrangement }: { arrangement: Arrangement }) =>
        useCompiled(arrangement),
      { wrapper, initialProps: { arrangement: DEFAULT_ARRANGEMENT } },
    );
    await waitFor(() => expect(result.current.current).toBe(true));
    let last = DEFAULT_ARRANGEMENT;
    for (const name of ["g", "go", "gol", "gold"]) {
      last = { ...DEFAULT_ARRANGEMENT, name };
      rerender({ arrangement: last });
    }
    await waitFor(() => expect(result.current.current).toBe(true));
    expect(stop()).toBe(2);
  });
});
