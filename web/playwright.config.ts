import { tmpdir } from "node:os";
import { join } from "node:path";
import { defineConfig } from "@playwright/test";

// The end-to-end tests, against the Gallery (`python -m pewpew studio`) on :8000 and the Vite dev server
// in front of it, which serves the Console page and the test fixtures and proxies /ws, /parts.json and
// /assembly to the Gallery. Both start here.
const PORT = 5179;
const GALLERY = "http://127.0.0.1:8000";

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  retries: 0,
  use: {
    baseURL: `http://127.0.0.1:${PORT}`,
    browserName: "chromium",
  },
  webServer: [
    {
      command: `uv run python -m pewpew studio --port ${new URL(GALLERY).port} --db ${join(tmpdir(), "pewpew-e2e-gallery.sqlite3")}`,
      cwd: "..",
      url: `${GALLERY}/health/live`,
      reuseExistingServer: false,
      timeout: 60_000,
    },
    {
      command: `pnpm exec vite --port ${PORT} --strictPort --host 127.0.0.1`,
      env: { PEWPEW_ENGINE: GALLERY },
      url: `http://127.0.0.1:${PORT}/e2e/fixtures/color.html`,
      reuseExistingServer: false,
      timeout: 60_000,
    },
  ],
});
