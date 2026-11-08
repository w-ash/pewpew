import { useGLTF } from "@react-three/drei";
import { useEffect, useMemo, useState } from "react";
import type { PartsCatalog } from "../rig/parts";
import { assembliesFor, baseType, missingAssemblies, type ViewRig } from "./instances";

/** The load state of a rig's GLBs, for a view's ErrorBoundary around them: `key` remounts it for a new
 * set of types or a retry, `onError` keeps what it threw, `retry` tries again and calls `onRetry` (which
 * can fetch the parts catalog again), and `missing` names the types with no assembly to draw. */
export function useModels(rig: ViewRig | null, catalog: PartsCatalog | null, onRetry?: () => void) {
  const [error, setError] = useState<string | null>(null);
  // A new set of fixture types gets a fresh try at loading their GLBs.
  const types = useMemo(
    () =>
      [
        ...new Set(
          rig?.fixtures.flatMap((f) => [
            baseType(f),
            ...Object.values(f.attachments ?? {}).filter((a) => a !== null),
          ]) ?? [],
        ),
      ]
        .sort()
        .join(","),
    [rig],
  );
  // The error belongs to the models it was raised for.
  // oxlint-disable-next-line react/set-state-in-effect -- drops the error of the models a new key replaces; render-time reset would need a key prop on the loader
  useEffect(() => setError(null), [types]);
  const missing = useMemo(() => (rig && catalog ? missingAssemblies(rig, catalog) : []), [rig, catalog]);
  // A failed load stays in the loader's cache, so it is cleared before a retry.
  const [attempt, setAttempt] = useState(0);
  const urls = useMemo(
    () => (rig && catalog ? assembliesFor(rig, catalog).map((r) => r.url) : []),
    [rig, catalog],
  );
  const onError = (message: string) => {
    useGLTF.clear(urls);
    setError(message);
  };
  const retry = () => {
    onRetry?.();
    setError(null);
    setAttempt((a) => a + 1);
  };
  return { key: `${types}#${attempt}`, error, onError, retry, missing };
}
