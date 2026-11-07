/**
 * The studio's HTTP routes (docs/studio/contracts.md, "HTTP"), on orval's
 * generated client.
 *
 * `customFetch` throws `ApiError` on any non-2xx reply, so only the 200 body
 * reaches these functions. The spec types the arrangement, catalog and
 * compile bodies as free-form objects; these functions give them their
 * hand-written types.
 */
import * as api from "./generated";
import type {
  Arrangement,
  Catalog,
  CompiledRig,
  SavedArrangement,
} from "./types";

type Body = Record<string, unknown>;

export async function getCatalog(): Promise<Catalog> {
  return (await api.getCatalog()).data as unknown as Catalog;
}

export async function compileArrangement(
  arrangement: Arrangement,
  signal?: AbortSignal,
): Promise<CompiledRig> {
  const { data } = await api.compileArrangement(
    arrangement as unknown as Body,
    { signal },
  );
  return data as CompiledRig;
}

export async function saveArrangement(
  arrangement: Arrangement,
): Promise<SavedArrangement> {
  const { data } = await api.saveArrangement(arrangement as unknown as Body);
  return data as SavedArrangement;
}

export async function getArrangement(id: string): Promise<Arrangement> {
  const { data } = await api.getArrangement(encodeURIComponent(id));
  return data as Arrangement;
}
