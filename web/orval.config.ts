import { defineConfig } from "orval";

// ../openapi.json is written by `scripts/export_openapi.py`; `pnpm generate`
// rewrites it and src/studio/api/generated.
export default defineConfig({
  studio: {
    input: { target: "../openapi.json" },
    output: {
      mode: "tags-split",
      target: "src/studio/api/generated",
      schemas: "src/studio/api/generated/model",
      client: "fetch",
      mock: false,
      override: {
        mutator: { path: "src/studio/api/fetch.ts", name: "customFetch" },
      },
    },
  },
});
