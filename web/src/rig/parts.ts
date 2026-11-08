/**
 * The parts catalog the engine serves: `Catalog.to_json` in
 * src/pewpew/rig/catalog.py, with each type's assembly `digest` and
 * `assembly_url` added. It is not a pydantic model, so these types are
 * written by hand.
 */

export type Vec3 = [number, number, number];

export interface CatalogAnchor {
  accepts?: string | null;
  connector?: string | null;
}

export interface CatalogFixtureType {
  id: string;
  name: string;
  /** Null on a server that cannot build geometry. */
  digest: string | null;
  assembly_url: string | null;
  anchors?: Record<string, CatalogAnchor>;
  [key: string]: unknown;
}

export interface CatalogAttachmentType {
  id: string;
  name: string;
  /** Null on a server that cannot build geometry. */
  digest: string | null;
  assembly_url: string | null;
  fits?: string;
  [key: string]: unknown;
}

export interface CatalogEntry {
  id: string;
  name: string;
  [key: string]: unknown;
}

export interface PresetInfo {
  name: string;
  doc?: string;
  params: Array<{ name: string; required: boolean; default?: unknown }>;
}

export interface PartsCatalog {
  digest?: string;
  fixture_types: CatalogFixtureType[];
  attachment_types: CatalogAttachmentType[];
  controllers: CatalogEntry[];
  psus: CatalogEntry[];
  cables: CatalogEntry[];
  presets: PresetInfo[];
}
