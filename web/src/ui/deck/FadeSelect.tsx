import { FADES } from "../../domain/aura/looks";
import { Select } from "../common/Select";

/** The fade a press on a look takes; a look's own fade is set in its settings. */
export function FadeSelect({ fade, onFade }: { fade: string; onFade(fade: string): void }) {
  return <Select className="fade" items={FADES} value={fade} onChange={onFade} label="fade into a look" />;
}
