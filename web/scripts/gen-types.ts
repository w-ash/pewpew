// Writes src/rig/types.gen.ts from ../schemas/rig.v1.json, which
// `uv run python scripts/export_schemas.py` writes from the pydantic models
// (src/pewpew/rig/models.py). With --check it writes nothing, and exits 1
// when the file differs. Options: https://github.com/bcherny/json-schema-to-typescript
import { readFile, writeFile } from "node:fs/promises";
import { compile, type JSONSchema } from "json-schema-to-typescript";

const SCHEMA = new URL("../../schemas/rig.v1.json", import.meta.url);
const OUT = new URL("../src/rig/types.gen.ts", import.meta.url);
const REGENERATE = "pnpm -C web gen-types";
const BANNER = [
  "// Generated from schemas/rig.v1.json by web/scripts/gen-types.ts; do not edit.",
  `// Regenerate: \`${REGENERATE}\`. The schema comes from src/pewpew/rig/models.py.`,
].join("\n");

/** `node` with each fixed tuple in the draft-04 form json-schema-to-typescript reads: `prefixItems` as `items`. */
function draft04Tuples(node: unknown): unknown {
  if (Array.isArray(node)) return node.map(draft04Tuples);
  if (node === null || typeof node !== "object") return node;
  const tuple = "prefixItems" in node && !("items" in node);
  return Object.fromEntries(
    Object.entries(node).map(([key, value]) => [tuple && key === "prefixItems" ? "items" : key, draft04Tuples(value)]),
  );
}

const schema = draft04Tuples(JSON.parse(await readFile(SCHEMA, "utf8"))) as JSONSchema;
const text = await compile(schema, "RigJson", {
  bannerComment: BANNER,
  // Every $def becomes a type, also one only another $def reaches.
  unreachableDefinitions: true,
  // A schema without additionalProperties gets no index signature.
  additionalProperties: false,
  format: true,
  style: { printWidth: 120, singleQuote: false, semi: true, trailingComma: "all" },
});

if (process.argv.includes("--check")) {
  const current = await readFile(OUT, "utf8").catch(() => "");
  if (current !== text) {
    console.error(`src/rig/types.gen.ts is stale; run \`${REGENERATE}\``);
    process.exit(1);
  }
} else {
  await writeFile(OUT, text);
  console.log("wrote src/rig/types.gen.ts");
}
