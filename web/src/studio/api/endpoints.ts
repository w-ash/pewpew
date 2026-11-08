/**
 * The studio's HTTP routes (docs/studio/contracts.md, "HTTP"), on orval's
 * generated client.
 *
 * `customFetch` throws `ApiError` on any non-2xx reply, so only the 200 body
 * reaches these functions. The spec types the arrangement, catalog and
 * compile bodies and the looks as free-form objects; these functions give them
 * their hand-written types.
 */
import * as api from "./generated";
import type {
  Arrangement,
  PartsCatalog,
  CompiledRig,
  LookDocument,
  SavedArrangement,
} from "./types";

type Body = Record<string, unknown>;

export async function getCatalog(): Promise<PartsCatalog> {
  return (await api.getCatalog()).data as unknown as PartsCatalog;
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

/** The example looks by name, each ready to send as a `look` request. */
export async function getLooks(): Promise<Record<string, LookDocument>> {
  return (await api.listLooks()).data as Record<string, LookDocument>;
}
