/**
 * tests/goldens/describe.json: every gallery pattern's `describe()` records
 * and the params zoo's, which declares one param of each kind the engine has.
 * Read through a glob, so `tsc` resolves no file outside studio-web/: the image
 * build (Dockerfile) type-checks the tests without the repo's tests/ folder.
 */
type Golden = { patterns: Record<string, Record<string, unknown>[]> };

const found = import.meta.glob<Golden>("../../../tests/goldens/describe.json", {
  eager: true,
  import: "default",
});

/** The golden's records by pattern. Throws when the file is not found. */
export function describeGolden(): Golden["patterns"] {
  const golden = Object.values(found)[0];
  if (!golden) throw new Error("tests/goldens/describe.json was not found");
  return golden.patterns;
}

/** The params zoo's record of `kind`. */
export function zooRecord(kind: string): Record<string, unknown> {
  const record = describeGolden().zoo.find((r) => r.kind === kind);
  if (!record) throw new Error(`the params zoo declares no ${kind}`);
  return record;
}
