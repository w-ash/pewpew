import { formatValue } from "../../../domain/params/kinds";
import type { Param } from "../../../domain/params/schema";
import type { ControlProps } from "./types";

/** A record this page cannot read: its value shown, not settable. */
export function UnknownControl({ p, value }: ControlProps<Param>) {
  const kind = p.kind === "unknown" && p.wireKind ? `a ${p.wireKind} param` : "this param";
  return (
    <p className="control unknown">
      {formatValue(p, value)}: this page cannot set {kind}
    </p>
  );
}
