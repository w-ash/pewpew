/**
 * Types for the studio API.
 *
 * `SavedArrangement` comes from the OpenAPI spec through orval
 * (src/studio/api/generated). The compile body's types are generated from
 * the pydantic models (src/rig/types.gen.ts), the parts catalog's are in
 * src/rig/parts.ts, and the arrangement's are the editor's
 * (src/arrange/types.ts).
 */
import type { Opaque } from "../../arrange/types";

export type { SavedArrangement } from "./generated/model";
export type { CompiledFixture, CompiledRig } from "../../rig/types.gen";
export type { PartsCatalog, Vec3 } from "../../rig/parts";
export type * from "../../arrange/types";

/** One look in the looks file's form (version 4), as `GET /api/looks` gives
 * each: the engine checks it whole, so the page passes it through. */
export type LookDocument = Opaque & { layers: unknown[] };
