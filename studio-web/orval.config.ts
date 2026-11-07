import { defineConfig } from "orval";

// ../openapi.json is written by `scripts/export_openapi.py`; `pnpm generate`
// rewrites it and src/api/generated. The app's msw mocks live in src/mocks.
export default defineConfig({
  studio: {
    input: { target: "../openapi.json" },
    output: {
      mode: "tags-split",
      target: "src/api/generated",
      schemas: "src/api/generated/model",
      client: "react-query",
      mock: false,
      override: {
        mutator: { path: "src/api/client.ts", name: "customFetch" },
        query: { useSuspenseQuery: false, version: 5 },
      },
    },
  },
});
