import { useEffect, useState } from "react";
import { useOnChange } from "../design/useOnChange";
import { useRefusalExcept, type Refusal } from "../wire/store";

/** How long a refusal borrows the status bar. */
const REFUSAL_MS = 4000;

/** The controls whose refusals their own forms show in place: a param, the look editor and the
 * add-layer panel. The bar shows every other. */
const IN_PLACE = ["set", "save", "delete", "rename", "cycle", "favorite", "fade", "add_layer"] as const;

/** The latest refusal the bar shows, for REFUSAL_MS after it came, else null. */
export function useShownRefusal(): Refusal | null {
  const refusal = useRefusalExcept(IN_PLACE);
  const [shown, setShown] = useState<Refusal | null>(null);
  useOnChange(refusal, () => setShown(refusal));
  useEffect(() => {
    if (!shown) return;
    const id = setTimeout(() => setShown(null), REFUSAL_MS);
    return () => clearTimeout(id);
  }, [shown]);
  return shown;
}
