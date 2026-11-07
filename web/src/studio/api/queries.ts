import { keepPreviousData, QueryClient, useQuery } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { ApiError } from "./fetch";
import { compileArrangement, getCatalog, getLooks } from "./endpoints";
import type { Arrangement, CompiledRig } from "./types";

/** Quiet time after an edit before it compiles, so typing sends one compile. */
const COMPILE_DEBOUNCE_MS = 200;

export function createQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        refetchOnWindowFocus: false,
        staleTime: Number.POSITIVE_INFINITY,
      },
    },
  });
}

export function useCatalog() {
  return useQuery({ queryKey: ["catalog"], queryFn: getCatalog });
}

export function useLooks() {
  return useQuery({ queryKey: ["looks"], queryFn: getLooks });
}

/** `value`, once it has stopped changing for `ms`. */
function useDebounced<T>(value: T, ms: number): T {
  const [settled, setSettled] = useState(value);
  useEffect(() => {
    const timer = setTimeout(() => setSettled(value), ms);
    return () => clearTimeout(timer);
  }, [value, ms]);
  return settled;
}

/**
 * The server's compile of an arrangement, after a short quiet spell.
 *
 * `rig` is the last compile that succeeded, so the view keeps it while a new
 * compile is in flight and after one fails. `current` is true only when `rig`
 * is the compile of `arrangement` itself.
 */
export function useCompiled(arrangement: Arrangement, enabled = true) {
  const settled = useDebounced(arrangement, COMPILE_DEBOUNCE_MS);
  const query = useQuery({
    // The compile never reads the name, so a rename compiles nothing.
    queryKey: ["compile", { ...settled, name: undefined }],
    queryFn: ({ signal }) => compileArrangement(settled, signal),
    placeholderData: keepPreviousData,
    enabled,
    retry: (count, error) =>
      !(error instanceof ApiError && error.status < 500) && count < 2,
    gcTime: 5 * 60_000,
  });
  const fresh = query.isSuccess && !query.isPlaceholderData;
  const [lastGood, setLastGood] = useState<CompiledRig | null>(null);
  if (fresh && query.data !== lastGood) setLastGood(query.data);
  return {
    query,
    rig: fresh ? query.data : lastGood,
    current: fresh && settled === arrangement,
  };
}
